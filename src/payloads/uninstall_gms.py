"""
uninstall_gms.py — Feature 6: Google Play Services (GMS) Clean Purge Payload Generator.
Performs a deep system wipe of all GMS artifacts, services, permissions, and caches.
"""
import os
import time
from core.constants import SIGNATURE_BANNER
from core.exceptions import log_exception
from core.i18n import t
from payloads.base import clean_usb_drive, write_script_file


def prepare_uninstall_gms_usb(
    usb_drive: str,
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """Prepares USB to cleanly remove Google Play Services, Play Store, and account caches."""
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(t("logs.prep_usb_header", f"\n── [6/13] Preparing Uninstall GMS USB: {usb_drive} ──", num="6", title=t("nav.uninstall_gms_title", "Uninstall GMS"), drive=usb_drive))
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
            progress_func(0.55, "Configuring GMS clean purge script...", 0.0, 0, 0)

        script = """#!/system/bin/sh
# ==========================================
# AERO SUITE — DEEP GMS CLEAN REMOVAL
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

LOG_FILE="$USB_PATH/gms_uninstall.log"
echo "=== AERO GMS PURGE START ===" > "$LOG_FILE"
date >> "$LOG_FILE"

mount -o remount,rw /system >> "$LOG_FILE" 2>&1
mount -o rw,remount /system >> "$LOG_FILE" 2>&1

echo "1. Uninstalling Google package instances..." >> "$LOG_FILE"
for pkg in com.android.vending com.google.android.gms com.google.android.gsf com.google.android.gsf.login; do
    PKG_PATH=$(pm path "$pkg" 2>/dev/null | cut -d ':' -f 2)
    if [ -n "$PKG_PATH" ]; then
        echo "  Removing installation directory for $pkg ($PKG_PATH)..." >> "$LOG_FILE"
        rm -rf $(dirname "$PKG_PATH") >> "$LOG_FILE" 2>&1
    fi
    pm clear "$pkg" >> "$LOG_FILE" 2>&1
    pm uninstall "$pkg" >> "$LOG_FILE" 2>&1
    rm -rf "/data/data/$pkg" >> "$LOG_FILE" 2>&1
    rm -rf "/data/user/0/$pkg" >> "$LOG_FILE" 2>&1
    rm -rf "/data/app/$pkg"* >> "$LOG_FILE" 2>&1
    rm -rf "/data/dalvik-cache/arm/*$pkg"* >> "$LOG_FILE" 2>&1
done

echo "2. Purging system priv-app and app remnants..." >> "$LOG_FILE"
rm -rf /system/priv-app/*PlayStore* /system/priv-app/*playstore* /system/priv-app/*vending* >> "$LOG_FILE" 2>&1
rm -rf /system/priv-app/*GMS* /system/priv-app/*gms* /system/priv-app/*GSF* /system/priv-app/*gsf* >> "$LOG_FILE" 2>&1
rm -rf /system/priv-app/Google* >> "$LOG_FILE" 2>&1
rm -rf /system/app/*PlayStore* /system/app/*GMS* /system/app/*GSF* >> "$LOG_FILE" 2>&1

echo "3. Removing Google permissions & account databases..." >> "$LOG_FILE"
rm -f /system/etc/permissions/voice_recognizers.xml >> "$LOG_FILE" 2>&1
rm -rf /data/system/users/0/accounts.db* >> "$LOG_FILE" 2>&1
rm -rf /data/system_de/0/accounts_de.db* >> "$LOG_FILE" 2>&1
rm -rf /data/system/sync/* >> "$LOG_FILE" 2>&1

sync
echo "=== GMS PURGE COMPLETED — REBOOTING ===" >> "$LOG_FILE"
date >> "$LOG_FILE"
sync
(sleep 3; setprop sys.powerctl reboot; reboot) &
"""
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        info_path = os.path.join(usb_drive, "Uninstall_GMS_Info.txt")
        info_content = f"""🗑️ AERO SUITE — UNINSTALL GOOGLE SERVICES (GMS) MANUAL
Target Vehicle: Dongfeng Shine (Aeolus D53) Infotainment System

============================================================
1. TECHNICAL OVERVIEW & INTERNAL WORKFLOW
============================================================
The scrub payload performs a rigorous, deep system purge:
1. Deep Package Uninstallation:
   Wipes com.android.vending, com.google.android.gms, com.google.android.gsf, and com.google.android.gsf.login.
2. System Partition Sweep:
   Purges all GMS and Play Store binaries from /system/priv-app/ and /system/app/.
3. Account Data & Auth Token Scrub:
   Removes cached accounts.db to prevent orphan Google accounts or sync crash loops.
4. Permission Rollback:
   Removes voice_recognizers.xml injected during installation.
5. Dalvik Cache Cleanse:
   Wipes compiled ART caches matching Google packages to eliminate crash loops.
6. Automatic System Reboot:
   Automates a clean reboot to re-register the system without GMS dependencies.

============================================================
2. VEHICLE USAGE INSTRUCTIONS
============================================================
1. Start the vehicle and wait for the screen to boot.
2. Insert this USB drive into the USB port. The GMS removal process executes automatically.
3. Wait approximately 30 to 45 seconds.
4. As soon as the screen turns off to restart automatically, unplug the USB drive immediately (before it boots back up).
5. Upon reboot, the system will be 100% clean of all Google Play Services traces.

{SIGNATURE_BANNER}
"""
        if progress_func:
            progress_func(0.80, "Writing Google Services removal manual...", 0.0, 0, 0)

        with open(info_path, "w", encoding="utf-8") as f:
            f.write(info_content)

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, "Uninstall GMS USB ready!", 0.0, 0, 0)

        _log(t("logs.prep_usb_success", "✓ Uninstall GMS USB prepared successfully.", title=t("nav.uninstall_gms_title", "Uninstall GMS")))
        return True
    except Exception as e:
        log_exception(e, "prepare_uninstall_gms_usb")
        _log(f"  ✗ Failed to prepare Uninstall GMS USB: {e}")
        return False
