"""
vehicle_tweaks.py — Feature: Advanced Vehicle Customization & Comfort Tweaks Payload Generator.
Generates shell payloads to interact directly with Dongfeng Shine Qinggan CAN-Bus (qg.canbus).
Allows granular enabling or disabling of specific vehicle features without touching other settings.
"""
import os
import time
from core.constants import SIGNATURE_BANNER
from core.exceptions import log_exception
from core.i18n import t
from payloads.base import clean_usb_drive, write_script_file
from payloads.bash_builder import gen_bash_header, gen_canbus_tweaks, gen_bash_footer
from payloads.manual_generator import write_payload_manuals


def prepare_vehicle_tweaks_usb(
    usb_drive: str,
    selected_tweaks: list,
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """
    Prepares USB payload containing CAN-Bus IPC transactions for selected vehicle tweaks.
    Each item in selected_tweaks is a dict: {"tweak": dict, "action": "enable"|"disable"}
    """
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(t("logs.prep_usb_header", f"\n── Preparing Vehicle Customization Tweaks USB: {usb_drive} ──", title=t("nav.vehicle_tweaks_title", "Vehicle Tweaks"), drive=usb_drive))
    if not os.path.exists(usb_drive):
        _log(t("logs.usb_not_found", f"  ✗ USB Drive not found: {usb_drive}", drive=usb_drive))
        return False

    if not selected_tweaks:
        _log("  ⚠ No vehicle features selected for payload generation.")
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
            progress_func(0.50, "Generating vehicle configuration commands...", 0.0, 0, 0)

        script = (
            gen_bash_header("ADVANCED VEHICLE TWEAKS", "vehicle_tweaks.log")
            + gen_canbus_tweaks(selected_tweaks, log_var="LOG_FILE")
            + gen_bash_footer(success_status="SUCCESS", with_reboot=False)
        )
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        if progress_func:
            progress_func(0.85, "Writing vehicle tweaks manual (HTML)...", 0.0, 0, 0)

        write_payload_manuals(usb_drive, "Vehicle_Tweaks_Info", "vehicle_tweaks", selected_tweaks=selected_tweaks)

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, "Vehicle Tweaks USB ready!", 0.0, 0, 0)

        _log(t("logs.prep_usb_success", "✓ Vehicle Tweaks USB prepared successfully.", title=t("nav.vehicle_tweaks_title", "Vehicle Tweaks")))
        return True

    except Exception as e:
        log_exception(e, "prepare_vehicle_tweaks_usb")
        _log(t("logs.prep_failed", f"  ✗ Failed to prepare vehicle tweaks USB: {err}", title=t("nav.vehicle_tweaks_title", "Vehicle Tweaks"), err=str(e)))
        return False
