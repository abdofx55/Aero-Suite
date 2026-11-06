"""
open_settings.py — Feature 4: Open Android Native Settings Payload Generator.
Dispatches an Android intent to reveal stock Android Settings and Developer Options.
"""
import os
import time
from core.constants import SIGNATURE_BANNER
from core.exceptions import log_exception
from core.i18n import t
from payloads.base import clean_usb_drive, write_script_file
from payloads.bash_builder import gen_bash_header, gen_bash_footer
from payloads.manual_generator import generate_info_content, write_payload_manuals


def prepare_open_settings_usb(
    usb_drive: str,
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """Prepares USB payload to unlock and launch native Android Settings on car screen."""
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(t("logs.prep_usb_header", f"\n── Preparing Open Settings USB: {usb_drive} ──", title=t("nav.open_settings_title", "Open Settings"), drive=usb_drive))
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
            progress_func(0.60, "Configuring Android Settings unlock trigger...", 0.0, 0, 0)

        script = (
            gen_bash_header("LAUNCH ANDROID SETTINGS", "open_settings.log")
            + "\n# Launch Android Native Settings\n"
            + 'am start -n com.android.settings/.Settings >> "$LOG_FILE" 2>&1\n'
            + 'am start -a android.settings.SETTINGS >> "$LOG_FILE" 2>&1\n\n'
            + gen_bash_footer(success_status="SUCCESS", with_reboot=False)
        )
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        if progress_func:
            progress_func(0.85, "Writing Android Settings manual (HTML)...", 0.0, 0, 0)

        write_payload_manuals(usb_drive, "Open_Settings_Info", "open_settings")

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, "Open Settings USB ready!", 0.0, 0, 0)

        _log(t("logs.prep_usb_success", "✓ Open Settings USB prepared successfully.", title=t("nav.open_settings_title", "Open Settings")))
        return True
    except Exception as e:
        log_exception(e, "prepare_open_settings_usb")
        _log(t("logs.prep_failed", "  ✗ Failed to prepare {title} USB: {err}", title=t("nav.open_settings_title", "Open Settings"), err=str(e)))
        return False
