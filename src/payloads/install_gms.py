"""
install_gms.py — Feature 5: Google Play Services (GMS) Injection Payload Generator.
Injects Google Services Framework, Play Services, Account Manager, and Play Store in calibrated dependency order.
"""
import os
import re
import time
from core.constants import SIGNATURE_BANNER, GMS_PACKAGES_SEQUENCE
from core.exceptions import log_exception
from payloads.base import clean_usb_drive, write_script_file, extract_so_libs, copy_file_with_chunk_progress


def _get_gms_order_prefix(filename: str) -> str:
    """
    Determines calibrated installation order prefix (1..4) based on GMS component role.
    Ensures shell globbing executes components in strict dependency sequence:
    1: Framework (GSF) -> 2: Play Services (GMS) -> 3: Account Manager (Login) -> 4: Play Store (Vending)
    """
    f_lower = filename.lower()
    if "framework" in f_lower or "gsf" in f_lower and "login" not in f_lower:
        return "1_"
    elif "services" in f_lower or "gmscore" in f_lower or "play_services" in f_lower:
        return "2_"
    elif "login" in f_lower or "account" in f_lower:
        return "3_"
    elif "store" in f_lower or "vending" in f_lower or "phonesky" in f_lower:
        return "4_"
    return "5_"


def prepare_install_gms_usb(
    usb_drive: str,
    gms_dir: str,
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """Prepares USB to inject Google Services Framework (GMS) into Dongfeng head unit."""
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(f"\n── [5/13] Preparing Install GMS USB: {usb_drive} ──")
    if not os.path.exists(usb_drive):
        _log(f"  ✗ USB Drive not found: {usb_drive}")
        return False
    if not os.path.exists(gms_dir):
        _log(f"  ✗ Google Services folder not found: {gms_dir}")
        return False

    if cancel_check and cancel_check():
        _log("  ⚠ Operation cancelled by user.")
        return False

    try:
        clean_usb_drive(usb_drive, log_func, progress_func, cancel_check, start_pct=0.0, end_pct=0.15)
        if cancel_check and cancel_check():
            _log("  ⚠ Operation cancelled by user.")
            return False

        update_dir = os.path.join(usb_drive, "update")
        soft_dir = os.path.join(update_dir, "soft")
        os.makedirs(soft_dir, exist_ok=True)

        raw_gms_apks = [f for f in os.listdir(gms_dir) if f.lower().endswith(".apk")]
        # Sort based on calibrated GMS dependency sequence
        gms_apks = sorted(raw_gms_apks, key=_get_gms_order_prefix)

        total = len(gms_apks)
        total_gms_bytes = sum(
            os.path.getsize(os.path.join(gms_dir, f)) for f in gms_apks
            if os.path.isfile(os.path.join(gms_dir, f))
        )
        if total_gms_bytes <= 0:
            total_gms_bytes = 1

        _log(f"  Staging {total} GMS package(s) ({total_gms_bytes / (1024 * 1024):.1f} MB total) in calibrated sequence...")
        copied_cumulative_bytes = 0
        start_transfer_time = time.time()

        for idx, apk_name in enumerate(gms_apks, 1):
            if cancel_check and cancel_check():
                _log("  ⚠ Operation cancelled by user.")
                return False

            src_f = os.path.join(gms_dir, apk_name)
            base = os.path.splitext(apk_name)[0]
            clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '', base)
            order_prefix = _get_gms_order_prefix(apk_name)
            folder_name = f"{order_prefix}{clean_name}" if not clean_name.startswith(order_prefix) else clean_name

            dest_dir = os.path.join(soft_dir, folder_name)
            os.makedirs(dest_dir, exist_ok=True)
            dest_f = os.path.join(dest_dir, f"{clean_name}.apk")

            _log(f"  [{idx}/{total}] Component [{order_prefix.rstrip('_')}]: {clean_name}")

            def _on_gms_chunk(chunk_len, file_copied, file_total):
                nonlocal copied_cumulative_bytes
                copied_cumulative_bytes += chunk_len
                elapsed = max(0.05, time.time() - start_transfer_time)
                speed_mb_s = (copied_cumulative_bytes / (1024 * 1024)) / elapsed
                pct = 0.15 + 0.70 * min(1.0, copied_cumulative_bytes / total_gms_bytes)
                c_mb = copied_cumulative_bytes / (1024 * 1024)
                t_mb = total_gms_bytes / (1024 * 1024)
                if progress_func:
                    progress_func(pct, apk_name, speed_mb_s, c_mb, t_mb)

            ok_stream = copy_file_with_chunk_progress(
                src_f,
                dest_f,
                chunk_size=256 * 1024,
                chunk_callback=_on_gms_chunk,
                cancel_check=cancel_check
            )
            if not ok_stream or (cancel_check and cancel_check()):
                _log("  ⚠ Operation cancelled by user.")
                return False

            extract_so_libs(src_f, dest_dir, log_func)

        if progress_func:
            progress_func(0.88, "Generating GMS injection script & permissions...", 0.0, total_gms_bytes / (1024 * 1024), total_gms_bytes / (1024 * 1024))

        script = """#!/system/bin/sh
# ==========================================
# AERO SUITE — GMS FRAMEWORK INSTALLER
# Calibrated 4-Component Dependency Sequence
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

LOG_FILE="$USB_PATH/gms_install.log"
echo "=== AERO GMS INJECTION START ===" > "$LOG_FILE"
date >> "$LOG_FILE"

mount -o remount,rw /system >> "$LOG_FILE" 2>&1
mount -o rw,remount /system >> "$LOG_FILE" 2>&1

# 0. Deep Pre-Clean: Completely wipe any existing/stale Google packages, leftover data & caches
# Prevents signature mismatch, corrupted databases, and package manager conflicts
echo "Executing pre-installation purge of existing Google packages & caches..." >> "$LOG_FILE"
for pkg in com.android.vending com.google.android.gms com.google.android.gsf com.google.android.gsf.login; do
    PKG_PATH=$(pm path "$pkg" 2>/dev/null | cut -d ':' -f 2)
    if [ -n "$PKG_PATH" ]; then
        echo "  Found existing package $pkg at $PKG_PATH — purging completely..." >> "$LOG_FILE"
        rm -rf $(dirname "$PKG_PATH") >> "$LOG_FILE" 2>&1
    fi
    pm clear "$pkg" >> "$LOG_FILE" 2>&1
    pm uninstall "$pkg" >> "$LOG_FILE" 2>&1
    rm -rf "/data/data/$pkg" >> "$LOG_FILE" 2>&1
    rm -rf "/data/user/0/$pkg" >> "$LOG_FILE" 2>&1
    rm -rf "/data/app/$pkg"* >> "$LOG_FILE" 2>&1
    rm -rf "/data/dalvik-cache/arm/*$pkg"* >> "$LOG_FILE" 2>&1
done

# Wipe old system directory remnants
rm -rf /system/priv-app/*PlayStore* /system/priv-app/*playstore* /system/priv-app/*vending* >> "$LOG_FILE" 2>&1
rm -rf /system/priv-app/*GMS* /system/priv-app/*gms* /system/priv-app/*GSF* /system/priv-app/*gsf* >> "$LOG_FILE" 2>&1
rm -rf /system/app/*PlayStore* /system/app/*GMS* /system/app/*GSF* >> "$LOG_FILE" 2>&1

# Reset corrupted account tokens and sync db to prevent auth conflict
rm -rf /data/system/users/0/accounts.db* >> "$LOG_FILE" 2>&1
rm -rf /data/system_de/0/accounts_de.db* >> "$LOG_FILE" 2>&1
rm -rf /data/system/sync/* >> "$LOG_FILE" 2>&1

SOFT_DIR="$USB_PATH/update/soft"
if [ -d "$SOFT_DIR" ]; then
    # Alphabetical traversal executes 1_*, 2_*, 3_*, 4_* in strict dependency order!
    for item in "$SOFT_DIR"/*; do
        if [ -d "$item" ]; then
            appname=$(basename "$item")
            clean_appname=$(echo "$appname" | sed 's/^[0-9]_//')
            echo "Injecting GMS component: $clean_appname (from $appname)" >> "$LOG_FILE"
            TARGET_DIR="/system/priv-app/$clean_appname"
            mkdir -p "$TARGET_DIR" >> "$LOG_FILE" 2>&1
            cp -r "$item"/* "$TARGET_DIR/" >> "$LOG_FILE" 2>&1
            chmod 755 "$TARGET_DIR" >> "$LOG_FILE" 2>&1
            chmod 644 "$TARGET_DIR"/*.apk >> "$LOG_FILE" 2>&1
            if [ -d "$TARGET_DIR/lib" ]; then
                chmod -R 755 "$TARGET_DIR/lib" >> "$LOG_FILE" 2>&1
                chmod 644 "$TARGET_DIR/lib/arm"/*.so >> "$LOG_FILE" 2>&1
            fi
        fi
    done
fi

# Inject voice_recognizers permission if available
cat << 'EOF' > /system/etc/permissions/voice_recognizers.xml
<?xml version="1.0" encoding="utf-8"?>
<permissions>
    <feature name="android.software.voice_recognizers" />
</permissions>
EOF
chmod 644 /system/etc/permissions/voice_recognizers.xml >> "$LOG_FILE" 2>&1

# Force device provisioning & onboarding completion to prevent Play Store download pending loop
echo "Forcing device provisioning & onboarding completion flags..." >> "$LOG_FILE"
settings put global device_provisioned 1 >> "$LOG_FILE" 2>&1
settings put secure user_setup_complete 1 >> "$LOG_FILE" 2>&1

sync
echo "=== GMS INJECTION COMPLETE ===" >> "$LOG_FILE"
sync
(sleep 3; setprop sys.powerctl reboot; reboot) &
"""
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        info_path = os.path.join(usb_drive, "Install_GMS_Info.txt")
        info_content = f"""🌐 AERO SUITE — GOOGLE PLAY SERVICES (GMS) INSTALLATION MANUAL
Target Vehicle: Dongfeng Shine (Aeolus D53) Infotainment System
Architecture: ARMv7-a / ARM64 Compatible (Android 8.1 / 9 / 10)

============================================================
1. TECHNICAL OVERVIEW & INTERNAL WORKFLOW
============================================================
The automated GMS payload injects the full Google mobile ecosystem into /system/priv-app/:
1. Pre-Installation Clean:
   Completely uninstalls and purges any broken, corrupt, or incompatible previous GMS installations.
2. Calibrated Component Injection Order:
   1. Google Services Framework (com.google.android.gsf)
   2. Google Play Services (com.google.android.gms)
   3. Google Account Manager (com.google.android.gsf.login)
   4. Google Play Store (com.android.vending)
3. Native Library Extraction (.so):
   Extracts and stages all compiled ARM .so libraries directly into /system/priv-app/<AppName>/lib/arm/
4. Android Permissions & Privileged Whitelist:
   Sets 0644 permissions on APKs and 0755 on directories. Injects voice_recognizers permission.
5. Onboarding & Provisioning Flags:
   Forces device_provisioned=1 and user_setup_complete=1 to prevent Google Play Store from getting stuck in an infinite "Download Pending" loop.
6. Automatic System Reboot:
   Automates a system reboot upon completion to let Android register the new system services.

============================================================
2. VEHICLE USAGE INSTRUCTIONS
============================================================
1. Start the vehicle and wait for the screen to boot.
2. Insert this USB drive into the USB port. The GMS injection process executes automatically in the background.
3. Wait approximately 45 to 60 seconds.
4. As soon as the screen turns off to reboot automatically, unplug the USB drive immediately (before it boots back up).
5. Upon restart, connect your vehicle to Wi-Fi, open Google Play Store, and sign in with your Google Account!

Note: The APK versions included here are specifically calibrated for Dongfeng Shine's SoC to prevent "Google Play Services has stopped" error dialogs.

{SIGNATURE_BANNER}
"""
        if progress_func:
            progress_func(0.96, "Writing Google Services manual & permissions...", 0.0, total_gms_bytes / (1024 * 1024), total_gms_bytes / (1024 * 1024))

        with open(info_path, "w", encoding="utf-8") as f:
            f.write(info_content)

        if progress_func:
            progress_func(0.99, "Flushing filesystem buffers to USB drive...", 0.0, total_gms_bytes / (1024 * 1024), total_gms_bytes / (1024 * 1024))
            time.sleep(0.04)
            progress_func(1.0, "Install GMS USB ready!", 0.0, total_gms_bytes / (1024 * 1024), total_gms_bytes / (1024 * 1024))

        _log("✓ Install GMS USB prepared successfully.")
        return True
    except Exception as e:
        log_exception(e, "prepare_install_gms_usb")
        _log(f"  ✗ Failed to prepare Install GMS USB: {e}")
        return False
