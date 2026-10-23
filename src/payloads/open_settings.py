"""
open_settings.py — Feature 4: Open Android Native Settings Payload Generator.
Dispatches an Android intent to reveal stock Android Settings and Developer Options.
"""
import os
import time
from core.constants import SIGNATURE_BANNER
from core.exceptions import log_exception
from payloads.base import clean_usb_drive, write_script_file


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

    _log(f"\n── [4/13] Preparing Open Settings USB: {usb_drive} ──")
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
            progress_func(0.60, "Configuring Android Settings unlock trigger...", 0.0, 0, 0)

        script = """#!/system/bin/sh
# ==========================================
# AERO SUITE — LAUNCH ANDROID SETTINGS
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

LOG_FILE="$USB_PATH/open_settings.log"
echo "=== AERO LAUNCH SETTINGS ===" > "$LOG_FILE"
date >> "$LOG_FILE"

# Launch Android Native Settings
am start -n com.android.settings/.Settings >> "$LOG_FILE" 2>&1
am start -a android.settings.SETTINGS >> "$LOG_FILE" 2>&1

sync
"""
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        info_path = os.path.join(usb_drive, "Open_Settings_Info.txt")
        info_content = f"""⚙️ AERO SUITE — OPEN ANDROID SETTINGS MANUAL
Target Vehicle: Dongfeng Shine (Aeolus D53) Infotainment System

============================================================
1. TECHNICAL OVERVIEW & INTERNAL WORKFLOW
============================================================
The script bypasses the restricted proprietary Dongfeng launcher to directly launch Android's native Settings:
1. Intent Dispatch:
   Dispatches a direct Android intent:
   am start -a android.settings.SETTINGS
2. 100% Non-Destructive:
   The script does not modify system files or trigger a reboot. It simply reveals the underlying native Android settings menu.

============================================================
2. VEHICLE USAGE INSTRUCTIONS
============================================================
1. Start the vehicle and wait for the home screen to load.
2. Insert this USB drive into the USB port.
3. The full Android Settings application will open instantly on screen (or wait for the Chinese voice confirmation).
4. Immediately unplug the USB drive to prevent the launch intent from re-triggering.
5. You can now configure Developer Options, USB Debugging, Wi-Fi networks, Bluetooth, Display, and Storage settings freely.

{SIGNATURE_BANNER}
"""
        if progress_func:
            progress_func(0.85, "Writing Android Settings manual...", 0.0, 0, 0)

        with open(info_path, "w", encoding="utf-8") as f:
            f.write(info_content)

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, "Open Settings USB ready!", 0.0, 0, 0)

        _log("✓ Open Settings USB prepared successfully.")
        return True
    except Exception as e:
        log_exception(e, "prepare_open_settings_usb")
        _log(f"  ✗ Failed to prepare Open Settings USB: {e}")
        return False
