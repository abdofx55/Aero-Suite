"""
reboot_screen.py — Feature 9: Restart Infotainment Screen Payload Generator.
Safely triggers a clean powerctl/hardware reboot of the Snapdragon IVI SoC.
"""
import os
import time
from core.constants import SIGNATURE_BANNER
from core.exceptions import log_exception
from core.i18n import t
from payloads.base import clean_usb_drive, write_script_file
from payloads.bash_builder import gen_bash_header, gen_bash_footer
from payloads.manual_generator import generate_info_content, write_payload_manuals


def prepare_reboot_screen_usb(
    usb_drive: str,
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """Prepares USB payload to instantly reboot / restart the car's Android infotainment unit."""
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(t("logs.prep_usb_header", f"\n── Preparing Restart Infotainment Screen USB: {usb_drive} ──", title=t("nav.reboot_screen_title", "Restart Screen"), drive=usb_drive))
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
            progress_func(0.60, "Generating infotainment reboot payload...", 0.0, 0, 0)

        script = (
            gen_bash_header("INSTANT SCREEN REBOOT", "reboot.log")
            + '\necho "Triggering hardware powerctl reboot..." >> "$LOG_FILE"\n'
            + gen_bash_footer(success_status="SUCCESS", with_reboot=True, reboot_delay=0, reboot_msg="Rebooting infotainment system...")
        )
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        if progress_func:
            progress_func(0.85, "Writing restart screen manual (HTML)...", 0.0, 0, 0)

        write_payload_manuals(usb_drive, "Restart_Screen_Info", "reboot_screen")

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, "Reboot Screen USB ready!", 0.0, 0, 0)

        _log(t("logs.prep_usb_success", "✓ Restart Infotainment Screen USB prepared successfully.", title=t("nav.reboot_screen_title", "Restart Screen")))
        return True
    except Exception as e:
        log_exception(e, "prepare_reboot_screen_usb")
        _log(t("logs.prep_failed", "  ✗ Failed to prepare {title} USB: {err}", title=t("nav.reboot_screen_title", "Restart Screen"), err=str(e)))
        return False
