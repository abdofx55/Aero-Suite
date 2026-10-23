"""
reboot_screen.py — Feature 9: Restart Infotainment Screen Payload Generator.
Safely triggers a clean powerctl/hardware reboot of the Snapdragon IVI SoC.
"""
import os
import time
from core.constants import SIGNATURE_BANNER
from core.exceptions import log_exception
from payloads.base import clean_usb_drive, write_script_file


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

    _log(f"\n── [9/13] Preparing Restart Infotainment Screen USB: {usb_drive} ──")
    if not os.path.exists(usb_drive):
        _log(f"  ✗ USB Drive not found: {usb_drive}")
        return False

    if cancel_check and cancel_check():
        _log("  ⚠ Operation cancelled by user.")
        return False

    try:
        clean_usb_drive(usb_drive, log_func, progress_func, cancel_check, start_pct=0.0, end_pct=0.30)
        if cancel_check and cancel_check():
            _log("  ⚠ Operation cancelled by user.")
            return False

        update_dir = os.path.join(usb_drive, "update")
        os.makedirs(update_dir, exist_ok=True)

        if progress_func:
            progress_func(0.60, "Generating infotainment reboot payload...", 0.0, 0, 0)

        script = """#!/system/bin/sh
# ==========================================
# AERO SUITE — INSTANT SCREEN REBOOT
# ==========================================

USB_PATH=""
for dir in /storage/* /mnt/media_rw/* /mnt/usb* /storage/usb*; do
    if [ -f "$dir/update/custom_rep.sh" ]; then
        USB_PATH="$dir"
        break
    fi
done
if [ -z "$USB_PATH" ]; then
    USB_PATH=$(dirname $(dirname "$0"))
fi

LOG_FILE="$USB_PATH/reboot.log"
echo "=== AERO REBOOT TRIGGERED ===" > "$LOG_FILE"
date >> "$LOG_FILE"

sync
echo "Triggering hardware powerctl reboot..." >> "$LOG_FILE"
sleep 1
sync
setprop sys.powerctl reboot || reboot -f || reboot
"""
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        info_path = os.path.join(usb_drive, "Restart_Screen_Info.txt")
        info_content = f"""🔄 AERO SUITE — RESTART INFOTAINMENT SCREEN MANUAL
Target Vehicle: Dongfeng Shine (Aeolus D53) Infotainment System

============================================================
1. TECHNICAL OVERVIEW & INTERNAL WORKFLOW
============================================================
This utility provides an instant, safe hardware-level reboot for the infotainment system:
1. Filesystem Synchronization:
   Executes sync to flush all pending storage buffers to protect eMMC integrity.
2. Power Control Reboot:
   Executes: setprop sys.powerctl reboot
   Safely terminates system services and restarts the Snapdragon SoC.
3. Non-Destructive:
   Does not modify any apps, settings, or user data. It simply performs a clean system reboot.

============================================================
2. VEHICLE USAGE INSTRUCTIONS
============================================================
1. Insert this USB drive into the vehicle USB port.
2. Within 2 to 5 seconds, the screen will turn off to reboot automatically.
3. As soon as the screen turns off (goes black), unplug the USB drive immediately (before it boots back up).

{SIGNATURE_BANNER}
"""
        if progress_func:
            progress_func(0.85, "Writing restart screen manual...", 0.0, 0, 0)

        with open(info_path, "w", encoding="utf-8") as f:
            f.write(info_content)

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, "Reboot Screen USB ready!", 0.0, 0, 0)

        _log("✓ Restart Infotainment Screen USB prepared successfully.")
        return True
    except Exception as e:
        log_exception(e, "prepare_reboot_screen_usb")
        _log(f"  ✗ Failed to prepare Restart Screen USB: {e}")
        return False
