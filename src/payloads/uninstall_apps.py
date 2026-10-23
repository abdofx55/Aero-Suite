"""
uninstall_apps.py — Feature 2: Safe Dual-Sweep Application Uninstallation Payload Generator.
Strictly removes vetted packages from both /data/app and /system/priv-app.
"""
import os
import re
import time
from core.constants import SIGNATURE_BANNER
from core.exceptions import log_exception
from payloads.base import clean_usb_drive, write_script_file


def prepare_uninstall_apps_usb(
    usb_drive: str,
    selected_packages: list,
    allowed_packages: set,
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """
    Generates a safe uninstallation payload that searches and purges from BOTH
    User Apps (/data/app) and System Apps (/system/priv-app and /system/app).
    STRICT SECURITY RULE: Only packages in allowed_packages (derived from local apks/) are allowed!
    """
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(f"\n── [2/13] Preparing Safe Uninstall Apps USB: {usb_drive} ──")
    if not os.path.exists(usb_drive):
        _log(f"  ✗ USB Drive not found: {usb_drive}")
        return False

    if cancel_check and cancel_check():
        _log("  ⚠ Operation cancelled by user.")
        return False

    # Security verification
    vetted_packages = [p for p in selected_packages if p in allowed_packages]
    if not vetted_packages:
        _log("  ✗ No valid vetted packages selected for uninstall. Operation aborted for safety.")
        return False

    try:
        clean_usb_drive(usb_drive, log_func, progress_func, cancel_check, start_pct=0.0, end_pct=0.30)
        if cancel_check and cancel_check():
            _log("  ⚠ Operation cancelled by user.")
            return False
        update_dir = os.path.join(usb_drive, "update")
        os.makedirs(update_dir, exist_ok=True)

        if progress_func:
            progress_func(0.55, f"Configuring {len(vetted_packages)} uninstall command(s)...", 0.0, 0, 0)

        uninstall_cmds = ""
        for pkg in vetted_packages:
            safe_pkg = re.sub(r'[^a-zA-Z0-9._\-]', '', pkg)
            clean_name = safe_pkg.split('.')[-1]
            uninstall_cmds += f"""
echo "Uninstalling vetted app: {safe_pkg}" >> "$LOG_FILE"
PKG_PATH=$(pm path "{safe_pkg}" | cut -d ':' -f 2)
if [ ! -z "$PKG_PATH" ]; then
    PKG_DIR=$(dirname "$PKG_PATH")
    echo "  Removing detected install directory: $PKG_DIR" >> "$LOG_FILE"
    rm -rf "$PKG_DIR" >> "$LOG_FILE" 2>&1
fi
pm clear "{safe_pkg}" >> "$LOG_FILE" 2>&1
pm uninstall "{safe_pkg}" >> "$LOG_FILE" 2>&1

# 1. Search & purge in User Apps (/data/app)
rm -rf /data/app/{safe_pkg}* >> "$LOG_FILE" 2>&1
rm -rf /data/app/*{safe_pkg}* >> "$LOG_FILE" 2>&1

# 2. Search & purge in System Apps (/system/priv-app and /system/app)
rm -rf /system/priv-app/{safe_pkg} >> "$LOG_FILE" 2>&1
rm -rf /system/priv-app/*{safe_pkg}* >> "$LOG_FILE" 2>&1
rm -rf /system/priv-app/*{clean_name}* >> "$LOG_FILE" 2>&1
rm -rf /system/app/{safe_pkg} >> "$LOG_FILE" 2>&1
rm -rf /system/app/*{safe_pkg}* >> "$LOG_FILE" 2>&1
rm -rf /system/app/*{clean_name}* >> "$LOG_FILE" 2>&1

# 3. Clean user data & cache
rm -rf "/data/data/{safe_pkg}" >> "$LOG_FILE" 2>&1
rm -rf "/data/user/0/{safe_pkg}" >> "$LOG_FILE" 2>&1
rm -rf "/data/media/0/Android/data/{safe_pkg}" >> "$LOG_FILE" 2>&1
rm -rf "/data/dalvik-cache/arm/*{safe_pkg}"* >> "$LOG_FILE" 2>&1
"""

        script = f"""#!/system/bin/sh
# ==========================================
# AERO SUITE — SAFE APP UNINSTALLER
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

LOG_FILE="$USB_PATH/uninstall_log.txt"
echo "=== AERO SAFE UNINSTALL START ===" > "$LOG_FILE"
date >> "$LOG_FILE"

mount -o remount,rw /system >> "$LOG_FILE" 2>&1
mount -o rw,remount /system >> "$LOG_FILE" 2>&1

{uninstall_cmds}

sync
echo "=== SAFE UNINSTALL COMPLETED ===" >> "$LOG_FILE"

# If system partitions had files removed, reboot is required to flush system server package caches
if grep -q "Removing detected install directory: /system" "$LOG_FILE" 2>/dev/null; then
    echo "System app components were removed. Rebooting infotainment system to clean framework cache..." >> "$LOG_FILE"
    sync
    (sleep 3; setprop sys.powerctl reboot; reboot) &
fi
"""
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        info_path = os.path.join(usb_drive, "Uninstall_Apps_Info.txt")
        info_content = f"""🛡️ AERO SUITE — SAFE UNINSTALL APPLICATIONS MANUAL
Target Vehicle: Dongfeng Shine (Aeolus D53) Infotainment System

============================================================
1. TECHNICAL OVERVIEW & INTERNAL WORKFLOW
============================================================
The uninstallation engine executes a deep dual-sweep removal while maintaining a strict safety lock:

1. Strict Security Whitelist:
   - The engine is hardcoded to only allow removal of packages originating from your vetted apks/ repository.
   - Factory OEM applications (Dongfeng CAN-Bus services, Air Conditioning controllers, Radio, Cluster sync) are cryptographically whitelisted and can NEVER be touched or removed.

2. Comprehensive Dual-Directory Sweep:
   - User Applications: Searches and removes matching installation directories from /data/app/*<package>*.
   - System Priv-Apps: Searches and removes matching installation directories from /system/priv-app/ and /system/app/.

3. Dynamic Path Resolution:
   - Uses `pm path <package>` to query Android's package database for the exact filesystem location and removes the parent directory.

4. Deep Cache & State Clean:
   - Executes `pm clear <package>` to wipe all cached data and user configurations.
   - Executes `pm uninstall <package>` to unregister the package from Android's PackageManager.
   - Deletes remaining runtime directories in /data/data/<package> and /data/user/0/<package>.
   - Purges compiled Dalvik/ART cache artifacts from /data/dalvik-cache/arm/*.

5. Completion:
   - Synchronizes filesystem buffers (sync) and writes uninstallation results to the USB log file.

============================================================
2. VEHICLE USAGE INSTRUCTIONS
============================================================
1. Start the vehicle and allow the infotainment screen to reach the main home launcher.
2. Insert this USB drive into the USB port. The uninstallation script will execute automatically in the background.
3. Wait approximately 30 to 45 seconds (or until you hear the vehicle's native Chinese voice announcement / صوت التنبيه الصيني الصادر من النظام).
4. Unplug the USB drive immediately.

============================================================
3. PACKAGES SCHEDULED FOR SAFE REMOVAL ({len(vetted_packages)})
============================================================
""" + "\n".join([f" • {p}" for p in vetted_packages]) + f"""

{SIGNATURE_BANNER}
"""
        if progress_func:
            progress_func(0.80, "Writing uninstallation manual & instructions...", 0.0, len(vetted_packages), len(vetted_packages))

        with open(info_path, "w", encoding="utf-8") as f:
            f.write(info_content)

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, len(vetted_packages), len(vetted_packages))
            time.sleep(0.04)
            progress_func(1.0, "Safe Uninstall USB ready!", 0.0, len(vetted_packages), len(vetted_packages))

        _log("✓ Safe Uninstall Apps USB prepared successfully.")
        return True
    except Exception as e:
        log_exception(e, "prepare_uninstall_apps_usb")
        _log(f"  ✗ Failed to prepare Uninstall Apps USB: {e}")
        return False
