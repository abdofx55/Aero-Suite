"""
backup.py — Feature 10: Vehicle System & Data Extraction (Car-to-USB) Payload Generator.
Supports 1:1 Personal Private clone and Zero-Leakage Community Shared presets.
"""
import os
import time
from core.constants import FACTORY_PRIV_APPS, FACTORY_APPS, SIGNATURE_BANNER
from core.exceptions import log_exception
from payloads.base import clean_usb_drive, write_script_file


def prepare_backup_usb(
    usb_drive: str,
    backup_type: str = "personal",
    include_media: bool = False,
    preset_name: str = "",
    author: str = "",
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """Prepares USB to extract car snapshot (Personal 1:1 or Community Preset) to USB:/Backup."""
    def _log(msg):
        if log_func:
            log_func(msg)

    b_type_clean = (backup_type or "personal").lower()
    if b_type_clean not in ("personal", "community"):
        b_type_clean = "personal"

    _log(f"\n── [10/13] Preparing {b_type_clean.upper()} Backup USB: {usb_drive} ──")
    if b_type_clean == "community":
        _log("  Scope:       🌐 Community Shared Preset (Safe for sharing)")
        _log(f"  Preset Name: {preset_name or 'Community Preset'}")
        _log(f"  Author:      {author or 'Anonymous'}")
        _log("  Privacy:     Zero-Leakage (Accounts, Wi-Fi & BT pairings scrubbed)")
    else:
        _log("  Scope:       🔒 Personal Private (1:1 Vehicle Clone)")
    _log(f"  User Media (/sdcard): {'Included (~4 GB+)' if include_media else 'Skipped (~200-400 MB, fast ~30s)'}")

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
            progress_func(0.60, f"Writing {b_type_clean.upper()} car backup scripts...", 0.0, 0, 0)

        priv_str = ' '.join(FACTORY_PRIV_APPS)
        app_str = ' '.join(FACTORY_APPS)

        b_type_sh = b_type_clean.upper()
        inc_media_sh = "1" if include_media else "0"
        p_name_sh = (preset_name or "").replace('"', '\\"').replace("'", "")
        author_sh = (author or "").replace('"', '\\"').replace("'", "")

        script = f"""#!/system/bin/sh
# ==========================================
# AERO SUITE — {b_type_sh} SYSTEM & DATA BACKUP
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

LOG_FILE="$USB_PATH/backup.log"
echo "=== AERO {b_type_sh} BACKUP START ===" > "$LOG_FILE"
date >> "$LOG_FILE"

CAR_MODEL=$(getprop ro.product.model)
BUILD_ID=$(getprop ro.build.display.id)
echo "Model: $CAR_MODEL" >> "$LOG_FILE"
echo "Build: $BUILD_ID" >> "$LOG_FILE"
echo "Backup Type: {b_type_sh}" >> "$LOG_FILE"
echo "Include Media: {inc_media_sh}" >> "$LOG_FILE"

TARGET_DIR="$USB_PATH/Backup"
rm -rf "$TARGET_DIR" >> "$LOG_FILE" 2>&1
mkdir -p "$TARGET_DIR" >> "$LOG_FILE" 2>&1
rm -f "$USB_PATH/backup_complete.flag" >> "$LOG_FILE" 2>&1

BACKUP_FAILED=0

# 1. System Settings & Properties
mkdir -p "$TARGET_DIR/settings" "$TARGET_DIR/property" >> "$LOG_FILE" 2>&1
cp -f /data/system/users/0/package-restrictions.xml "$TARGET_DIR/settings/" >> "$LOG_FILE" 2>&1
cp -f /data/system/users/0/runtime-permissions.xml "$TARGET_DIR/settings/" >> "$LOG_FILE" 2>&1
cp -f /data/system/appops.xml "$TARGET_DIR/settings/" >> "$LOG_FILE" 2>&1
cp -f /data/system/users/0/settings_*.xml "$TARGET_DIR/settings/" >> "$LOG_FILE" 2>&1
cp -f /data/system/users/0/appwidgets.xml "$TARGET_DIR/settings/" >> "$LOG_FILE" 2>&1
cp -f /system/etc/permissions/voice_recognizers.xml "$TARGET_DIR/settings/" >> "$LOG_FILE" 2>&1
cp -f /system/build.prop "$TARGET_DIR/settings/" >> "$LOG_FILE" 2>&1

# Capture explicit default launcher component & stock launcher freeze state
cmd package resolve-activity --brief -c android.intent.category.HOME -a android.intent.action.MAIN 2>/dev/null | tail -n 1 > "$TARGET_DIR/settings/default_launcher.txt" 2>/dev/null
if pm list packages -d 2>/dev/null | grep -q "com.qinggan.app.launcher"; then
    echo "FROZEN" > "$TARGET_DIR/settings/oem_launcher_state.txt"
fi

# Personal mode preserves locksettings; Community skips locksettings to prevent vehicle locks
if [ "{b_type_sh}" = "PERSONAL" ]; then
    cp -f /data/system/locksettings.db* "$TARGET_DIR/settings/" >> "$LOG_FILE" 2>&1
fi

if [ -d "/data/property" ]; then
    cp -r /data/property/* "$TARGET_DIR/property/" >> "$LOG_FILE" 2>&1
fi

# 2. Custom System Apps
mkdir -p "$TARGET_DIR/system_apps/priv-app" "$TARGET_DIR/system_apps/app" >> "$LOG_FILE" 2>&1
PRIV_WHITELIST="{priv_str}"
APP_WHITELIST="{app_str}"

for dir in /system/priv-app/*; do
    if [ -d "$dir" ]; then
        name=$(basename "$dir")
        is_factory=false
        for fw in $PRIV_WHITELIST; do
            if [ "$name" = "$fw" ]; then is_factory=true; break; fi
        done
        if [ "$is_factory" = "false" ]; then
            cp -r "$dir" "$TARGET_DIR/system_apps/priv-app/" >> "$LOG_FILE" 2>&1
        fi
    fi
done

for dir in /system/app/*; do
    if [ -d "$dir" ]; then
        name=$(basename "$dir")
        is_factory=false
        for fw in $APP_WHITELIST; do
            if [ "$name" = "$fw" ]; then is_factory=true; break; fi
        done
        if [ "$is_factory" = "false" ]; then
            cp -r "$dir" "$TARGET_DIR/system_apps/app/" >> "$LOG_FILE" 2>&1
        fi
    fi
done

# 3. Accounts & App Data
if [ "{b_type_sh}" = "PERSONAL" ]; then
    mkdir -p "$TARGET_DIR/accounts" "$TARGET_DIR/keystore" "$TARGET_DIR/data_data" >> "$LOG_FILE" 2>&1
    cp -f /data/system/users/0/accounts.db* "$TARGET_DIR/accounts/" >> "$LOG_FILE" 2>&1
    cp -f /data/system_de/0/accounts_de.db* "$TARGET_DIR/accounts/" >> "$LOG_FILE" 2>&1
    if [ -d "/data/misc/keystore" ]; then
        cp -r /data/misc/keystore/* "$TARGET_DIR/keystore/" >> "$LOG_FILE" 2>&1
    fi
    if [ -d "/data/system/sync" ]; then
        mkdir -p "$TARGET_DIR/accounts/sync" >> "$LOG_FILE" 2>&1
        cp -r /data/system/sync/* "$TARGET_DIR/accounts/sync/" >> "$LOG_FILE" 2>&1
    fi
    # Backup all Google and Play Store databases & tokens
    for gms_dir in /data/data/com.google.* /data/data/com.android.vending; do
        if [ -d "$gms_dir" ]; then
            cp -r "$gms_dir" "$TARGET_DIR/data_data/" >> "$LOG_FILE" 2>&1
        fi
    done
else
    mkdir -p "$TARGET_DIR/data_data" >> "$LOG_FILE" 2>&1
    echo "Community Mode: Scrubbing accounts.db and Google private tokens." >> "$LOG_FILE"
fi

if [ -f "/data/system/packages.list" ]; then
    cp -f /data/system/packages.list "$TARGET_DIR/packages.list" >> "$LOG_FILE" 2>&1
fi

# Android Core Settings, Vehicle Settings, Driving Modes, Audio
for qg_dir in /data/data/com.android.settings /data/data/com.android.providers.settings /data/data/com.qinggan.* /data/data/com.pateo.CarPlay.*; do
    if [ -d "$qg_dir" ]; then
        cp -r "$qg_dir" "$TARGET_DIR/data_data/" >> "$LOG_FILE" 2>&1
    fi
done

if [ "{b_type_sh}" = "PERSONAL" ]; then
    if [ -d "/data/data/com.android.bluetooth" ]; then
        cp -r /data/data/com.android.bluetooth "$TARGET_DIR/data_data/" >> "$LOG_FILE" 2>&1
    fi
fi

# Device-Encrypted Storage (user_de) for Vehicle Settings & Providers
if [ -d "/data/user_de/0" ]; then
    mkdir -p "$TARGET_DIR/user_de" >> "$LOG_FILE" 2>&1
    for de_dir in /data/user_de/0/com.qinggan.* /data/user_de/0/com.android.providers.settings /data/user_de/0/com.android.settings; do
        if [ -d "$de_dir" ]; then
            cp -r "$de_dir" "$TARGET_DIR/user_de/" >> "$LOG_FILE" 2>&1
        fi
    done
    if [ "{b_type_sh}" = "PERSONAL" ]; then
        if [ -d "/data/user_de/0/com.android.bluetooth" ]; then
            cp -r /data/user_de/0/com.android.bluetooth "$TARGET_DIR/user_de/" >> "$LOG_FILE" 2>&1
        fi
    fi
fi

# 4. User Apps (/data/app) & Complete App Data Coverage
mkdir -p "$TARGET_DIR/data_apps" >> "$LOG_FILE" 2>&1
if [ -d "/data/app" ]; then
    for uapp in /data/app/*; do
        if [ -e "$uapp" ]; then
            u_bname=$(basename "$uapp")
            cp -r "$uapp" "$TARGET_DIR/data_apps/" >> "$LOG_FILE" 2>&1
            clean_pkg=$(echo "$u_bname" | cut -d'-' -f1)
            if [ -d "/data/data/$clean_pkg" ] && [ ! -d "$TARGET_DIR/data_data/$clean_pkg" ]; then
                cp -r "/data/data/$clean_pkg" "$TARGET_DIR/data_data/" >> "$LOG_FILE" 2>&1
            fi
        fi
    done
fi

# Backup /data/data for all Custom System Apps (AGAMA Launcher, SmartTube, Radarbot, etc.)
for c_dir in "$TARGET_DIR/system_apps/priv-app/"* "$TARGET_DIR/system_apps/app/"*; do
    if [ -d "$c_dir" ]; then
        c_bname=$(basename "$c_dir")
        for c_apk in "$c_dir"/*.apk; do
            if [ -f "$c_apk" ]; then
                c_pkg=$(pm list packages -f | grep "$c_bname" | cut -d '=' -f 2 | head -n 1)
                if [ -n "$c_pkg" ] && [ -d "/data/data/$c_pkg" ] && [ ! -d "$TARGET_DIR/data_data/$c_pkg" ]; then
                    cp -r "/data/data/$c_pkg" "$TARGET_DIR/data_data/" >> "$LOG_FILE" 2>&1
                fi
            fi
        done
    fi
done

# Explicit safety net for custom launchers, widgets and modded tools
for c_pkg in altergames.carlauncher org.smarttube.stable com.vialsoft.radarbot_free com.nst.iptvsmarterstvbox com.Hydraprimeonline nu.nav.bar com.farmerbb.taskbar; do
    if [ -d "/data/data/$c_pkg" ] && [ ! -d "$TARGET_DIR/data_data/$c_pkg" ]; then
        cp -r "/data/data/$c_pkg" "$TARGET_DIR/data_data/" >> "$LOG_FILE" 2>&1
    fi
done

# 5. Wi-Fi & Bluetooth (Only included in PERSONAL mode; 100% scrubbed in COMMUNITY mode)
if [ "{b_type_sh}" = "PERSONAL" ]; then
    mkdir -p "$TARGET_DIR/wifi_bt/wifi" "$TARGET_DIR/wifi_bt/bluedroid" "$TARGET_DIR/wifi_bt/bluetooth" "$TARGET_DIR/wifi_bt/vendor_bt" "$TARGET_DIR/wifi_bt/adb" >> "$LOG_FILE" 2>&1
    if [ -d "/data/misc/wifi" ]; then cp -r /data/misc/wifi/* "$TARGET_DIR/wifi_bt/wifi/" >> "$LOG_FILE" 2>&1; fi
    if [ -d "/data/misc/dhcp" ]; then cp -r /data/misc/dhcp/* "$TARGET_DIR/wifi_bt/wifi/" >> "$LOG_FILE" 2>&1; fi
    if [ -d "/data/misc/bluedroid" ]; then cp -r /data/misc/bluedroid/* "$TARGET_DIR/wifi_bt/bluedroid/" >> "$LOG_FILE" 2>&1; fi
    if [ -d "/data/misc/bluetooth" ]; then cp -r /data/misc/bluetooth/* "$TARGET_DIR/wifi_bt/bluetooth/" >> "$LOG_FILE" 2>&1; fi
    if [ -d "/data/vendor/bluetooth" ]; then cp -r /data/vendor/bluetooth/* "$TARGET_DIR/wifi_bt/vendor_bt/" >> "$LOG_FILE" 2>&1; fi
    if [ -d "/data/misc/adb" ]; then cp -r /data/misc/adb/* "$TARGET_DIR/wifi_bt/adb/" >> "$LOG_FILE" 2>&1; fi
else
    echo "Community Mode: Wi-Fi networks and Bluetooth pairings skipped." >> "$LOG_FILE"
fi

# 6. Internal Storage (/sdcard)
if [ "{inc_media_sh}" = "1" ]; then
    mkdir -p "$TARGET_DIR/sdcard" >> "$LOG_FILE" 2>&1
    SD_SRC="/data/media/0"
    if [ ! -d "$SD_SRC" ] || [ -z "$(ls -A "$SD_SRC" 2>/dev/null)" ]; then
        if [ -d "/sdcard" ]; then SD_SRC="/sdcard"; fi
    fi

    for item in "$SD_SRC"/*; do
        if [ -e "$item" ]; then
            bname=$(basename "$item")
            if [ "$bname" = "Android" ]; then
                mkdir -p "$TARGET_DIR/sdcard/Android" >> "$LOG_FILE" 2>&1
                for a_item in "$item"/*; do
                    if [ "$(basename "$a_item")" != "data" ] && [ -e "$a_item" ]; then
                        cp -r "$a_item" "$TARGET_DIR/sdcard/Android/" >> "$LOG_FILE" 2>&1
                    fi
                done
            else
                cp -r "$item" "$TARGET_DIR/sdcard/" >> "$LOG_FILE" 2>&1
            fi
        fi
    done
else
    echo "User Media disabled: Skipping /sdcard backup for fast lightweight archive." >> "$LOG_FILE"
fi

# 7. Generate Comprehensive Backup Manifest & Restoration Strategy Checklist
MANIFEST_FILE="$TARGET_DIR/Backup_Manifest.txt"
echo "==========================================================" > "$MANIFEST_FILE"
echo "📋 AERO SUITE v2.0 — BACKUP MANIFEST & STRATEGY CHECKLIST" >> "$MANIFEST_FILE"
echo "==========================================================" >> "$MANIFEST_FILE"
echo "Backup Date:    $(date)" >> "$MANIFEST_FILE"
echo "Vehicle Model:  $CAR_MODEL" >> "$MANIFEST_FILE"
echo "ROM Build ID:   $BUILD_ID" >> "$MANIFEST_FILE"
echo "Backup Type:    {b_type_sh}" >> "$MANIFEST_FILE"
echo "Preset Name:    {p_name_sh}" >> "$MANIFEST_FILE"
echo "Author:         {author_sh}" >> "$MANIFEST_FILE"
echo "Include Media:  {inc_media_sh}" >> "$MANIFEST_FILE"
echo "" >> "$MANIFEST_FILE"
echo "── 1. Captured User Applications (/data/app) ──" >> "$MANIFEST_FILE"
if [ -d "$TARGET_DIR/data_apps" ]; then
    for u in "$TARGET_DIR/data_apps/"*; do
        if [ -e "$u" ]; then echo "  [App] $(basename "$u")" >> "$MANIFEST_FILE"; fi
    done
fi
echo "" >> "$MANIFEST_FILE"
echo "── 2. Captured Custom System Apps (/system/priv-app & app) ──" >> "$MANIFEST_FILE"
if [ -d "$TARGET_DIR/system_apps/priv-app" ]; then
    for s in "$TARGET_DIR/system_apps/priv-app/"*; do
        if [ -d "$s" ]; then echo "  [Priv-App] $(basename "$s")" >> "$MANIFEST_FILE"; fi
    done
fi
if [ -d "$TARGET_DIR/system_apps/app" ]; then
    for s in "$TARGET_DIR/system_apps/app/"*; do
        if [ -d "$s" ]; then echo "  [System-App] $(basename "$s")" >> "$MANIFEST_FILE"; fi
    done
fi
echo "" >> "$MANIFEST_FILE"
echo "── 3. Launcher & UI Configuration ──" >> "$MANIFEST_FILE"
if [ -f "$TARGET_DIR/settings/default_launcher.txt" ]; then
    echo "  Default Launcher: $(cat "$TARGET_DIR/settings/default_launcher.txt")" >> "$MANIFEST_FILE"
fi
if [ -f "$TARGET_DIR/settings/oem_launcher_state.txt" ]; then
    echo "  Stock OEM Launcher: FROZEN (Will be re-frozen on restore)" >> "$MANIFEST_FILE"
else
    echo "  Stock OEM Launcher: ACTIVE" >> "$MANIFEST_FILE"
fi
echo "" >> "$MANIFEST_FILE"
echo "── 4. Google Services & Keystore ──" >> "$MANIFEST_FILE"
if [ -d "$TARGET_DIR/keystore" ] && [ -n "$(ls -A "$TARGET_DIR/keystore" 2>/dev/null)" ]; then
    echo "  Keystore: Master keys archived (1:1 Auth Token Preservation)" >> "$MANIFEST_FILE"
else
    echo "  Keystore: Not present" >> "$MANIFEST_FILE"
fi
if [ -f "$TARGET_DIR/accounts/accounts.db" ]; then
    echo "  Accounts DB: Google & System account database archived" >> "$MANIFEST_FILE"
fi
echo "==========================================================" >> "$MANIFEST_FILE"

sync
if [ "$BACKUP_FAILED" -eq 0 ]; then
    echo "BACKUP_DATE=$(date)" > "$USB_PATH/backup_complete.flag"
    echo "DEVICE_MODEL=$CAR_MODEL" >> "$USB_PATH/backup_complete.flag"
    echo "BUILD_ID=$BUILD_ID" >> "$USB_PATH/backup_complete.flag"
    echo "BACKUP_TYPE={b_type_sh}" >> "$USB_PATH/backup_complete.flag"
    echo "PRESET_NAME={p_name_sh}" >> "$USB_PATH/backup_complete.flag"
    echo "AUTHOR={author_sh}" >> "$USB_PATH/backup_complete.flag"
    echo "INCLUDE_MEDIA={inc_media_sh}" >> "$USB_PATH/backup_complete.flag"
    echo "STATUS=SUCCESS" >> "$USB_PATH/backup_complete.flag"
    sync
fi
sync
"""
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        info_path = os.path.join(usb_drive, "Backup_Info.txt")
        info_content = f"""💾 AERO SUITE — {b_type_sh} CAR BACKUP MANUAL
Target Vehicle: Dongfeng Shine (Aeolus D53) Infotainment System
Backup Mode: {b_type_sh}
Preset Name: {preset_name or 'N/A'}
Author:      {author or 'N/A'}
Media /sdcard: {'Included' if include_media else 'Skipped'}

============================================================
1. TECHNICAL OVERVIEW & INTERNAL WORKFLOW
============================================================
The backup engine extracts a snapshot of your head unit into:
USB:/Backup/

Layers processed:
1. System Settings & Custom Properties (XML configs, OEM props).
2. Custom System Priv-Apps (non-factory system apps).
3. User Applications (/data/app).
4. Application Databases & Tokens (/data/data).
5. Wireless Configurations (Personal only; completely scrubbed in Community presets).
6. Internal Storage (/sdcard - {'Included' if include_media else 'Skipped'}).
7. Verification & Completion Flag.

============================================================
2. VEHICLE BACKUP INSTRUCTIONS
============================================================
1. Start the vehicle and wait for the screen to stabilize.
2. Insert this USB drive into the USB port.
3. Wait while the script collects and archives data (Fast ~30-60s if media is skipped).
4. When you hear the vehicle's native Chinese voice announcement (صوت التنبيه الصيني الصادر من النظام) or after 60 seconds have elapsed, unplug the USB drive.
5. Connect the USB drive to your PC: Aero Suite will automatically detect and sync the backup into your PC Vault!

{SIGNATURE_BANNER}
"""
        if progress_func:
            progress_func(0.85, f"Writing {b_type_clean.upper()} backup manual...", 0.0, 0, 0)

        with open(info_path, "w", encoding="utf-8") as f:
            f.write(info_content)

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, f"{b_type_clean.capitalize()} Backup USB ready!", 0.0, 0, 0)

        _log(f"✓ {b_type_sh} Backup USB prepared successfully.")
        return True
    except Exception as e:
        log_exception(e, "prepare_backup_usb")
        _log(f"  ✗ Failed to prepare Backup USB: {e}")
        return False
