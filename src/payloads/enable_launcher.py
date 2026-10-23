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

    _log(t("logs.prep_usb_header", f"\n── [8/13] Preparing Enable Factory Launcher USB: {usb_drive} ──", num="8", title=t("nav.enable_launcher_title", "Enable Launcher"), drive=usb_drive))
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
            progress_func(0.60, "Generating enable launcher payload...", 0.0, 0, 0)

        script = f"""#!/system/bin/sh
# ==========================================
# AERO SUITE — ENABLE FACTORY LAUNCHER
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

LOG_FILE="$USB_PATH/enable_launcher.log"
echo "=== AERO ENABLE LAUNCHER START ===" > "$LOG_FILE"
date >> "$LOG_FILE"

mount -o remount,rw /system >> "$LOG_FILE" 2>&1
mount -o rw,remount /system >> "$LOG_FILE" 2>&1

echo "Unfreezing stock OEM launcher ({FACTORY_LAUNCHER_PKG})..." >> "$LOG_FILE"
pm enable {FACTORY_LAUNCHER_PKG} >> "$LOG_FILE" 2>&1

mount -o remount,ro /system >> "$LOG_FILE" 2>&1
echo "=== LAUNCHER ENABLED — REBOOTING DIRECTLY TO ANDROID ===" >> "$LOG_FILE"
date >> "$LOG_FILE"
sync
sleep 2
sync
setprop sys.powerctl reboot || reboot -f || reboot
"""
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        info_path = os.path.join(usb_drive, "Enable_Launcher_Info.txt")
        info_content = f"""✅ AERO SUITE — ENABLE FACTORY LAUNCHER MANUAL
Target Vehicle: Dongfeng Shine (Aeolus D53) Infotainment System

============================================================
1. TECHNICAL OVERVIEW & INTERNAL WORKFLOW
============================================================
This payload restores and unfreezes the stock factory launcher:
1. Package Manager Unfreeze:
   Executes: pm enable {FACTORY_LAUNCHER_PKG}
2. Restores Factory Home Screen:
   Restores the original Dongfeng Qinggan OS launcher as an active home candidate.
3. Dealership & Inspection Safe:
   Leaves no residual restrictions on the stock launcher.

============================================================
2. VEHICLE USAGE INSTRUCTIONS
============================================================
1. Start the vehicle and wait for the screen to turn on.
2. Insert this USB drive into the USB port.
3. Wait 15 to 30 seconds (or until you hear the vehicle's native Chinese voice announcement / صوت التنبيه الصيني الصادر من النظام).
4. Immediately unplug the USB drive.
5. The original factory launcher is now fully active.

{SIGNATURE_BANNER}
"""
        if progress_func:
            progress_func(0.85, "Writing enable launcher manual...", 0.0, 0, 0)

        with open(info_path, "w", encoding="utf-8") as f:
            f.write(info_content)

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, "Enable Launcher USB ready!", 0.0, 0, 0)

        _log(t("logs.prep_usb_success", "✓ Enable Launcher USB prepared successfully.", title=t("nav.enable_launcher_title", "Enable Launcher")))
        return True
    except Exception as e:
        log_exception(e, "prepare_enable_launcher_usb")
        _log(f"  ✗ Failed to prepare Enable Launcher USB: {e}")
        return False
