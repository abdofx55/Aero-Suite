"""
disable_launcher.py — Feature 7: Freeze / Disable Stock OEM Launcher Payload Generator.
Freezes com.qinggan.app.launcher to hand over full home screen control to custom launchers.
"""
import os
import time
from core.constants import SIGNATURE_BANNER, FACTORY_LAUNCHER_PKG
from core.exceptions import log_exception
from core.i18n import t
from payloads.base import clean_usb_drive, write_script_file
from payloads.bash_builder import (
    gen_bash_header,
    gen_mount_rw,
    gen_mount_ro,
    gen_disable_app,
    gen_system_snapshot,
    gen_device_provisioning,
    gen_bash_footer
)
from payloads.manual_generator import generate_info_content, write_payload_manuals


def prepare_disable_launcher_usb(
    usb_drive: str,
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """Prepares USB payload to freeze (disable) the stock Dongfeng system launcher."""
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(t("logs.prep_usb_header", f"\n── Preparing Disable Factory Launcher USB: {usb_drive} ──", title=t("nav.disable_launcher_title", "Disable Launcher"), drive=usb_drive))
    if not os.path.exists(usb_drive):
        _log(t("logs.usb_not_found", f"  ✗ USB Drive not found: {usb_drive}", drive=usb_drive))
        return False

    if cancel_check and cancel_check():
        _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
        return False

    try:
        clean_usb_drive(usb_drive, log_func, progress_func, cancel_check, start_pct=0.0, end_pct=0.30)
        if cancel_check and cancel_check():
            _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
            return False

        update_dir = os.path.join(usb_drive, "update")
        os.makedirs(update_dir, exist_ok=True)

        if progress_func:
            progress_func(0.60, "Generating disable launcher payload...", 0.0, 0, 0)

        script = (
            gen_bash_header("DISABLE FACTORY LAUNCHER", "install_log.txt")
            + gen_mount_rw()
            + gen_disable_app(FACTORY_LAUNCHER_PKG)
            + gen_system_snapshot()
            + gen_device_provisioning()
            + gen_mount_ro()
            + 'echo "Switching to custom launcher..." >> "$LOG_FILE"\n'
            + 'am start -c android.intent.category.HOME -a android.intent.action.MAIN >> "$LOG_FILE" 2>&1\n'
            + gen_bash_footer(success_status="SUCCESS", with_reboot=False)
        )
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        if progress_func:
            progress_func(0.85, "Writing disable launcher manual (HTML)...", 0.0, 0, 0)

        write_payload_manuals(usb_drive, "Disable_Launcher_Info", "disable_launcher", pkg=FACTORY_LAUNCHER_PKG)

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, "Disable Launcher USB ready!", 0.0, 0, 0)

        _log(t("logs.prep_usb_success", "✓ Disable Launcher USB prepared successfully.", title=t("nav.disable_launcher_title", "Disable Launcher")))
        return True
    except Exception as e:
        log_exception(e, "prepare_disable_launcher_usb")
        _log(t("logs.prep_failed", "  ✗ Failed to prepare {title} USB: {err}", title=t("nav.disable_launcher_title", "Disable Launcher"), err=str(e)))
        return False
