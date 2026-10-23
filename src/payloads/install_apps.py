"""
install_apps.py — Feature 1: Automated Application Installation Payload Generator.
Supports User Apps (/data/app), System Apps (/system/priv-app), AXML patching, and Auto-Launch.
"""
import os
import re
import time
import tempfile
from core.constants import SIGNATURE_BANNER
from core.exceptions import log_exception
from payloads.base import clean_usb_drive, write_script_file, extract_so_libs, copy_file_with_chunk_progress, patch_apk


def prepare_install_apps_usb(
    usb_drive: str,
    selected_apks: list,
    options: dict = None,
    log_func=None,
    progress_func=None,
    cancel_check=None,
    auto_launch_package: str = ""
) -> bool:
    """
    Copies selected APKs to USB with per-app options:
    - install_target: 'user' (User App) or 'system' (System App)
    - force_portrait: bool (Overrides orientation in AXML)
    - block_boot: bool (Neutralizes boot receivers in AXML)
    - auto_launch_package: str (Package name to launch immediately after install)
    """
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(f"\n── [1/13] Preparing Install Apps USB: {usb_drive} ──")
    if not os.path.exists(usb_drive):
        _log(f"  ✗ USB Drive not found: {usb_drive}")
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
        soft_dir = os.path.join(update_dir, "soft")           # System apps
        user_soft_dir = os.path.join(update_dir, "user_soft") # User apps
        os.makedirs(soft_dir, exist_ok=True)
        os.makedirs(user_soft_dir, exist_ok=True)

        total_apks = len(selected_apks)
        total_bytes = sum(
            os.path.getsize(a["path"]) for a in selected_apks
            if os.path.isfile(a.get("path", ""))
        )
        if total_bytes <= 0:
            total_bytes = 1

        _log(f"  Staging {total_apks} selected APK(s) ({total_bytes / (1024 * 1024):.1f} MB total) with custom parameters...")

        system_app_count = 0
        user_app_count = 0
        copied_cumulative_bytes = 0
        start_transfer_time = time.time()

        for idx, apk_info in enumerate(selected_apks, 1):
            if cancel_check and cancel_check():
                _log("  ⚠ Operation cancelled by user.")
                return False

            src_apk = apk_info["path"]
            fname = os.path.basename(src_apk)
            base = os.path.splitext(fname)[0]
            clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '', base)

            target_type = apk_info.get("install_target", "user")
            force_portrait = apk_info.get("force_portrait", False)
            block_boot = apk_info.get("block_boot", True)

            _log(f"  [{idx}/{total_apks}] Processing {fname} -> Target: {target_type.upper()}, Portrait: {force_portrait}, BlockBoot: {block_boot}")

            target_ori = "portrait" if force_portrait else "default"
            needs_patch = (target_ori == "portrait" or block_boot)

            if target_type == "system":
                system_app_count += 1
                app_dest_dir = os.path.join(soft_dir, clean_name)
                os.makedirs(app_dest_dir, exist_ok=True)
                dest_apk = os.path.join(app_dest_dir, f"{clean_name}.apk")
                extract_so_libs(src_apk, app_dest_dir, log_func)
            else:
                user_app_count += 1
                dest_apk = os.path.join(user_soft_dir, f"{clean_name}.apk")

            temp_patched_apk = None
            source_to_stream = src_apk

            if needs_patch:
                temp_patched_apk = os.path.join(tempfile.gettempdir(), f"aero_{clean_name}_{int(time.time()*1000)}.apk")
                patch_success = patch_apk(src_apk, temp_patched_apk, log_func, target_orientation=target_ori, disable_boot_launch=block_boot)
                if patch_success and os.path.isfile(temp_patched_apk):
                    source_to_stream = temp_patched_apk
                else:
                    source_to_stream = src_apk

            def _on_chunk(chunk_len, file_copied, file_total):
                nonlocal copied_cumulative_bytes
                copied_cumulative_bytes += chunk_len
                elapsed = max(0.05, time.time() - start_transfer_time)
                speed_mb_s = (copied_cumulative_bytes / (1024 * 1024)) / elapsed
                pct = 0.15 + 0.70 * min(1.0, copied_cumulative_bytes / total_bytes)
                c_mb = copied_cumulative_bytes / (1024 * 1024)
                t_mb = total_bytes / (1024 * 1024)
                if progress_func:
                    progress_func(pct, fname, speed_mb_s, c_mb, t_mb)

            ok_stream = copy_file_with_chunk_progress(
                source_to_stream,
                dest_apk,
                chunk_size=256 * 1024,
                chunk_callback=_on_chunk,
                cancel_check=cancel_check
            )

            if temp_patched_apk and os.path.exists(temp_patched_apk):
                try:
                    os.remove(temp_patched_apk)
                except Exception:
                    pass

            if not ok_stream or (cancel_check and cancel_check()):
                _log("  ⚠ Operation cancelled by user.")
                return False

        if progress_func:
            progress_func(0.88, "Extracting native libraries & verifying signatures...", 0.0, total_bytes / (1024*1024), total_bytes / (1024*1024))

        # Generate custom_rep.sh for both System Apps and User Apps
        script = f"""#!/system/bin/sh
# ==========================================
# AERO SUITE — AUTOMATED APP INSTALLER
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

LOG_FILE="$USB_PATH/install_log.txt"
echo "=== AERO APP INSTALL START ===" > "$LOG_FILE"
date >> "$LOG_FILE"

mount -o remount,rw /system >> "$LOG_FILE" 2>&1
mount -o rw,remount /system >> "$LOG_FILE" 2>&1

SOFT_DIR="$USB_PATH/update/soft"
USER_SOFT_DIR="$USB_PATH/update/user_soft"

# 1. Install System Apps (into /system/priv-app)
if [ -d "$SOFT_DIR" ]; then
    for item in "$SOFT_DIR"/*; do
        if [ -d "$item" ]; then
            appname=$(basename "$item")
            echo "Installing System App: $appname" >> "$LOG_FILE"
            TARGET_DIR="/system/priv-app/$appname"
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

# 2. Install User Apps (directly to /data/app via Package Manager)
if [ -d "$USER_SOFT_DIR" ]; then
    echo "Unlocking OEM third-party app installation policies..." >> "$LOG_FILE"
    setprop persist.ais_server.3app.perm 1 >> "$LOG_FILE" 2>&1
    settings put global install_non_market_apps 1 >> "$LOG_FILE" 2>&1
    settings put secure install_non_market_apps 1 >> "$LOG_FILE" 2>&1
    settings put system install_non_market_apps 1 >> "$LOG_FILE" 2>&1
    settings put global package_verifier_enable 0 >> "$LOG_FILE" 2>&1
    settings put global package_verifier_user_consent -1 >> "$LOG_FILE" 2>&1
    settings put global verifier_verify_adb_installs 0 >> "$LOG_FILE" 2>&1

    echo "Processing User Apps..." >> "$LOG_FILE"
    STAGE_DIR="/data/local/tmp/user_stage"
    rm -rf "$STAGE_DIR" >> "$LOG_FILE" 2>&1
    mkdir -p "$STAGE_DIR" >> "$LOG_FILE" 2>&1
    for item in "$USER_SOFT_DIR"/*.apk; do
        if [ -f "$item" ]; then
            fname=$(basename "$item")
            echo "Installing User APK: $fname..." >> "$LOG_FILE"
            cp -f "$item" "$STAGE_DIR/$fname" >> "$LOG_FILE" 2>&1
            chmod 644 "$STAGE_DIR/$fname" >> "$LOG_FILE" 2>&1

            sz=$(stat -c%s "$STAGE_DIR/$fname" 2>/dev/null || wc -c < "$STAGE_DIR/$fname")
            installed=false
            sess_id=$(pm install-create -i com.android.packageinstaller -r -g -S $sz 2>&1 | tr -cd '0-9')
            if [ -z "$sess_id" ]; then
                sess_id=$(pm install-create -i com.android.vending -r -g -S $sz 2>&1 | tr -cd '0-9')
            fi
            if [ -z "$sess_id" ]; then
                sess_id=$(pm install-create -r -g -S $sz 2>&1 | tr -cd '0-9')
            fi

            if [ -n "$sess_id" ]; then
                echo "Created session $sess_id for $fname" >> "$LOG_FILE"
                pm install-write -S $sz $sess_id base "$STAGE_DIR/$fname" >> "$LOG_FILE" 2>&1
                commit_res=$(pm install-commit $sess_id 2>&1)
                echo "Session commit: $commit_res" >> "$LOG_FILE"
                if echo "$commit_res" | grep -qi "Success"; then
                    installed=true
                else
                    pm install-abandon $sess_id >/dev/null 2>&1
                fi
            fi

            if [ "$installed" = false ]; then
                inst_res=$(pm install -i com.android.packageinstaller -r "$STAGE_DIR/$fname" 2>&1)
                echo "$inst_res" >> "$LOG_FILE"
                if echo "$inst_res" | grep -qi "Success"; then
                    installed=true
                else
                    inst_res=$(pm install -i com.android.vending -r "$STAGE_DIR/$fname" 2>&1)
                    echo "$inst_res" >> "$LOG_FILE"
                    if echo "$inst_res" | grep -qi "Success"; then
                        installed=true
                    else
                        inst_res=$(pm install -r "$STAGE_DIR/$fname" 2>&1)
                        echo "$inst_res" >> "$LOG_FILE"
                        if echo "$inst_res" | grep -qi "Success"; then
                            installed=true
                        fi
                    fi
                fi
            fi

            if [ "$installed" = false ]; then
                cmd_res=$(cmd package install -i com.android.packageinstaller -r "$STAGE_DIR/$fname" 2>&1)
                echo "cmd package: $cmd_res" >> "$LOG_FILE"
                if echo "$cmd_res" | grep -qi "Success"; then
                    installed=true
                fi
            fi

            if [ "$installed" = true ]; then
                echo "✓ $fname installed successfully as User App!" >> "$LOG_FILE"
            else
                echo "⚠ $fname installation rejected by PM." >> "$LOG_FILE"
            fi
            rm -f "$STAGE_DIR/$fname" >> "$LOG_FILE" 2>&1
        fi
    done
    rm -rf "$STAGE_DIR" >> "$LOG_FILE" 2>&1
fi

sync
echo "=== INSTALLATION COMPLETED ===" >> "$LOG_FILE"
"""
        auto_pkg_clean = auto_launch_package.strip() if auto_launch_package else ""
        if auto_pkg_clean:
            script += f"""
# 3. Auto-Launch Primary Application (if requested)
AUTO_LAUNCH_PKG="{auto_pkg_clean}"
if [ -n "$AUTO_LAUNCH_PKG" ]; then
    echo "Auto-launching primary application: $AUTO_LAUNCH_PKG..." >> "$LOG_FILE"
    sleep 2
    monkey -p "$AUTO_LAUNCH_PKG" -c android.intent.category.LAUNCHER 1 >> "$LOG_FILE" 2>&1
fi
"""

        if system_app_count > 0:
            script += """
echo "System app(s) installed. Rebooting infotainment system to register system components..." >> "$LOG_FILE"
sync
(sleep 3; setprop sys.powerctl reboot; reboot) &
"""

        if progress_func:
            progress_func(0.93, "Generating automated installer script (custom_rep.sh)...", 0.0, total_bytes / (1024*1024), total_bytes / (1024*1024))

        os.makedirs(update_dir, exist_ok=True)
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        if progress_func:
            progress_func(0.96, "Writing vehicle manual & manifest flags...", 0.0, total_bytes / (1024*1024), total_bytes / (1024*1024))

        info_path = os.path.join(usb_drive, "Install_Apps_Info.txt")
        info_content = f"""📦 AERO SUITE — INSTALL APPLICATIONS MANUAL
Target Vehicle: Dongfeng Shine (Aeolus D53) Infotainment System
Architecture: ARMv7-a / ARM64 Compatible (Android 8.1 / 9 / 10)

============================================================
1. TECHNICAL OVERVIEW & INTERNAL WORKFLOW
============================================================
The automated payload script executes an intelligent dual-target deployment pipeline:

1. Filesystem Remount:
   - Remounts the system partition with read-write permissions:
     mount -o remount,rw /system

2. System Applications (System Priv-Apps) [{system_app_count} Apps]:
   - Deploys the package to its dedicated system directory: /system/priv-app/<AppName>/
   - Native Library Extraction (.so): Extracts native ARM libraries from the APK (armeabi-v7a / armeabi) into /system/priv-app/<AppName>/lib/arm/ to prevent runtime crashes and satisfy linker dependencies.
   - Filesystem Permissions: Sets standard Android system permissions: 0644 (rw-r--r--) for APK and .so files, and 0755 (rwxr-xr-x) for directories, matching factory OEM pre-installed applications.

3. User Applications (User Apps) [{user_app_count} Apps]:
   - Deploys packages via the official Android Package Manager: pm install -r to /data/app/.

4. Binary AndroidManifest Patching (AXML):
   - Force Portrait: Directly overrides the screenOrientation attribute (0x0101001e) in the compiled binary AndroidManifest.xml when enabled.
   - Block Boot Launch: Neutralizes BOOT_COMPLETED receiver actions to prevent background auto-start and conserve RAM on vehicle startup when enabled.

5. Auto-Launch Post-Installation:
   - Primary Launch Target: {auto_launch_package.strip() or 'None (Manual Launch)'}

6. Verification & Completion:
   - Synchronizes filesystem buffers (sync) and writes complete execution status to the USB log.

============================================================
2. VEHICLE INSTALLATION INSTRUCTIONS
============================================================
1. Turn on the car ignition and wait until the infotainment screen fully boots up.
2. Insert this USB drive into the vehicle USB port. The script will run automatically in the background.
3. Wait approximately 30 to 60 seconds (or until you hear the vehicle's native Chinese voice announcement / صوت التنبيه الصيني الصادر من النظام).
4. Unplug the USB drive immediately.

============================================================
3. STAGED APPLICATIONS ({total_apks} APKS)
============================================================
""" + "\n".join([f" • {a['display_name']} ({a['package']})\n   - Target: {'System App (/system/priv-app)' if a.get('install_target', 'user') == 'system' else 'User App (/data/app)'} | Auto-Launch: {'YES' if a['package'] == auto_launch_package.strip() else 'No'} | Force Portrait: {'Enabled' if a.get('force_portrait', False) else 'Disabled'} | Block Boot: {'Enabled' if a.get('block_boot', False) else 'Disabled'}" for a in selected_apks]) + f"""

{SIGNATURE_BANNER}
"""
        with open(info_path, "w", encoding="utf-8") as f:
            f.write(info_content)

        if progress_func:
            progress_func(0.99, "Flushing filesystem buffers to USB drive...", 0.0, total_bytes / (1024*1024), total_bytes / (1024*1024))
            time.sleep(0.04)
            progress_func(1.0, "Install Apps USB ready!", 0.0, total_bytes / (1024 * 1024), total_bytes / (1024 * 1024))

        _log(f"✓ Install Apps USB prepared successfully ({user_app_count} User Apps, {system_app_count} System Apps).")
        return True
    except Exception as e:
        log_exception(e, "prepare_install_apps_usb")
        _log(f"  ✗ Failed to prepare Install Apps USB: {e}")
        return False
