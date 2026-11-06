"""
uninstall_gms.py — Feature 6: Google Play Services (GMS) Clean Purge Payload Generator.
Performs a deep system wipe of all GMS artifacts, services, permissions, and caches.
"""
import os
import time
from core.constants import SIGNATURE_BANNER, GMS_FULL_PURGE_PACKAGES, GMS_FULL_PRIVAPP_PATTERNS
from core.exceptions import log_exception
from core.i18n import t
from payloads.base import clean_usb_drive, write_script_file
from payloads.bash_builder import (
    gen_bash_header,
    gen_mount_rw,
    gen_mount_ro,
    gen_purge_stale_gms,
    gen_restore_oem_defaults,
    gen_bash_footer
)
from payloads.manual_generator import generate_info_content, write_payload_manuals

GMS_PURGE_PACKAGES = GMS_FULL_PURGE_PACKAGES
GMS_PRIVAPP_PATTERNS = GMS_FULL_PRIVAPP_PATTERNS


def prepare_uninstall_gms_usb(
    usb_drive: str,
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """Prepares USB to cleanly remove Google Play Services, Play Store, and account caches."""
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(t("logs.prep_usb_header", f"\n── Preparing Uninstall GMS USB: {usb_drive} ──", title=t("nav.uninstall_gms_title", "Uninstall GMS"), drive=usb_drive))
    if not os.path.exists(usb_drive):
        _log(t("logs.usb_not_found", f"  ✗ USB Drive not found: {usb_drive}", drive=usb_drive))
        return False

    if cancel_check and cancel_check():
        _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
        return False

    try:
        clean_work_units = count_usb_clean_ops(usb_drive) if "count_usb_clean_ops" in globals() else 10
        clean_usb_drive(usb_drive, log_func, progress_func, cancel_check, start_pct=0.0, end_pct=0.45)
        if cancel_check and cancel_check():
            _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
            return False
        update_dir = os.path.join(usb_drive, "update")
        os.makedirs(update_dir, exist_ok=True)

        if progress_func:
            progress_func(0.55, "Configuring GMS clean purge script...", 0.0, 0, 0)

        script = (
            gen_bash_header("DEEP GMS CLEAN REMOVAL", "gms_uninstall.log")
            + gen_mount_rw()
            + gen_purge_stale_gms(log_var="LOG_FILE")
            + gen_restore_oem_defaults()
            + gen_mount_ro()
            + gen_bash_footer(
                success_status="SUCCESS",
                with_reboot=True,
                reboot_delay=3,
                reboot_msg="Rebooting infotainment system to clean framework cache..."
            )
        )
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        if progress_func:
            progress_func(0.80, "Writing Google Services removal manual (HTML)...", 0.0, 0, 0)

        write_payload_manuals(usb_drive, "Uninstall_GMS_Info", "uninstall_gms")

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, "Uninstall GMS USB ready!", 0.0, 0, 0)

        _log(t("logs.prep_usb_success", "✓ Uninstall GMS USB prepared successfully.", title=t("nav.uninstall_gms_title", "Uninstall GMS")))
        return True
    except Exception as e:
        log_exception(e, "prepare_uninstall_gms_usb")
        _log(t("logs.prep_failed", "  ✗ Failed to prepare {title} USB: {err}", title=t("nav.uninstall_gms_title", "Uninstall GMS"), err=str(e)))
        return False
