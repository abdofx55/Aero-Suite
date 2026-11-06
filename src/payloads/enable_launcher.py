"""
enable_launcher.py — Feature 8: Unfreeze / Enable Stock OEM Launcher Payload Generator.
Unfreezes com.qinggan.app.launcher to restore original Dongfeng dashboard.
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
    gen_enable_app,
    gen_system_snapshot,
    gen_bash_footer
)
from payloads.manual_generator import generate_info_content, write_payload_manuals


def prepare_enable_launcher_usb(
    usb_drive: str,
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """Prepares USB payload to unfreeze (enable) the stock Dongfeng system launcher."""
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(t("logs.prep_usb_header", f"\n── Preparing Enable Factory Launcher USB: {usb_drive} ──", title=t("nav.enable_launcher_title", "Enable Launcher"), drive=usb_drive))
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
            progress_func(0.60, "Generating enable launcher payload...", 0.0, 0, 0)

        script = (
            gen_bash_header("ENABLE FACTORY LAUNCHER", "install_log.txt")
            + gen_mount_rw()
            + gen_enable_app(FACTORY_LAUNCHER_PKG, set_home_activity=f"{FACTORY_LAUNCHER_PKG}/.activity.MainActivity")
            + gen_system_snapshot()
            + gen_mount_ro()
            + 'echo "Switching back to stock launcher..." >> "$LOG_FILE"\n'
            + 'am start -c android.intent.category.HOME -a android.intent.action.MAIN >> "$LOG_FILE" 2>&1\n'
            + gen_bash_footer(success_status="SUCCESS", with_reboot=False)
        )
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        if progress_func:
            progress_func(0.85, "Writing enable launcher manual (HTML)...", 0.0, 0, 0)

        write_payload_manuals(usb_drive, "Enable_Launcher_Info", "enable_launcher", pkg=FACTORY_LAUNCHER_PKG)

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, "Enable Launcher USB ready!", 0.0, 0, 0)

        _log(t("logs.prep_usb_success", "✓ Enable Launcher USB prepared successfully.", title=t("nav.enable_launcher_title", "Enable Launcher")))
        return True
    except Exception as e:
        log_exception(e, "prepare_enable_launcher_usb")
        _log(t("logs.prep_failed", "  ✗ Failed to prepare {title} USB: {err}", title=t("nav.enable_launcher_title", "Enable Launcher"), err=str(e)))
        return False
