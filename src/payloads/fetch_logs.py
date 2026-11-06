"""
fetch_logs.py — Feature 13: System Diagnostic Telemetry & Logs Dump Payload Generator.
Extracts logcat, dmesg, dumpsys, storage partitions, and crash tombstones to USB:/Logs.
"""
import os
import time
from core.constants import SIGNATURE_BANNER
from core.exceptions import log_exception
from core.i18n import t
from payloads.base import clean_usb_drive, write_script_file
from payloads.bash_builder import gen_bash_header, gen_bash_footer
from payloads.manual_generator import generate_info_content, write_payload_manuals


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

    _log(t("logs.prep_usb_header", f"\n── Preparing Fetch Logs USB: {usb_drive} ──", title=t("nav.fetch_logs_title", "Fetch Logs"), drive=usb_drive))
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
            progress_func(0.60, "Configuring logcat & diagnostic dump script...", 0.0, 0, 0)

        script = (
            gen_bash_header("DIAGNOSTIC LOGS EXTRACTION", "fetch_logs.log")
            + """
LOGS_DIR="$USB_PATH/Logs"
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
"""
            + gen_bash_footer(success_status="SUCCESS", with_reboot=False)
        )
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        if progress_func:
            progress_func(0.85, "Writing diagnostic logs manual (HTML)...", 0.0, 0, 0)

        write_payload_manuals(usb_drive, "Fetch_Logs_Info", "fetch_logs")

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, "Fetch Logs USB ready!", 0.0, 0, 0)

        _log(t("logs.prep_usb_success", "✓ Fetch Logs USB prepared successfully.", title=t("nav.fetch_logs_title", "Fetch Logs")))
        return True
    except Exception as e:
        log_exception(e, "prepare_fetch_logs_usb")
        _log(t("logs.prep_failed", "  ✗ Failed to prepare {title} USB: {err}", title=t("nav.fetch_logs_title", "Fetch Logs"), err=str(e)))
        return False
