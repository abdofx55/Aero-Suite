"""
uninstall_apps.py — Feature 2: Safe Dual-Sweep Application Uninstallation Payload Generator.
Strictly removes vetted packages from both /data/app and /system/priv-app.
"""
import os
import re
import time
from core.constants import SIGNATURE_BANNER
from core.exceptions import log_exception
from core.i18n import t
from payloads.base import clean_usb_drive, write_script_file
from payloads.bash_builder import (
    gen_bash_header,
    gen_mount_rw,
    gen_mount_ro,
    gen_purge_apps,
    gen_bash_footer,
    gen_system_purge_reboot_check
)
from payloads.manual_generator import generate_info_content, write_payload_manuals


def prepare_uninstall_apps_usb(
    usb_drive: str,
    selected_packages: list,
    allowed_packages: set,
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """
    Generates a safe uninstallation payload that searches and purges from BOTH
    User Apps (/data/app) and System Apps (/system/priv-app and /system/app).
    STRICT SECURITY RULE: Only packages in allowed_packages (derived from local apks/) are allowed!
    """
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(t("logs.prep_usb_header", f"\n── Preparing Safe Uninstall Apps USB: {usb_drive} ──", title=t("nav.uninstall_apps_title", "Uninstall Apps"), drive=usb_drive))
    if not os.path.exists(usb_drive):
        _log(t("logs.usb_not_found", f"  ✗ USB Drive not found: {usb_drive}", drive=usb_drive))
        return False

    if cancel_check and cancel_check():
        _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
        return False

    # Security verification
    vetted_packages = [p for p in selected_packages if p in allowed_packages]
    if not vetted_packages:
        _log(t("logs.no_pkgs_uninstall", "  ✗ No valid vetted packages selected for uninstall."))
        return False

    try:
        clean_usb_drive(usb_drive, log_func, progress_func, cancel_check, start_pct=0.0, end_pct=0.30)
        if cancel_check and cancel_check():
            _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
            return False
        update_dir = os.path.join(usb_drive, "update")
        os.makedirs(update_dir, exist_ok=True)

        if progress_func:
            progress_func(0.55, f"Configuring {len(vetted_packages)} uninstall command(s)...", 0.0, 0, 0)

        script = (
            gen_bash_header("SAFE APP UNINSTALLER", "uninstall_log.txt")
            + gen_mount_rw()
            + gen_purge_apps(vetted_packages, purge_system_apps=True)
            + gen_mount_ro()
            + gen_bash_footer(success_status="SUCCESS", with_reboot=False)
            + gen_system_purge_reboot_check()
        )
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        if progress_func:
            progress_func(0.80, "Writing uninstallation manual (HTML)...", 0.0, len(vetted_packages), len(vetted_packages))

        write_payload_manuals(usb_drive, "Uninstall_Apps_Info", "uninstall_apps", vetted_packages=vetted_packages)

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, len(vetted_packages), len(vetted_packages))
            time.sleep(0.04)
            progress_func(1.0, "Safe Uninstall USB ready!", 0.0, len(vetted_packages), len(vetted_packages))

        _log(t("logs.prep_usb_success", "✓ Safe Uninstall Apps USB prepared successfully.", title=t("nav.uninstall_apps_title", "Uninstall Apps")))
        return True
    except Exception as e:
        log_exception(e, "prepare_uninstall_apps_usb")
        _log(t("logs.prep_failed", "  ✗ Failed to prepare {title} USB: {err}", title=t("nav.uninstall_apps_title", "Uninstall Apps"), err=str(e)))
        return False
