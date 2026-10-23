"""
open_app.py — Feature 3: Launch Specific Application Payload Generator.
Dispatches an Android intent to launch any installed package directly into the foreground.
"""
import os
import re
import time
from core.constants import SIGNATURE_BANNER
from core.exceptions import log_exception
from payloads.base import clean_usb_drive, write_script_file


def prepare_open_app_usb(
    usb_drive: str,
    package_name: str,
    app_name: str = "",
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """Prepares USB payload to launch a specific application on the vehicle screen if installed."""
    def _log(msg):
        if log_func:
            log_func(msg)

    display_label = app_name or package_name
    _log(f"\n── [3/13] Preparing Open App USB ({display_label}): {usb_drive} ──")
    if not os.path.exists(usb_drive):
        _log(f"  ✗ USB Drive not found: {usb_drive}")
        return False

    if not package_name:
        _log("  ✗ No package name provided to launch.")
        return False

    if cancel_check and cancel_check():
        _log("  ⚠ Operation cancelled by user.")
        return False

    clean_pkg = re.sub(r'[^a-zA-Z0-9._]', '', package_name)

    try:
        clean_usb_drive(usb_drive, log_func, progress_func, cancel_check, start_pct=0.0, end_pct=0.30)
        if cancel_check and cancel_check():
            _log("  ⚠ Operation cancelled by user.")
            return False

        update_dir = os.path.join(usb_drive, "update")
        os.makedirs(update_dir, exist_ok=True)

        if progress_func:
            progress_func(0.60, f"Configuring launch trigger for {display_label}...", 0.0, 0, 0)

        script = f"""#!/system/bin/sh
# ==========================================
# AERO SUITE — LAUNCH SPECIFIC APPLICATION
# Target: {clean_pkg} ({display_label})
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

LOG_FILE="$USB_PATH/open_app.log"
echo "=== AERO OPEN APP START ===" > "$LOG_FILE"
date >> "$LOG_FILE"

TARGET_PKG="{clean_pkg}"
echo "Checking if $TARGET_PKG is installed..." >> "$LOG_FILE"

if pm path "$TARGET_PKG" >/dev/null 2>&1; then
    echo "✓ Package found. Launching $TARGET_PKG..." >> "$LOG_FILE"
    monkey -p "$TARGET_PKG" -c android.intent.category.LAUNCHER 1 >> "$LOG_FILE" 2>&1
else
    echo "⚠ Package $TARGET_PKG is NOT installed on this vehicle." >> "$LOG_FILE"
fi

sync
"""
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        info_path = os.path.join(usb_drive, "Open_App_Info.txt")
        info_content = f"""🚀 AERO SUITE — LAUNCH APPLICATION MANUAL
Target Application: {display_label}
Package Name: {clean_pkg}
Target Vehicle: Dongfeng Shine (Aeolus D53) Infotainment System

============================================================
1. TECHNICAL OVERVIEW & INTERNAL WORKFLOW
============================================================
This payload launches the selected application directly:
1. Existence Verification:
   The script checks if the package exists in PackageManager:
   pm path {clean_pkg}
2. Launch Execution:
   If found, launches the app's default launcher activity into the foreground:
   monkey -p {clean_pkg} -c android.intent.category.LAUNCHER 1
3. Fail-Safe:
   If the package is not installed on the vehicle, the script logs a warning to the USB log and safely exits without errors.

============================================================
2. VEHICLE USAGE INSTRUCTIONS
============================================================
1. Start the vehicle and wait for the screen to turn on.
2. Insert this USB drive into the vehicle USB port.
3. Within a few seconds, {display_label} will launch directly on screen (or wait for the Chinese voice confirmation).
4. Unplug the USB drive immediately.

{SIGNATURE_BANNER}
"""
        if progress_func:
            progress_func(0.85, f"Writing launch manual for {display_label}...", 0.0, 0, 0)

        with open(info_path, "w", encoding="utf-8") as f:
            f.write(info_content)

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, f"Launch {display_label} USB ready!", 0.0, 0, 0)

        _log(f"✓ Open App USB prepared successfully for {display_label}.")
        return True
    except Exception as e:
        log_exception(e, "prepare_open_app_usb")
        _log(f"  ✗ Failed to prepare Open App USB: {e}")
        return False
