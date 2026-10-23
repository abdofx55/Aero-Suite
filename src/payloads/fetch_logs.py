"""
fetch_logs.py — Feature 13: System Diagnostic Telemetry & Logs Dump Payload Generator.
Extracts logcat, dmesg, dumpsys, storage partitions, and crash tombstones to USB:/AeroLogs_<timestamp>.
"""
import os
import time
from core.constants import SIGNATURE_BANNER
from core.exceptions import log_exception
from core.i18n import t
from payloads.base import clean_usb_drive, write_script_file


def prepare_fetch_logs_usb(
    usb_drive: str,
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """Prepares USB to extract logcat, dmesg, and diagnostic dumps from car."""
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(t("logs.prep_usb_header", f"\n── [13/13] Preparing Fetch Logs USB: {usb_drive} ──", num="13", title=t("nav.fetch_logs_title", "Fetch Logs"), drive=usb_drive))
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
            progress_func(0.60, "Configuring logcat & diagnostic dump script...", 0.0, 0, 0)

        script = """#!/system/bin/sh
# ==========================================
# AERO SUITE — DIAGNOSTIC LOGS EXTRACTION
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

LOGS_DIR="$USB_PATH/AeroLogs_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOGS_DIR"

logcat -d -v time > "$LOGS_DIR/logcat.txt" 2>&1
dmesg > "$LOGS_DIR/dmesg.txt" 2>&1
getprop > "$LOGS_DIR/getprop.txt" 2>&1
dumpsys package > "$LOGS_DIR/dumpsys_package.txt" 2>&1
dumpsys meminfo > "$LOGS_DIR/dumpsys_meminfo.txt" 2>&1
df -h > "$LOGS_DIR/storage_df.txt" 2>&1

if [ -d "/data/tombstones" ]; then
    mkdir -p "$LOGS_DIR/tombstones"
    cp -r /data/tombstones/* "$LOGS_DIR/tombstones/" 2>/dev/null
fi
if [ -d "/data/anr" ]; then
    mkdir -p "$LOGS_DIR/anr"
    cp -r /data/anr/* "$LOGS_DIR/anr/" 2>/dev/null
fi
if [ -d "/cache/recovery" ]; then
    mkdir -p "$LOGS_DIR/recovery"
    cp -r /cache/recovery/* "$LOGS_DIR/recovery/" 2>/dev/null
fi

sync
"""
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        info_path = os.path.join(usb_drive, "Fetch_Logs_Info.txt")
        info_content = f"""📋 AERO SUITE — DIAGNOSTIC LOGS EXTRACTION MANUAL
Target Vehicle: Dongfeng Shine (Aeolus D53) Infotainment System

============================================================
1. TECHNICAL OVERVIEW & INTERNAL WORKFLOW
============================================================
The diagnostic tool extracts comprehensive system telemetry from the vehicle into:
USB:/AeroLogs_<YYYYMMDD_HHMMSS>

Extracted Diagnostic Data:
1. Android Runtime Logcat:
   logcat -d -v time > logcat.txt (timestamped application and system service events).
2. Kernel Ring Buffer:
   dmesg > dmesg.txt (kernel hardware drivers, CPU, and USB bus diagnostics).
3. System Properties:
   getprop > getprop.txt (software version, build ID, and OEM vendor parameters).
4. Package Manager State:
   dumpsys package > dumpsys_package.txt (installed packages, permissions, and paths).
5. Memory Allocation State:
   dumpsys meminfo > dumpsys_meminfo.txt (RAM usage, process footprints, and leaks).
6. Filesystem Storage:
   df -h > storage_df.txt (disk partition usage across /system, /data, /cache).
7. Crash & ANR Dumps:
   Copies crash tombstones (/data/tombstones) and Application Not Responding logs (/data/anr).
8. Safe & Read-Only:
   The extraction process is 100% read-only and does not modify any system files.

============================================================
2. VEHICLE USAGE INSTRUCTIONS
============================================================
1. Start the vehicle and wait for the screen to turn on.
2. Insert this USB drive into the USB port. The logs extraction takes 15 to 30 seconds.
3. When you hear the vehicle's native Chinese voice announcement (صوت التنبيه الصيني الصادر من النظام) or after 30 seconds have elapsed, unplug the USB drive.
4. Plug the USB drive into your PC to inspect the diagnostic logs.

{SIGNATURE_BANNER}
"""
        if progress_func:
            progress_func(0.85, "Writing diagnostic logs manual...", 0.0, 0, 0)

        with open(info_path, "w", encoding="utf-8") as f:
            f.write(info_content)

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, "Fetch Logs USB ready!", 0.0, 0, 0)

        _log(t("logs.prep_usb_success", "✓ Fetch Logs USB prepared successfully.", title=t("nav.fetch_logs_title", "Fetch Logs")))
        return True
    except Exception as e:
        log_exception(e, "prepare_fetch_logs_usb")
        _log(f"  ✗ Failed to prepare Fetch Logs USB: {e}")
        return False
