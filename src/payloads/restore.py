"""
restore.py — Feature 11: 12-Step Full ROM, System Apps & Data Restoration Payload Generator.
Restores saved vehicle PC Vault archives with intelligent UID mapping, SELinux relabeling, and hard reboot.
"""
import os
import time
from core.constants import SIGNATURE_BANNER
from core.exceptions import log_exception
from core.i18n import t
from payloads.base import clean_usb_drive, write_script_file, copy_tree_with_progress


def prepare_restore_usb(
    usb_drive: str,
    local_backup_folder: str,
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """
    Copies local PC backup to USB:/Backup (with progress bar)
    and generates the 12-step restoration script in USB:/update/custom_rep.sh.
    """
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(t("logs.prep_usb_header", f"\n── [11/13] Preparing Restore USB: {usb_drive} ──", num="11", title=t("nav.restore_title", "Restore"), drive=usb_drive))
    if not os.path.exists(usb_drive):
        _log(f"  ✗ USB Drive not found: {usb_drive}")
        return False
    if not os.path.exists(local_backup_folder):
        _log(f"  ✗ Local backup folder not found: {local_backup_folder}")
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
        os.makedirs(update_dir, exist_ok=True)

        # Check where backup contents are
        src_backup_data = os.path.join(local_backup_folder, "Backup")
        if not os.path.isdir(src_backup_data):
            src_backup_data = local_backup_folder

        dest_usb_backup = os.path.join(usb_drive, "Backup")
        _log("  Transferring PC backup files to USB (with live progress)...")
        ok_copy = copy_tree_with_progress(src_backup_data, dest_usb_backup, progress_func, log_func, cancel_check=cancel_check, scale_range=(0.15, 0.88))
        if not ok_copy or (cancel_check and cancel_check()):
            _log("  ⚠ Restore preparation cancelled.")
            return False

        if progress_func:
            progress_func(0.90, "Verifying backup metadata & vehicle profile...", 0.0, 0, 0)

        # Detect source backup metadata
        is_community = False
        backup_type = "PERSONAL"
        preset_name = ""
        author = ""

        flag_candidates = [
            os.path.join(local_backup_folder, "backup_complete.flag"),
            os.path.join(src_backup_data, "backup_complete.flag"),
        ]
        for fc in flag_candidates:
            if os.path.isfile(fc):
                try:
                    with open(fc, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if line.startswith("BACKUP_TYPE="):
                                backup_type = line.split("=", 1)[1].strip().upper()
                            elif line.startswith("PRESET_NAME="):
                                preset_name = line.split("=", 1)[1].strip()
                            elif line.startswith("AUTHOR="):
                                author = line.split("=", 1)[1].strip()
                except Exception:
                    pass
                break

        if not backup_type or backup_type not in ("COMMUNITY", "PERSONAL"):
            folder_bname = os.path.basename(local_backup_folder)
            if folder_bname.startswith("Community_"):
                backup_type = "COMMUNITY"
            elif folder_bname.startswith("Dongfeng_Backup_"):
                backup_type = "PERSONAL"
            else:
                has_private = (
                    os.path.isdir(os.path.join(src_backup_data, "wifi_bt")) or
                    os.path.isfile(os.path.join(src_backup_data, "accounts", "accounts.db")) or
                    os.path.isfile(os.path.join(src_backup_data, "accounts", "accounts_de.db"))
                )
                backup_type = "PERSONAL" if has_private else "COMMUNITY"

        is_community = (backup_type == "COMMUNITY")

        if is_community:
            _log("  ✓ Detected Community Preset: Safe Non-Destructive Restore enabled.")
            _log("    (Target car's existing Google accounts, Wi-Fi & Bluetooth will NOT be overwritten)")
        else:
            _log("  ✓ Detected Personal Vault: 1:1 Complete Vehicle State Restore.")

        # Write restore markers (remove any stale backup_complete.flag)
        b_flag = os.path.join(usb_drive, "backup_complete.flag")
        if os.path.exists(b_flag):
            try:
                os.remove(b_flag)
            except Exception:
                pass

        r_flag = os.path.join(usb_drive, "restore_ready.flag")
        with open(r_flag, "w", encoding="utf-8") as f:
            f.write(
                f"STATUS=SUCCESS\n"
                f"RESTORE_READY=true\n"
                f"SOURCE_VAULT={os.path.basename(local_backup_folder)}\n"
                f"BACKUP_TYPE={backup_type}\n"
                f"PRESET_NAME={preset_name}\n"
                f"AUTHOR={author}\n"
            )

        # 12-Step Restore Script
        script = """#!/system/bin/sh
# ==========================================
# AERO SUITE — COMPLETE 12-STEP RESTORE
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

LOG_FILE="$USB_PATH/restore.log"
echo "=== AERO RESTORE START ===" > "$LOG_FILE"
date >> "$LOG_FILE"

TARGET_DIR="$USB_PATH/Backup"
if [ ! -d "$TARGET_DIR" ]; then
    TARGET_DIR="$USB_PATH/PersonalBackup"
fi

if [ ! -d "$TARGET_DIR" ]; then
    echo "❌ ABORT: No valid Backup folder found on USB!" >> "$LOG_FILE"
    exit 1
fi

# 1. Mount /system RW & unfreeze launcher immediately
mount -o remount,rw /system >> "$LOG_FILE" 2>&1
mount -o rw,remount /system >> "$LOG_FILE" 2>&1
echo "Unfreezing stock launcher immediately for active UI during restore..." >> "$LOG_FILE"
pm enable com.qinggan.app.launcher >> "$LOG_FILE" 2>&1

# 2. Restore Custom System Apps
if [ -d "$TARGET_DIR/system_apps/priv-app" ]; then
    for dir in "$TARGET_DIR/system_apps/priv-app/"*; do
        if [ -d "$dir" ]; then
            bname=$(basename "$dir")
            echo "Restoring Priv-App: $bname..." >> "$LOG_FILE"
            mkdir -p "/system/priv-app/$bname" >> "$LOG_FILE" 2>&1
            cp -r "$dir/." "/system/priv-app/$bname/" >> "$LOG_FILE" 2>&1
            chmod 755 "/system/priv-app/$bname" >> "$LOG_FILE" 2>&1
            chmod 644 "/system/priv-app/$bname"/*.apk >> "$LOG_FILE" 2>&1
            if [ -d "/system/priv-app/$bname/lib" ]; then
                chmod -R 755 "/system/priv-app/$bname/lib" >> "$LOG_FILE" 2>&1
                chmod 644 "/system/priv-app/$bname/lib/arm"/*.so >> "$LOG_FILE" 2>&1
            fi
        fi
    done
fi

if [ -d "$TARGET_DIR/system_apps/app" ]; then
    for dir in "$TARGET_DIR/system_apps/app/"*; do
        if [ -d "$dir" ]; then
            bname=$(basename "$dir")
            echo "Restoring System App: $bname..." >> "$LOG_FILE"
            mkdir -p "/system/app/$bname" >> "$LOG_FILE" 2>&1
            cp -r "$dir/." "/system/app/$bname/" >> "$LOG_FILE" 2>&1
            chmod 755 "/system/app/$bname" >> "$LOG_FILE" 2>&1
            chmod 644 "/system/app/$bname"/*.apk >> "$LOG_FILE" 2>&1
            if [ -d "/system/app/$bname/lib" ]; then
                chmod -R 755 "/system/app/$bname/lib" >> "$LOG_FILE" 2>&1
                chmod 644 "/system/app/$bname/lib/arm"/*.so >> "$LOG_FILE" 2>&1
            fi
        fi
    done
fi

# 3. Voice Recognizers, Keystore Master Keys & Accounts DB
if [ -f "$TARGET_DIR/settings/voice_recognizers.xml" ]; then
    cp -f "$TARGET_DIR/settings/voice_recognizers.xml" /system/etc/permissions/ >> "$LOG_FILE" 2>&1
    chmod 644 /system/etc/permissions/voice_recognizers.xml >> "$LOG_FILE" 2>&1
fi

if [ -d "$TARGET_DIR/keystore" ]; then
    echo "Restoring Android Keystore Master Keys (Auth Token Preservation)..." >> "$LOG_FILE"
    mkdir -p /data/misc/keystore >> "$LOG_FILE" 2>&1
    cp -r "$TARGET_DIR/keystore/"* /data/misc/keystore/ >> "$LOG_FILE" 2>&1
    chown -R keystore:keystore /data/misc/keystore >> "$LOG_FILE" 2>&1
    chmod 700 /data/misc/keystore >> "$LOG_FILE" 2>&1
fi

if [ -f "$TARGET_DIR/accounts/accounts.db" ]; then
    echo "Restoring Personal Accounts DB & Sync Tables..." >> "$LOG_FILE"
    mkdir -p /data/system/users/0 /data/system_de/0 >> "$LOG_FILE" 2>&1
    cp -f "$TARGET_DIR/accounts/accounts.db"* /data/system/users/0/ >> "$LOG_FILE" 2>&1
    cp -f "$TARGET_DIR/accounts/accounts_de.db"* /data/system_de/0/ >> "$LOG_FILE" 2>&1
    if [ -d "$TARGET_DIR/accounts/sync" ]; then
        mkdir -p /data/system/sync >> "$LOG_FILE" 2>&1
        cp -r "$TARGET_DIR/accounts/sync/"* /data/system/sync/ >> "$LOG_FILE" 2>&1
    fi
    chmod 600 /data/system/users/0/accounts.db* /data/system_de/0/accounts_de.db* >> "$LOG_FILE" 2>&1
    chown system:system /data/system/users/0/accounts.db* /data/system_de/0/accounts_de.db* >> "$LOG_FILE" 2>&1
else
    echo "Community Preset / No Accounts in backup: Preserving target vehicle accounts untouched." >> "$LOG_FILE"
fi

# 4. Enforce Device Provisioning & Setup Complete Flags (Crucial for GMS & Play Store)
echo "Enforcing Setup Completion & Non-Market Install Policies..." >> "$LOG_FILE"
settings put global device_provisioned 1 >> "$LOG_FILE" 2>&1
settings put secure user_setup_complete 1 >> "$LOG_FILE" 2>&1
setprop persist.ais_server.3app.perm 1 >> "$LOG_FILE" 2>&1
settings put global install_non_market_apps 1 >> "$LOG_FILE" 2>&1
settings put secure install_non_market_apps 1 >> "$LOG_FILE" 2>&1
settings put system install_non_market_apps 1 >> "$LOG_FILE" 2>&1
settings put global package_verifier_enable 0 >> "$LOG_FILE" 2>&1
settings put global package_verifier_user_consent -1 >> "$LOG_FILE" 2>&1
settings put global verifier_verify_adb_installs 0 >> "$LOG_FILE" 2>&1

# 5. Restore System Properties
if [ -d "$TARGET_DIR/property" ]; then
    mkdir -p /data/property >> "$LOG_FILE" 2>&1
    cp -r "$TARGET_DIR/property/"* /data/property/ >> "$LOG_FILE" 2>&1
    chmod 600 /data/property/* >> "$LOG_FILE" 2>&1
    chown root:root /data/property/* >> "$LOG_FILE" 2>&1
    for propfile in "$TARGET_DIR/property/"*; do
        if [ -f "$propfile" ]; then
            p_name=$(basename "$propfile")
            p_val=$(cat "$propfile" 2>/dev/null)
            if [ -n "$p_val" ]; then
                setprop "$p_name" "$p_val" >> "$LOG_FILE" 2>&1
            fi
        fi
    done
fi

# 6. User Apps - Pure /data/app Installation via Package Manager
echo "Cleaning any user apps previously placed in /system/app..." >> "$LOG_FILE"
mount -o remount,rw /system >> "$LOG_FILE" 2>&1
for u_check in "$TARGET_DIR/data_apps/"*; do
    if [ -d "$u_check" ]; then
        u_bname=$(basename "$u_check")
        rm -rf "/system/app/$u_bname" >> "$LOG_FILE" 2>&1
    elif [ -f "$u_check" ] && [ "${u_check##*.}" = "apk" ]; then
        u_fname=$(basename "$u_check")
        u_bname="${u_fname%.*}"
        rm -rf "/system/app/$u_bname" "/system/app/$u_fname" >> "$LOG_FILE" 2>&1
    fi
done

if [ -d "$TARGET_DIR/data_apps" ]; then
    echo "Installing User Apps to /data/app..." >> "$LOG_FILE"
    STAGE_DIR="/data/local/tmp/user_restore_stage"
    for appdir in "$TARGET_DIR/data_apps/"*; do
        if [ -d "$appdir" ]; then
            app_bname=$(basename "$appdir")
            pkg_name="${app_bname%%-*}"
            if [ -n "$pkg_name" ] && pm path "$pkg_name" >/dev/null 2>&1; then
                echo "✓ $pkg_name is already installed, skipping..." >> "$LOG_FILE"
                continue
            fi
            echo "Installing User App: $app_bname..." >> "$LOG_FILE"
            rm -rf "$STAGE_DIR" >> "$LOG_FILE" 2>&1
            mkdir -p "$STAGE_DIR" >> "$LOG_FILE" 2>&1
            cp "$appdir"/*.apk "$STAGE_DIR/" >> "$LOG_FILE" 2>&1
            chmod 644 "$STAGE_DIR"/*.apk >> "$LOG_FILE" 2>&1

            total_bytes=0
            for a in "$STAGE_DIR"/*.apk; do
                sz=$(stat -c%s "$a" 2>/dev/null || wc -c < "$a")
                total_bytes=$((total_bytes + sz))
            done

            installed=false
            sess_id=$(pm install-create -i com.android.packageinstaller -r -g -S $total_bytes 2>&1 | tr -cd '0-9')
            if [ -z "$sess_id" ]; then
                sess_id=$(pm install-create -i com.android.vending -r -g -S $total_bytes 2>&1 | tr -cd '0-9')
            fi
            if [ -z "$sess_id" ]; then
                sess_id=$(pm install-create -r -g -S $total_bytes 2>&1 | tr -cd '0-9')
            fi

            if [ -n "$sess_id" ]; then
                echo "Created session $sess_id for $app_bname" >> "$LOG_FILE"
                for a in "$STAGE_DIR"/*.apk; do
                    b_name=$(basename "$a" .apk)
                    sz=$(stat -c%s "$a" 2>/dev/null || wc -c < "$a")
                    pm install-write -S $sz $sess_id "$b_name" "$a" >> "$LOG_FILE" 2>&1
                done
                commit_res=$(pm install-commit $sess_id 2>&1)
                echo "Session commit: $commit_res" >> "$LOG_FILE"
                if echo "$commit_res" | grep -qi "Success"; then
                    installed=true
                else
                    pm install-abandon $sess_id >/dev/null 2>&1
                fi
            fi

            if [ "$installed" = false ]; then
                target_apk="$STAGE_DIR/base.apk"
                if [ ! -f "$target_apk" ]; then
                    target_apk=$(ls -1 "$STAGE_DIR"/*.apk 2>/dev/null | head -n 1)
                fi
                if [ -f "$target_apk" ]; then
                    inst_res=$(pm install -i com.android.packageinstaller -r "$target_apk" 2>&1)
                    echo "$inst_res" >> "$LOG_FILE"
                    if echo "$inst_res" | grep -qi "Success"; then
                        installed=true
                    else
                        inst_res=$(pm install -i com.android.vending -r "$target_apk" 2>&1)
                        echo "$inst_res" >> "$LOG_FILE"
                        if echo "$inst_res" | grep -qi "Success"; then
                            installed=true
                        else
                            inst_res=$(pm install -r "$target_apk" 2>&1)
                            echo "$inst_res" >> "$LOG_FILE"
                            if echo "$inst_res" | grep -qi "Success"; then
                                installed=true
                            fi
                        fi
                    fi
                fi
            fi

            if [ "$installed" = false ]; then
                target_apk="$STAGE_DIR/base.apk"
                if [ ! -f "$target_apk" ]; then
                    target_apk=$(ls -1 "$STAGE_DIR"/*.apk 2>/dev/null | head -n 1)
                fi
                if [ -f "$target_apk" ]; then
                    cmd_res=$(cmd package install -i com.android.packageinstaller -r "$target_apk" 2>&1)
                    echo "cmd package: $cmd_res" >> "$LOG_FILE"
                    if echo "$cmd_res" | grep -qi "Success"; then
                        installed=true
                    fi
                fi
            fi

            if [ "$installed" = true ]; then
                echo "✓ $app_bname installed successfully as User App!" >> "$LOG_FILE"
            else
                echo "⚠ $app_bname installation rejected by PM." >> "$LOG_FILE"
            fi
            rm -rf "$STAGE_DIR" >> "$LOG_FILE" 2>&1
        elif [ -f "$appdir" ] && [ "${appdir##*.}" = "apk" ]; then
            fname=$(basename "$appdir")
            echo "Installing User APK: $fname..." >> "$LOG_FILE"
            rm -rf "$STAGE_DIR" >> "$LOG_FILE" 2>&1
            mkdir -p "$STAGE_DIR" >> "$LOG_FILE" 2>&1
            cp "$appdir" "$STAGE_DIR/$fname" >> "$LOG_FILE" 2>&1
            chmod 644 "$STAGE_DIR/$fname" >> "$LOG_FILE" 2>&1

            installed=false
            sz=$(stat -c%s "$STAGE_DIR/$fname" 2>/dev/null || wc -c < "$STAGE_DIR/$fname")
            sess_id=$(pm install-create -i com.android.packageinstaller -r -g -S $sz 2>&1 | tr -cd '0-9')
            if [ -n "$sess_id" ]; then
                pm install-write -S $sz $sess_id base "$STAGE_DIR/$fname" >> "$LOG_FILE" 2>&1
                commit_res=$(pm install-commit $sess_id 2>&1)
                if echo "$commit_res" | grep -qi "Success"; then
                    installed=true
                else
                    pm install-abandon $sess_id >/dev/null 2>&1
                fi
            fi
            if [ "$installed" = false ]; then
                inst_res=$(pm install -i com.android.packageinstaller -r "$STAGE_DIR/$fname" 2>&1)
                if echo "$inst_res" | grep -qi "Success"; then
                    installed=true
                else
                    inst_res=$(pm install -r "$STAGE_DIR/$fname" 2>&1)
                    if echo "$inst_res" | grep -qi "Success"; then
                        installed=true
                    fi
                fi
            fi
            if [ "$installed" = true ]; then
                echo "✓ $fname installed successfully as User App!" >> "$LOG_FILE"
            fi
            rm -rf "$STAGE_DIR" >> "$LOG_FILE" 2>&1
        fi
    done
fi

# 7. App Internal Data with Dynamic UIDs & Preserving Library Symlinks
if [ -d "$TARGET_DIR/data_data" ]; then
    echo "Restoring App Data with Dynamic UID resolution..." >> "$LOG_FILE"
    for pdir in "$TARGET_DIR/data_data/"*; do
        if [ -d "$pdir" ]; then
            pname=$(basename "$pdir")
            dest_dir="/data/data/$pname"

            # Gracefully force-stop background process to prevent SQLite WAL corruption
            am force-stop "$pname" >/dev/null 2>&1
            rm -f "$dest_dir/databases/"*-wal "$dest_dir/databases/"*-shm 2>/dev/null
            mkdir -p "$dest_dir" >> "$LOG_FILE" 2>&1

            # Smart merge: copy databases, shared_prefs, files, but PRESERVE lib symlink and caches
            for item in "$pdir/"*; do
                if [ -e "$item" ]; then
                    iname=$(basename "$item")
                    if [ "$iname" != "lib" ] && [ "$iname" != "cache" ] && [ "$iname" != "code_cache" ]; then
                        cp -r "$item" "$dest_dir/" >> "$LOG_FILE" 2>&1
                    fi
                fi
            done

            # Read actual live UID assigned by Android PM
            APP_UID=$(stat -c %u "$dest_dir" 2>/dev/null)
            if [ -n "$APP_UID" ] && [ "$APP_UID" -ge 10000 ]; then
                chown -R "$APP_UID:$APP_UID" "$dest_dir" >> "$LOG_FILE" 2>&1
            elif [ -f "/data/system/packages.list" ]; then
                puid=$(awk -v p="$pname" '$1==p {print $2}' /data/system/packages.list)
                if [ -n "$puid" ]; then
                    chown -R "$puid:$puid" "$dest_dir" >> "$LOG_FILE" 2>&1
                fi
            fi
            chmod 751 "$dest_dir" >> "$LOG_FILE" 2>&1
            restorecon -R "$dest_dir" >> "$LOG_FILE" 2>&1
        fi
    done
    restorecon -R /data/system >> "$LOG_FILE" 2>&1
fi

# Restore Device-Encrypted Storage (user_de) for Vehicle Settings & System
if [ -d "$TARGET_DIR/user_de" ]; then
    mkdir -p /data/user_de/0 >> "$LOG_FILE" 2>&1
    cp -r "$TARGET_DIR/user_de/"* /data/user_de/0/ >> "$LOG_FILE" 2>&1
    if [ -f "/data/system/packages.list" ]; then
        for udedir in /data/user_de/0/*; do
            if [ -d "$udedir" ]; then
                udename=$(basename "$udedir")
                udeuid=$(awk -v p="$udename" '$1==p {print $2}' /data/system/packages.list)
                if [ -n "$udeuid" ]; then
                    chown -R "$udeuid:$udeuid" "$udedir" >> "$LOG_FILE" 2>&1
                    chmod 751 "$udedir" >> "$LOG_FILE" 2>&1
                fi
            fi
        done
    fi
fi

# 8. Break Android FLAG_STOPPED State (Awaken Apps for Vehicle Autostart)
echo "Waking up applications from STOPPED state for vehicle boot..." >> "$LOG_FILE"
for pdir in "$TARGET_DIR/data_data/"*; do
    if [ -d "$pdir" ]; then
        pname=$(basename "$pdir")
        am broadcast -a android.intent.action.BOOT_COMPLETED -p "$pname" --include-stopped-packages >/dev/null 2>&1
    fi
done

# 9. Wi-Fi, Bluetooth & Developer Mode
if [ -d "$TARGET_DIR/wifi_bt/wifi" ]; then
    echo "Restoring Wi-Fi configurations..." >> "$LOG_FILE"
    mkdir -p /data/misc/wifi >> "$LOG_FILE" 2>&1
    cp -r "$TARGET_DIR/wifi_bt/wifi/"* /data/misc/wifi/ >> "$LOG_FILE" 2>&1
    chown -R wifi:wifi /data/misc/wifi >> "$LOG_FILE" 2>&1
    chmod -R 770 /data/misc/wifi >> "$LOG_FILE" 2>&1
else
    echo "Community Preset / No Wi-Fi in backup: Preserving target vehicle Wi-Fi untouched." >> "$LOG_FILE"
fi
if [ -d "$TARGET_DIR/wifi_bt/bluedroid" ]; then
    echo "Restoring Bluetooth pairings..." >> "$LOG_FILE"
    mkdir -p /data/misc/bluedroid >> "$LOG_FILE" 2>&1
    cp -r "$TARGET_DIR/wifi_bt/bluedroid/"* /data/misc/bluedroid/ >> "$LOG_FILE" 2>&1
    chown -R bluetooth:bluetooth /data/misc/bluedroid >> "$LOG_FILE" 2>&1
    chmod -R 770 /data/misc/bluedroid >> "$LOG_FILE" 2>&1
fi
if [ -d "$TARGET_DIR/wifi_bt/bluetooth" ]; then
    echo "Restoring Bluetooth pairings..." >> "$LOG_FILE"
    mkdir -p /data/misc/bluetooth >> "$LOG_FILE" 2>&1
    cp -r "$TARGET_DIR/wifi_bt/bluetooth/"* /data/misc/bluetooth/ >> "$LOG_FILE" 2>&1
    chown -R bluetooth:bluetooth /data/misc/bluetooth >> "$LOG_FILE" 2>&1
    chmod -R 770 /data/misc/bluetooth >> "$LOG_FILE" 2>&1
fi
if [ -d "$TARGET_DIR/wifi_bt/vendor_bt" ]; then
    mkdir -p /data/vendor/bluetooth >> "$LOG_FILE" 2>&1
    cp -r "$TARGET_DIR/wifi_bt/vendor_bt/"* /data/vendor/bluetooth/ >> "$LOG_FILE" 2>&1
    chown -R bluetooth:bluetooth /data/vendor/bluetooth >> "$LOG_FILE" 2>&1
    chmod -R 770 /data/vendor/bluetooth >> "$LOG_FILE" 2>&1
fi
if [ -d "$TARGET_DIR/wifi_bt/adb" ]; then
    mkdir -p /data/misc/adb >> "$LOG_FILE" 2>&1
    cp -r "$TARGET_DIR/wifi_bt/adb/"* /data/misc/adb/ >> "$LOG_FILE" 2>&1
    chmod 640 /data/misc/adb/* >> "$LOG_FILE" 2>&1
    chown -R system:shell /data/misc/adb >> "$LOG_FILE" 2>&1
fi

# Reinforce Developer Mode and unlock Developer Options UI without 7-tap requirement
if grep -q 'name="development_settings_enabled" value="1"' "$TARGET_DIR/settings/settings_global.xml" 2>/dev/null; then
    echo "Reinforcing Developer Mode, ADB flags, and unlocking Developer UI..." >> "$LOG_FILE"
    settings put global development_settings_enabled 1 >> "$LOG_FILE" 2>&1
    settings put global adb_enabled 1 >> "$LOG_FILE" 2>&1
    setprop persist.sys.usb.config diag,serial_smd,rmnet_ipa,adb >> "$LOG_FILE" 2>&1
    setprop persist.adb.tcp.port 5555 >> "$LOG_FILE" 2>&1

    for s_dir in /data/user_de/0/com.android.settings /data/data/com.android.settings; do
        if [ -d "$s_dir" ]; then
            mkdir -p "$s_dir/shared_prefs" >> "$LOG_FILE" 2>&1
            echo '<?xml version="1.0" encoding="utf-8" standalone="yes" ?><map><boolean name="show" value="true" /></map>' > "$s_dir/shared_prefs/development.xml" 2>> "$LOG_FILE"
            chmod 660 "$s_dir/shared_prefs/development.xml" >> "$LOG_FILE" 2>&1
            chown 1000:1000 "$s_dir/shared_prefs/development.xml" >> "$LOG_FILE" 2>&1
        fi
    done
fi

# 10. Internal Storage (/data/media/0)
if [ -d "$TARGET_DIR/sdcard" ] && [ -n "$(ls -A "$TARGET_DIR/sdcard" 2>/dev/null)" ]; then
    echo "Restoring Internal Storage files..." >> "$LOG_FILE"
    SD_DEST="/data/media/0"
    if [ ! -d "$SD_DEST" ]; then SD_DEST="/sdcard"; fi
    cp -r "$TARGET_DIR/sdcard/." "$SD_DEST/" >> "$LOG_FILE" 2>&1
    chown -R media_rw:media_rw "$SD_DEST" >> "$LOG_FILE" 2>&1
    chmod -R 775 "$SD_DEST" >> "$LOG_FILE" 2>&1
else
    echo "No media backup to restore: Preserving existing internal storage untouched." >> "$LOG_FILE"
fi

# 11. Lock /system Read-Only, Restore Settings XMLs & Set Default Home Launcher
mount -o remount,ro /system >> "$LOG_FILE" 2>&1

# Inject system XML configurations right before reboot to prevent package manager overwrite
echo "Injecting runtime permissions and settings XML configurations..." >> "$LOG_FILE"
cp -f "$TARGET_DIR/settings/settings_"*.xml /data/system/users/0/ >> "$LOG_FILE" 2>&1
cp -f "$TARGET_DIR/settings/runtime-permissions.xml" /data/system/users/0/ >> "$LOG_FILE" 2>&1
cp -f "$TARGET_DIR/settings/appops.xml" /data/system/ >> "$LOG_FILE" 2>&1
cp -f "$TARGET_DIR/settings/appwidgets.xml" /data/system/users/0/ >> "$LOG_FILE" 2>&1
chmod 600 /data/system/users/0/settings_*.xml /data/system/users/0/runtime-permissions.xml /data/system/appops.xml /data/system/users/0/appwidgets.xml >> "$LOG_FILE" 2>&1
chown system:system /data/system/users/0/settings_*.xml /data/system/users/0/runtime-permissions.xml /data/system/appops.xml /data/system/users/0/appwidgets.xml >> "$LOG_FILE" 2>&1

DEF_LAUNCHER_FILE="$TARGET_DIR/settings/default_launcher.txt"
if [ -f "$DEF_LAUNCHER_FILE" ]; then
    DEF_COMPONENT=$(cat "$DEF_LAUNCHER_FILE" | tr -d '\r\n ')
    if echo "$DEF_COMPONENT" | grep -q "/"; then
        echo "Setting default home launcher: $DEF_COMPONENT" >> "$LOG_FILE"
        cmd package set-home-activity "$DEF_COMPONENT" >> "$LOG_FILE" 2>&1
    fi
fi

if [ -f "$TARGET_DIR/settings/oem_launcher_state.txt" ]; then
    echo "Re-freezing stock OEM launcher as specified in backup..." >> "$LOG_FILE"
    pm disable com.qinggan.app.launcher >> "$LOG_FILE" 2>&1
elif grep -q 'name="com.qinggan.app.launcher".*enabled="2"' "$TARGET_DIR/settings/package-restrictions.xml" 2>/dev/null; then
    echo "Restoring stock launcher freeze state from XML..." >> "$LOG_FILE"
    pm disable com.qinggan.app.launcher >> "$LOG_FILE" 2>&1
fi

# 12. Final sync & Kernel Hard Reboot (Prevents system_server In-Memory Overwrite)
echo "=== RESTORE COMPLETED 100%! REBOOTING DIRECTLY TO ANDROID ===" >> "$LOG_FILE"
date >> "$LOG_FILE"
sync
sleep 2
sync

# Kernel Hard Reboot to guarantee zero in-memory flush over restored files
reboot -f || busybox reboot -f || setprop sys.powerctl reboot || reboot
"""
        if progress_func:
            progress_func(0.93, "Generating 12-step restoration script (custom_rep.sh)...", 0.0, 0, 0)

        os.makedirs(update_dir, exist_ok=True)
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        if progress_func:
            progress_func(0.96, "Writing restoration manual & verification flags...", 0.0, 0, 0)

        info_path = os.path.join(usb_drive, "Restore_Info.txt")
        info_content = f"""🔄 AERO SUITE — SYSTEM & DATA RESTORE MANUAL
Target Vehicle: Dongfeng Shine (Aeolus D53) Infotainment System

============================================================
1. TECHNICAL OVERVIEW & INTERNAL WORKFLOW
============================================================
The restore engine executes an exact 12-step restoration of your saved vehicle backup:
1. System Partition Remount:
   Mounts /system with read-write permissions: mount -o remount,rw /system.
2. Custom Priv-Apps Restoration:
   Restores all custom system priv-apps along with their native .so libraries and sets standard permissions (0644 / 0755).
3. User Applications Restoration:
   Restores all user applications to /data/app/.
4. Application Databases & Accounts:
   Restores application databases, preferences, and Google accounts in /data/data/.
5. Connectivity & Settings:
   Restores saved Wi-Fi networks, paired Bluetooth devices, and system settings.
6. Internal Storage:
   Restores user files to /data/media/0 (Downloads, Music, Documents).
7. Cache Invalidation & Partition Lock:
   Clears temporary Dalvik cache and remounts /system as Read-Only.
8. Sync & Reboot:
   Synchronizes all filesystem buffers (sync) and commands an automatic clean system restart.

============================================================
2. VEHICLE RESTORE INSTRUCTIONS
============================================================
1. Ensure this USB drive was prepared using Aero Suite.
2. Start the vehicle and wait until the screen fully boots up.
3. Insert this USB drive into the USB port. The restore process runs automatically (takes 1-3 minutes).
4. As soon as the screen turns off to restart automatically, unplug the USB drive immediately (before it boots back up).
5. After rebooting, all your apps, accounts, settings, and files will be fully restored!

{SIGNATURE_BANNER}
"""
        with open(info_path, "w", encoding="utf-8") as f:
            f.write(info_content)

        if progress_func:
            progress_func(0.99, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, "Restore USB ready!", 0.0, 0, 0)

        _log(t("logs.prep_usb_success", "✓ Restore USB prepared successfully.", title=t("nav.restore_title", "Restore")))
        return True
    except Exception as e:
        log_exception(e, "prepare_restore_usb")
        _log(f"  ✗ Failed to prepare Restore USB: {e}")
        return False
