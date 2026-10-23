"""
disable_launcher.py — Feature 7: Freeze / Disable Stock OEM Launcher Payload Generator.
Freezes com.qinggan.app.launcher to hand over full home screen control to custom launchers.
"""
import os
import time
from core.constants import SIGNATURE_BANNER, FACTORY_LAUNCHER_PKG
from core.exceptions import log_exception
from payloads.base import clean_usb_drive, write_script_file


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

    _log(f"\n── [7/13] Preparing Disable Factory Launcher USB: {usb_drive} ──")
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
            progress_func(0.60, "Generating disable launcher payload...", 0.0, 0, 0)

        script = f"""#!/system/bin/sh
# ==========================================
# AERO SUITE — DISABLE FACTORY LAUNCHER
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

LOG_FILE="$USB_PATH/disable_launcher.log"
echo "=== AERO DISABLE LAUNCHER START ===" > "$LOG_FILE"
date >> "$LOG_FILE"

mount -o remount,rw /system >> "$LOG_FILE" 2>&1
mount -o rw,remount /system >> "$LOG_FILE" 2>&1

echo "Freezing stock OEM launcher ({FACTORY_LAUNCHER_PKG})..." >> "$LOG_FILE"
pm disable {FACTORY_LAUNCHER_PKG} >> "$LOG_FILE" 2>&1

mount -o remount,ro /system >> "$LOG_FILE" 2>&1
echo "=== LAUNCHER DISABLED — REBOOTING DIRECTLY TO ANDROID ===" >> "$LOG_FILE"
date >> "$LOG_FILE"
sync
sleep 2
sync
setprop sys.powerctl reboot || reboot -f || reboot
"""
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        info_path = os.path.join(usb_drive, "Disable_Launcher_Info.txt")
        info_content = f"""🚫 AERO SUITE — DISABLE FACTORY LAUNCHER MANUAL
Target Vehicle: Dongfeng Shine (Aeolus D53) Infotainment System

============================================================
1. TECHNICAL OVERVIEW & INTERNAL WORKFLOW
============================================================
This payload safely freezes (disables) the factory proprietary launcher:
1. Package Manager Freeze:
   Executes: pm disable {FACTORY_LAUNCHER_PKG}
2. Clean Custom Home Handoff:
   Allows custom launchers (like AGAMA Car Launcher or Nova) to function as the exclusive default home screen without being interrupted by the stock UI.
3. 100% Reversible:
   This change is non-destructive and can be re-enabled at any time using the "Enable Factory Launcher" feature.

============================================================
2. VEHICLE USAGE INSTRUCTIONS
============================================================
1. Start the vehicle and wait for the screen to boot.
2. Insert this USB drive into the USB port.
3. Wait 15 to 30 seconds (or until you hear the vehicle's native Chinese voice announcement / صوت التنبيه الصيني الصادر من النظام).
4. Immediately unplug the USB drive.
5. Press the physical or virtual Home button to verify your custom launcher is now primary.

{SIGNATURE_BANNER}
"""
        if progress_func:
            progress_func(0.85, "Writing disable launcher manual...", 0.0, 0, 0)

        with open(info_path, "w", encoding="utf-8") as f:
            f.write(info_content)

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, "Disable Launcher USB ready!", 0.0, 0, 0)

        _log("✓ Disable Launcher USB prepared successfully.")
        return True
    except Exception as e:
        log_exception(e, "prepare_disable_launcher_usb")
        _log(f"  ✗ Failed to prepare Disable Launcher USB: {e}")
        return False
