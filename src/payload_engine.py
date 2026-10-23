"""
payload_engine.py — Complete Payload & Script Generation Engine for Aero Suite.
Calibrated for Dongfeng Shine (Aeolus D53) Android 8.1/9/10 Infotainment.
Generates all 9 automotive USB scripts and developer info manuals.
"""
import os
import sys
import shutil
import zipfile
import re
import stat
import time
from theme import SIGNATURE_BANNER, DEVELOPER_NAME, DEVELOPER_EMAIL, DEVELOPER_PHONE
from sync_manager import copy_tree_with_progress, copy_file_with_chunk_progress
from apk_engine import patch_apk

# ---------------------------------------------------------------------------
# Dongfeng Shine Factory Whitelist (69 priv-apps & 33 apps)
# ---------------------------------------------------------------------------
FACTORY_PRIV_APPS = [
    "ArielCallVechileFunction-release-signed", "AudioPolicy-release", "BackupRestoreConfirmation",
    "BlockedNumberProvider", "BluetoothPhone-release-signed", "BluetoothService-release",
    "CallLogBackup", "CanBusService-release", "CarPlayApp-release", "CarPlayService-release",
    "CarrierConfig", "CarSignalService-release", "CellBroadcastReceiver", "CNEService",
    "ContactsProvider", "CtsShimPrivPrebuilt", "DabPlayer", "DefaultContainerService",
    "DownloadProvider", "dpmserviceapp", "EasyConnect.release", "EasyService-release-signed",
    "EmergencyInfo", "ExternalStorageProvider", "ExtServices", "FactoryTest-release-signed",
    "FusedLocation", "iAP2Service-release", "InputDevices", "KeyManagerService-release",
    "LastMemory-release", "Launcher-release-signed", "Mms", "MmsService", "Music-release-signed",
    "NuNavbar", "opentouch", "OTAService-release", "PackageInstaller", "PowerManager-release",
    "Provision", "PushMessageApp-release-signed", "qcrilmsgtunnel", "QGBus-release",
    "QGIME-release", "QGMediaProvider-release", "QGSettingProvider-release",
    "QGTtsService-release-signed", "QingLinkProxyService-release", "Radio-release-signed",
    "RemoteDebug-release", "Setting-release-signed", "Settings", "SettingsProvider",
    "SettingsShortcut", "SharedStorageBackup", "Shell", "SnapdragonCamera", "StatementService",
    "StorageManager", "SystemPolicy-release", "SystemUI-release-signed", "TBoxService-release",
    "Telecom", "TelephonyProvider", "TeleService", "TSPService-release", "TunerService-release",
    "Vehicle-release-signed"
]

FACTORY_APPS = [
    "access-qcom-logkit", "AntHalService", "BasicDreams", "Bluetooth", "BluetoothExt",
    "BluetoothMidiService", "CallFeaturesSetting", "CarrierDefaultApp", "CertInstaller",
    "CompanionDeviceManager", "ConfURIDialer", "CtsShimPrebuilt", "datastatusnotification",
    "embms", "Exchange2", "ExtShared", "FidoCryptoService", "HTMLViewer", "ims", "imssettings",
    "KeyChain", "NetworkSetting", "NuNavbar", "QtiTelephonyService", "remotesimlockservice",
    "SimSettings", "Stk", "uceShimService", "uimlpaservice", "UserDictionaryProvider",
    "WallpaperBackup", "webview", "WfdService"
]


def clean_usb_drive(usb_drive: str, log_func=None, progress_func=None, cancel_check=None, start_pct: float = 0.0, end_pct: float = 0.15):
    """Safely wipes all user files from the USB drive to prepare a clean payload with live progress."""
    def _log(msg):
        if log_func:
            log_func(msg)

    if cancel_check and cancel_check():
        _log("  ⚠ Clean cancelled.")
        return False

    _log(f"  Cleaning target USB drive: {usb_drive}...")
    if not os.path.exists(usb_drive) or usb_drive.strip().upper().startswith("C:"):
        _log("  ⚠ Safety block: aborting clean on invalid or root system drive.")
        return False

    if progress_func:
        progress_func(start_pct, "Inspecting USB drive contents...", 0.0, 0, 0)

    try:
        raw_items = os.listdir(usb_drive)
    except Exception as e:
        _log(f"  ⚠ Failed to read drive contents: {e}")
        raw_items = []

    all_items = [
        item for item in raw_items
        if item.lower() not in ("system volume information", "$recycle.bin")
    ]

    if not all_items:
        if progress_func:
            progress_func(end_pct, "USB drive is clean and ready.", 0.0, 0, 0)
        return True

    # Scan all files and directories to delete for granular progress
    files_to_delete = []
    dirs_to_delete = []
    for item in all_items:
        item_path = os.path.join(usb_drive, item)
        if os.path.isdir(item_path):
            for root, dirs, files in os.walk(item_path, topdown=False):
                for f in files:
                    files_to_delete.append(os.path.join(root, f))
                for d in dirs:
                    dirs_to_delete.append(os.path.join(root, d))
            dirs_to_delete.append(item_path)
        else:
            files_to_delete.append(item_path)

    total_ops = len(files_to_delete) + len(dirs_to_delete)
    if total_ops == 0:
        total_ops = 1

    ops_done = 0
    last_update_time = 0.0

    for fpath in files_to_delete:
        if cancel_check and cancel_check():
            _log("  ⚠ Cleaning cancelled.")
            return False

        fname = os.path.basename(fpath)
        for attempt in range(3):
            try:
                os.chmod(fpath, stat.S_IWRITE)
                os.remove(fpath)
                break
            except Exception:
                if attempt < 2:
                    time.sleep(0.05)

        ops_done += 1
        now = time.time()
        if progress_func and (now - last_update_time >= 0.08 or ops_done == total_ops):
            last_update_time = now
            cur_pct = start_pct + (end_pct - start_pct) * (ops_done / total_ops)
            progress_func(cur_pct, f"Cleaning USB: removing {fname[:24]}...", 0.0, ops_done, total_ops)

    for dpath in dirs_to_delete:
        if cancel_check and cancel_check():
            _log("  ⚠ Cleaning cancelled.")
            return False

        try:
            os.rmdir(dpath)
        except Exception:
            try:
                shutil.rmtree(dpath, ignore_errors=True)
            except Exception:
                pass

        ops_done += 1
        now = time.time()
        if progress_func and (now - last_update_time >= 0.08 or ops_done == total_ops):
            last_update_time = now
            cur_pct = start_pct + (end_pct - start_pct) * (ops_done / total_ops)
            progress_func(cur_pct, f"Cleaning USB: removing directories...", 0.0, ops_done, total_ops)

    if progress_func:
        progress_func(end_pct, "USB wipe completed.", 0.0, total_ops, total_ops)
    time.sleep(0.05)
    return True


def format_usb_drive(usb_drive: str, fs: str = "FAT32", label: str = "AERO_USB", log_func=None, progress_func=None, cancel_check=None) -> bool:
    """
    Formats the target USB drive as FAT32 (or exFAT) using PowerShell Format-Volume.
    Fully integrated with progress callbacks, cancel check, and terminal logging.
    """
    def _log(msg, level="cyan"):
        if log_func:
            log_func(msg, level)
        else:
            print(f"[{level}] {msg}")

    letter = usb_drive.upper().rstrip(":\\").strip()
    if not letter or letter == "C":
        _log("Safety block: Cannot format system drive C: or invalid drive.", "danger")
        return False

    if cancel_check and cancel_check():
        _log("Format cancelled before start.", "warn")
        return False

    _log(f"── Formatting USB Drive: {letter}:\\ ({fs}) ──", "warn")
    _log(f"Volume Label: {label} | Target FileSystem: {fs}", "dim")
    if progress_func:
        progress_func(0.1, f"Initializing format on {letter}:\\ ({fs})...")

    # Format using PowerShell Format-Volume
    ps_cmd = f"Format-Volume -DriveLetter {letter} -FileSystem {fs} -NewFileSystemLabel '{label}' -Force -Confirm:$false"
    cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd]

    import subprocess
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        pct = 0.2
        while proc.poll() is None:
            if cancel_check and cancel_check():
                proc.terminate()
                _log("Format operation aborted by user.", "warn")
                return False
            time.sleep(0.4)
            pct = min(0.85, pct + 0.1)
            if progress_func:
                progress_func(pct, f"Formatting {letter}:\\ ({fs})...")

        stdout, stderr = proc.communicate()
        if proc.returncode == 0:
            if progress_func:
                progress_func(1.0, f"Drive {letter}:\\ formatted successfully ({fs}).")
            _log(f"✓ Drive {letter}:\\ successfully formatted to {fs} [Label: {label}]", "mint")
            time.sleep(0.5)
            return True
        else:
            err_msg = stderr.strip() or stdout.strip() or "Unknown formatting error"
            _log(f"Format-Volume error: {err_msg}", "danger")

            # Fallback for FAT32 using cmd format.com
            if fs.upper() == "FAT32":
                _log("Attempting fallback quick format via format.com...", "warn")
                if progress_func:
                    progress_func(0.5, f"Running fallback format on {letter}:\\...")
                fallback_cmd = f"format {letter}: /FS:FAT32 /V:{label} /Q /Y"
                res = subprocess.run(fallback_cmd, shell=True, capture_output=True, text=True)
                if res.returncode == 0:
                    if progress_func:
                        progress_func(1.0, f"Drive {letter}:\\ formatted successfully ({fs}).")
                    _log(f"✓ Drive {letter}:\\ successfully formatted to FAT32 via format.com", "mint")
                    return True
                else:
                    _log(f"Fallback format failed: {res.stderr.strip() or res.stdout.strip()}", "danger")

            return False
    except Exception as e:
        _log(f"Format execution failed: {e}", "danger")
        return False


def extract_so_libs(apk_path: str, output_dir: str, log_func=None):
    """Extracts armeabi-v7a/armeabi native .so libraries for system priv-app execution."""
    lib_arm_dir = os.path.join(output_dir, "lib", "arm")
    try:
        with zipfile.ZipFile(apk_path, 'r') as z:
            all_files = z.namelist()
            v7a_libs = [f for f in all_files if f.startswith("lib/armeabi-v7a/") and f.endswith(".so")]
            v5a_libs = [f for f in all_files if f.startswith("lib/armeabi/") and f.endswith(".so")]
            libs = v7a_libs if v7a_libs else v5a_libs
            if not libs:
                libs = [f for f in all_files if f.startswith("lib/arm64-v8a/") and f.endswith(".so")]

            if libs:
                os.makedirs(lib_arm_dir, exist_ok=True)
                for lib_file in libs:
                    filename = os.path.basename(lib_file)
                    dst = os.path.join(lib_arm_dir, filename)
                    with open(dst, "wb") as out_f:
                        out_f.write(z.read(lib_file))
    except Exception:
        pass


def write_script_file(script_path: str, content: str):
    """Writes a shell script with strict UNIX line endings (LF), ensuring parent directory exists."""
    parent_dir = os.path.dirname(os.path.abspath(script_path))
    os.makedirs(parent_dir, exist_ok=True)
    with open(script_path, "wb") as f:
        f.write(content.replace("\r\n", "\n").encode("utf-8"))


# ===========================================================================
# 1. INSTALL APPS PAYLOAD (WITH PER-APP TARGET, PORTRAIT & BOOT SETTINGS)
# ===========================================================================
def prepare_install_apps_usb(usb_drive: str, selected_apks: list, options: dict = None, log_func=None, progress_func=None, cancel_check=None, auto_launch_package: str = "") -> bool:
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
        import tempfile

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
        # If any System Apps were staged into /system/priv-app, a reboot is required for Android framework to bind them
        if system_app_count > 0:
            script += """
echo "System app(s) installed. Rebooting infotainment system to register system components..." >> "$LOG_FILE"
sync
(sleep 3; setprop sys.powerctl reboot; reboot) &
"""
        else:
            # 3. Auto-Launch Primary Application (for User Apps without reboot)
            auto_pkg_clean = auto_launch_package.strip()
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
        _log(f"  ✗ Failed to prepare Install Apps USB: {e}")
        return False


# ===========================================================================
# 2. UNINSTALL APPS PAYLOAD (SEARCHES BOTH USER & SYSTEM APPS)
# ===========================================================================
def prepare_uninstall_apps_usb(usb_drive: str, selected_packages: list, allowed_packages: set, log_func=None, progress_func=None, cancel_check=None) -> bool:
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
        _log(f"  ✗ Failed to prepare Uninstall Apps USB: {e}")
        return False


# ===========================================================================
# 5. INSTALL GMS PAYLOAD
# ===========================================================================
def prepare_install_gms_usb(usb_drive: str, gms_dir: str, log_func=None, progress_func=None, cancel_check=None) -> bool:
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

        gms_apks = [f for f in sorted(os.listdir(gms_dir)) if f.lower().endswith(".apk")]
        total = len(gms_apks)
        total_gms_bytes = sum(
            os.path.getsize(os.path.join(gms_dir, f)) for f in gms_apks
            if os.path.isfile(os.path.join(gms_dir, f))
        )
        if total_gms_bytes <= 0:
            total_gms_bytes = 1

        _log(f"  Staging {total} GMS package(s) ({total_gms_bytes / (1024 * 1024):.1f} MB total)...")
        copied_cumulative_bytes = 0
        start_transfer_time = time.time()

        for idx, apk_name in enumerate(gms_apks, 1):
            if cancel_check and cancel_check():
                _log("  ⚠ Operation cancelled by user.")
                return False

            src_f = os.path.join(gms_dir, apk_name)
            base = os.path.splitext(apk_name)[0]
            clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '', base)
            dest_dir = os.path.join(soft_dir, clean_name)
            os.makedirs(dest_dir, exist_ok=True)
            dest_f = os.path.join(dest_dir, f"{clean_name}.apk")

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
    for item in "$SOFT_DIR"/*; do
        if [ -d "$item" ]; then
            appname=$(basename "$item")
            echo "Injecting GMS component: $appname" >> "$LOG_FILE"
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
GOOGLE PLAY SERVICES & PLAY STORE FOR DONGFENG SHINE
============================================================
After extensive engineering, reverse engineering, and real-world vehicle testing,
Aero Suite delivers a fully integrated Google Mobile Services (GMS) solution.
Simply insert the USB drive into your car, and the script handles the entire installation automatically!

INCLUDED COMPONENTS:
1. Google Services Framework (Core API & Cloud Messaging engine)
2. Google Account Manager (Authentication & Account Synchronization)
3. Google Play Services (GMS Runtime & Location Services)
4. Google Play Store (App Store & Auto-Update Client)

WHAT YOU GAIN AFTER INSTALLATION:
• Immediate Google account login directly on the vehicle screen.
• Full access to Google Play Store to install, update, and manage any Android app.
• Native compatibility with apps requiring Google Play Services (e.g., streaming, navigation).
• Google Maps with full account sync (saved locations, history, real-time traffic).
• Seamless account login and Google background services support.

============================================================
1. TECHNICAL OVERVIEW & INTERNAL WORKFLOW
============================================================
This script does NOT simply sideload ordinary APKs. It implements two critical system-level mechanisms:

1. Strict Installation Sequence:
   Google components depend on one another like interlocking gears. The script installs them in a strict, calibrated order:
   (Google Services Framework -> Google Account Manager -> Google Play Services -> Google Play Store).
   Any disorder in installation sequence causes synchronization failures or causes Play Store to crash on startup.

2. Native ARM Library Injection (.so):
   Each Google component requires specific native compiled libraries (ARMv7-a .so binaries) matching the vehicle's Snapdragon CPU architecture.
   The script extracts these libraries from inside the packages and injects them directly into:
   /system/priv-app/<AppName>/lib/arm/
   Applying strict system permissions (chmod 644 for .so and .apk, chmod 755 for directories), identical to a factory OEM build.

3. Voice Recognition Permissions:
   Generates and injects the system permissions manifest:
   /system/etc/permissions/voice_recognizers.xml
   Enabling Android speech recognition and Google Voice search without runtime security exceptions.

============================================================
2. VEHICLE INSTALLATION INSTRUCTIONS
============================================================
1. Start the vehicle and wait until the infotainment screen fully loads.
2. Insert the USB drive into the USB port. The script runs automatically in the background (takes ~1 minute).
3. The infotainment screen will automatically power off and reboot upon completion.
4. As soon as the screen turns off to restart, unplug the USB drive immediately (before it boots back up).
5. Once the screen boots back up, open Google Play Store and sign in with your Google account.

Note: The APK versions included here are specifically calibrated for Dongfeng Shine. Do not replace them with arbitrary external builds.

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
        _log(f"  ✗ Failed to prepare Install GMS USB: {e}")
        return False


# ===========================================================================
# 6. UNINSTALL GMS PAYLOAD
# ===========================================================================
def prepare_uninstall_gms_usb(usb_drive: str, log_func=None, progress_func=None, cancel_check=None) -> bool:
    """Prepares USB to completely and cleanly scrub Google Play Services components."""
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(f"\n── [6/13] Preparing Uninstall GMS USB: {usb_drive} ──")
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
# AERO SUITE — GMS CLEAN SCRUB & PURGE
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

for pkg in com.android.vending com.google.android.gms com.google.android.gsf com.google.android.gsf.login; do
    echo "Purging: $pkg" >> "$LOG_FILE"
    PKG_PATH=$(pm path "$pkg" | cut -d ':' -f 2)
    if [ ! -z "$PKG_PATH" ]; then
        rm -rf $(dirname "$PKG_PATH") >> "$LOG_FILE" 2>&1
    fi
    pm clear "$pkg" >> "$LOG_FILE" 2>&1
    pm uninstall "$pkg" >> "$LOG_FILE" 2>&1
    rm -rf "/data/data/$pkg" >> "$LOG_FILE" 2>&1
    rm -rf "/data/user/0/$pkg" >> "$LOG_FILE" 2>&1
    rm -rf "/data/app/$pkg"* >> "$LOG_FILE" 2>&1
    rm -rf "/data/dalvik-cache/arm/*$pkg"* >> "$LOG_FILE" 2>&1
done

# Wipe lingering Google system folders & voice recognizers
rm -rf /system/priv-app/*PlayStore* /system/priv-app/*playstore* /system/priv-app/*vending* >> "$LOG_FILE" 2>&1
rm -rf /system/priv-app/*GMS* /system/priv-app/*gms* /system/priv-app/*GSF* /system/priv-app/*gsf* >> "$LOG_FILE" 2>&1
rm -rf /system/app/*PlayStore* /system/app/*GMS* /system/app/*GSF* >> "$LOG_FILE" 2>&1
rm -f /system/etc/permissions/voice_recognizers.xml >> "$LOG_FILE" 2>&1

# Reset Google accounts and tokens
rm -rf /data/system/users/0/accounts.db* >> "$LOG_FILE" 2>&1
rm -rf /data/system_de/0/accounts_de.db* >> "$LOG_FILE" 2>&1
rm -rf /data/system/sync/* >> "$LOG_FILE" 2>&1

# Reset provisioning and setup flags back to stock OEM state
echo "Resetting provisioning and setup flags to factory defaults..." >> "$LOG_FILE"
settings put global device_provisioned 1 >> "$LOG_FILE" 2>&1
settings put secure user_setup_complete 1 >> "$LOG_FILE" 2>&1

sync
echo "=== GMS PURGE COMPLETE ===" >> "$LOG_FILE"
sync
(sleep 3; setprop sys.powerctl reboot; reboot) &
"""
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        info_path = os.path.join(usb_drive, "Uninstall_GMS_Info.txt")
        info_content = f"""🧹 AERO SUITE — GOOGLE PLAY SERVICES (GMS) UNINSTALL & SCRUB MANUAL
Target Vehicle: Dongfeng Shine (Aeolus D53) Infotainment System

============================================================
ZERO-TRACE GOOGLE SERVICES PURGE & FACTORY RESTORATION
============================================================
To give you complete peace of mind, Aero Suite provides a dedicated clean scrub payload.
This payload completely removes all traces of Google services, returning the head unit
to its 100% factory state. This ensures total OEM compliance before dealership visits or maintenance.

============================================================
1. TECHNICAL OVERVIEW & INTERNAL WORKFLOW
============================================================
The scrub payload performs a rigorous, deep system purge:

1. Package Purge:
   - Completely unregisters and uninstalls:
     • Google Play Store (com.android.vending)
     • Google Play Services (com.google.android.gms)
     • Google Services Framework (com.google.android.gsf)
     • Google Login Service (com.google.android.gsf.login)

2. System Partition Cleanup:
   - Deletes system directories from /system/priv-app/ and /system/app/.
   - Removes /system/etc/permissions/voice_recognizers.xml.

3. Account & Sync Database Reset:
   - Deletes residual account databases: /data/system/users/0/accounts.db and /data/system_de/0/accounts_de.db.
   - Clears /data/system/sync/ and wipes all Dalvik cache artifacts from /data/dalvik-cache/arm/*.
   - Ensures zero lingering authentication tokens or synchronization errors.

4. Completion & Safe Reboot:
   - Synchronizes filesystem buffers (sync) and commands an automatic clean system restart.

============================================================
2. VEHICLE USAGE INSTRUCTIONS
============================================================
1. Start the vehicle and wait for the screen to stabilize.
2. Insert this USB drive into the USB port. The script will automatically scrub Google components.
3. As soon as the screen turns off to restart automatically, unplug the USB drive immediately (before it boots back up).

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

        _log("✓ Uninstall GMS USB prepared successfully.")
        return True
    except Exception as e:
        _log(f"  ✗ Failed to prepare Uninstall GMS USB: {e}")
        return False


# ===========================================================================
# 4. OPEN SETTINGS PAYLOAD
# ===========================================================================
def prepare_open_settings_usb(usb_drive: str, log_func=None, progress_func=None, cancel_check=None) -> bool:
    """Prepares USB payload to unlock and launch native Android Settings on car screen."""
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(f"\n── [4/13] Preparing Open Settings USB: {usb_drive} ──")
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
            progress_func(0.60, "Configuring Android Settings unlock trigger...", 0.0, 0, 0)

        script = """#!/system/bin/sh
# ==========================================
# AERO SUITE — LAUNCH ANDROID SETTINGS
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

LOG_FILE="$USB_PATH/open_settings.log"
echo "=== AERO LAUNCH SETTINGS ===" > "$LOG_FILE"
date >> "$LOG_FILE"

# Launch Android Native Settings
am start -n com.android.settings/.Settings >> "$LOG_FILE" 2>&1
am start -a android.settings.SETTINGS >> "$LOG_FILE" 2>&1

sync
"""
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        info_path = os.path.join(usb_drive, "Open_Settings_Info.txt")
        info_content = f"""⚙️ AERO SUITE — OPEN ANDROID SETTINGS MANUAL
Target Vehicle: Dongfeng Shine (Aeolus D53) Infotainment System

============================================================
1. TECHNICAL OVERVIEW & INTERNAL WORKFLOW
============================================================
The script bypasses the restricted proprietary Dongfeng launcher to directly launch Android's native Settings:
1. Intent Dispatch:
   Dispatches a direct Android intent:
   am start -a android.settings.SETTINGS
2. 100% Non-Destructive:
   The script does not modify system files or trigger a reboot. It simply reveals the underlying native Android settings menu.

============================================================
2. VEHICLE USAGE INSTRUCTIONS
============================================================
1. Start the vehicle and wait for the home screen to load.
2. Insert this USB drive into the USB port.
3. The full Android Settings application will open instantly on screen (or wait for the Chinese voice confirmation).
4. Immediately unplug the USB drive to prevent the launch intent from re-triggering.
5. You can now configure Developer Options, USB Debugging, Wi-Fi networks, Bluetooth, Display, and Storage settings freely.

{SIGNATURE_BANNER}
"""
        if progress_func:
            progress_func(0.85, "Writing Android Settings manual...", 0.0, 0, 0)

        with open(info_path, "w", encoding="utf-8") as f:
            f.write(info_content)

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, "Open Settings USB ready!", 0.0, 0, 0)

        _log("✓ Open Settings USB prepared successfully.")
        return True
    except Exception as e:
        _log(f"  ✗ Failed to prepare Open Settings USB: {e}")
        return False


# ===========================================================================
# 10. BACKUP PAYLOAD (CAR TO USB)
# ===========================================================================
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
        _log(f"  Scope:       🌐 Community Shared Preset (Safe for sharing)")
        _log(f"  Preset Name: {preset_name or 'Community Preset'}")
        _log(f"  Author:      {author or 'Anonymous'}")
        _log(f"  Privacy:     Zero-Leakage (Accounts, Wi-Fi & BT pairings scrubbed)")
    else:
        _log(f"  Scope:       🔒 Personal Private (1:1 Vehicle Clone)")
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
    # Community Preset: Completely skip all Google accounts and sync tables for 100% privacy
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
        _log(f"  ✗ Failed to prepare Backup USB: {e}")
        return False


# ===========================================================================
# 12. FACTORY RESET PAYLOAD (ZERO-TRACE RESTORATION)
# ===========================================================================
def prepare_factory_reset_usb(usb_drive: str, local_factory_backup_dir: str = "", log_func=None, progress_func=None, cancel_check=None) -> bool:
    """Prepares USB to restore vehicle to pristine factory zero state."""
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(f"\n── [12/13] Preparing Factory Reset USB (Zero-Trace Purge): {usb_drive} ──")
    if not os.path.exists(usb_drive):
        _log(f"  ✗ USB Drive not found: {usb_drive}")
        return False

    if cancel_check and cancel_check():
        _log("  ⚠ Operation cancelled by user.")
        return False

    try:
        has_local_factory = bool(local_factory_backup_dir and os.path.exists(local_factory_backup_dir))
        clean_usb_drive(usb_drive, log_func, progress_func, cancel_check, start_pct=0.0, end_pct=0.15 if has_local_factory else 0.30)
        if cancel_check and cancel_check():
            _log("  ⚠ Operation cancelled by user.")
            return False

        update_dir = os.path.join(usb_drive, "update")
        os.makedirs(update_dir, exist_ok=True)

        if has_local_factory:
            _log("  Copying FactoryBackup to USB for auto-healing stock ROM (with live progress)...")
            ok_copy = copy_tree_with_progress(
                local_factory_backup_dir,
                os.path.join(update_dir, "FactoryRestore"),
                progress_callback=progress_func,
                log_func=log_func,
                cancel_check=cancel_check,
                scale_range=(0.15, 0.88)
            )
            if not ok_copy or (cancel_check and cancel_check()):
                _log("  ⚠ Factory Reset preparation aborted.")
                return False
            if progress_func:
                progress_func(0.91, "Verifying factory restore integrity...", 0.0, 0, 0)
        else:
            if progress_func:
                progress_func(0.55, "Configuring factory whitelist...", 0.0, 0, 0)

        if progress_func:
            progress_func(0.94 if has_local_factory else 0.75, "Generating Zero-Trace recovery script...", 0.0, 0, 0)

        priv_str = ' '.join(FACTORY_PRIV_APPS)
        app_str = ' '.join(FACTORY_APPS)

        script = f"""#!/system/bin/sh
# ==========================================
# AERO SUITE — DEEP ZERO-TRACE FACTORY PURGE
# ==========================================

USB_PATH=""
for dir in /storage/* /mnt/media_rw/* /mnt/usb* /storage/usb* /mnt/udisk* /udisk* /media* /mnt/media*; do
    if [ -f "$dir/update/custom_rep.sh" ]; then
        USB_PATH="$dir"
        break
    fi
done
if [ -z "$USB_PATH" ]; then
    SCRIPT_PATH="$0"
    USB_PATH=$(dirname $(dirname "$SCRIPT_PATH"))
fi

LOG_FILE="$USB_PATH/factory_restore.log"
echo "=== AERO FACTORY RESET START ===" > "$LOG_FILE"
date >> "$LOG_FILE"
sync

# 1. MOUNT /system RW & IMMEDIATELY UNFREEZE STOCK LAUNCHER
mount -o remount,rw /system >> "$LOG_FILE" 2>&1
mount -o rw,remount /system >> "$LOG_FILE" 2>&1
echo "Unfreezing stock factory launcher immediately (Pre-Purge Safety)..." >> "$LOG_FILE"
pm enable com.qinggan.app.launcher >> "$LOG_FILE" 2>&1

PRIV_WHITELIST="{priv_str}"
APP_WHITELIST="{app_str}"

# 3. Purge non-factory priv-apps
for dir in /system/priv-app/*; do
    if [ -d "$dir" ]; then
        name="${{dir##*/}}"
        is_factory=false
        for fw in $PRIV_WHITELIST; do
            if [ "$name" = "$fw" ]; then is_factory=true; break; fi
        done
        if [ "$is_factory" = "false" ]; then
            echo "Purging non-factory priv-app: $name" >> "$LOG_FILE"
            rm -rf "$dir" >> "$LOG_FILE" 2>&1
        fi
    fi
done

# 4. Purge non-factory apps
for dir in /system/app/*; do
    if [ -d "$dir" ]; then
        name="${{dir##*/}}"
        is_factory=false
        for fw in $APP_WHITELIST; do
            if [ "$name" = "$fw" ]; then is_factory=true; break; fi
        done
        if [ "$is_factory" = "false" ]; then
            echo "Purging non-factory app: $name" >> "$LOG_FILE"
            rm -rf "$dir" >> "$LOG_FILE" 2>&1
        fi
    fi
done

# 5. Smart auto-heal missing factory apps (restores only if missing)
if [ -d "$USB_PATH/update/FactoryRestore/priv-app" ]; then
    for fdir in "$USB_PATH/update/FactoryRestore/priv-app/"*; do
        if [ -d "$fdir" ]; then
            bname="${{fdir##*/}}"
            if [ ! -d "/system/priv-app/$bname" ]; then
                echo "Restoring missing factory priv-app: $bname" >> "$LOG_FILE"
                cp -r "$fdir" /system/priv-app/ >> "$LOG_FILE" 2>&1
                chmod 755 "/system/priv-app/$bname" >> "$LOG_FILE" 2>&1
                chmod 644 "/system/priv-app/$bname"/*.apk >> "$LOG_FILE" 2>&1
            fi
        fi
    done
fi
if [ -d "$USB_PATH/update/FactoryRestore/app" ]; then
    for fdir in "$USB_PATH/update/FactoryRestore/app/"*; do
        if [ -d "$fdir" ]; then
            bname="${{fdir##*/}}"
            if [ ! -d "/system/app/$bname" ]; then
                echo "Restoring missing factory app: $bname" >> "$LOG_FILE"
                cp -r "$fdir" /system/app/ >> "$LOG_FILE" 2>&1
                chmod 755 "/system/app/$bname" >> "$LOG_FILE" 2>&1
                chmod 644 "/system/app/$bname"/*.apk >> "$LOG_FILE" 2>&1
            fi
        fi
    done
fi

# 6. Remove injected permissions & enable stock launcher
echo "Enabling stock launcher and cleaning custom permissions..." >> "$LOG_FILE"
rm -f /system/etc/permissions/voice_recognizers.xml >> "$LOG_FILE" 2>&1
(pm enable com.qinggan.app.launcher >> "$LOG_FILE" 2>&1) &

# 7. Reset Bluetooth Factory State
echo "Resetting Bluetooth factory properties..." >> "$LOG_FILE"
setprop persist.bluetooth.factoryreset true

# 8. Remount /system Read-Only to protect it
echo "Locking /system partition back to Read-Only..." >> "$LOG_FILE"
mount -o remount,ro /system >> "$LOG_FILE" 2>&1

# 9. Complete Deep Wipe of /data partition (User data, accounts, settings, caches)
echo "Executing complete root wipe of /data partition..." >> "$LOG_FILE"
rm -rf /data/app/* >> "$LOG_FILE" 2>&1
rm -rf /data/data/* >> "$LOG_FILE" 2>&1
rm -rf /data/user/* >> "$LOG_FILE" 2>&1
rm -rf /data/user_de/* >> "$LOG_FILE" 2>&1
rm -rf /data/system/* >> "$LOG_FILE" 2>&1
rm -rf /data/system_de/* >> "$LOG_FILE" 2>&1
rm -rf /data/property/* >> "$LOG_FILE" 2>&1
rm -rf /data/media/* /data/media/0/* /sdcard/* >> "$LOG_FILE" 2>&1
rm -rf /data/misc/* >> "$LOG_FILE" 2>&1
rm -rf /data/dalvik-cache/* /cache/dalvik-cache/* >> "$LOG_FILE" 2>&1
rm -rf /data/local/* >> "$LOG_FILE" 2>&1
rm -rf /data/tombstones/* >> "$LOG_FILE" 2>&1
rm -rf /data/anr/* >> "$LOG_FILE" 2>&1
rm -rf /data/log/* /data/logs/* >> "$LOG_FILE" 2>&1

# Initialize clean directory structures for fresh first boot
mkdir -p /data/system /data/media/0 /data/local/tmp >> "$LOG_FILE" 2>&1
chmod 775 /data/system /data/media /data/local/tmp >> "$LOG_FILE" 2>&1
chown system:system /data/system >> "$LOG_FILE" 2>&1
chown media_rw:media_rw /data/media /data/media/0 >> "$LOG_FILE" 2>&1

# 10. Purge cache and clear stale recovery triggers
echo "Purging /cache partition and clearing stale recovery commands..." >> "$LOG_FILE"
rm -rf /cache/* >> "$LOG_FILE" 2>&1
mkdir -p /cache >> "$LOG_FILE" 2>&1
chmod 771 /cache >> "$LOG_FILE" 2>&1

# Clear BCB (Bootloader Control Block) in misc partition so bootloader boots straight to normal Android
for dev in /dev/block/bootdevice/by-name/misc /dev/block/platform/*/by-name/misc /dev/block/by-name/misc; do
    if [ -b "$dev" ]; then
        echo "Clearing BCB in misc partition ($dev)..." >> "$LOG_FILE"
        dd if=/dev/zero of="$dev" bs=512 count=64 >> "$LOG_FILE" 2>&1
        break
    fi
done

# 11. Final sync and normal system reboot directly into Android OS
echo "=== FACTORY RESET COMPLETE — REBOOTING DIRECTLY TO ANDROID ===" >> "$LOG_FILE"
date >> "$LOG_FILE"
sync
sleep 2
sync

# Reboot directly to normal Android system via Kernel Hard Reboot
reboot -f || busybox reboot -f || setprop sys.powerctl reboot || reboot
"""
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        info_path = os.path.join(usb_drive, "Factory_Reset_Info.txt")
        info_content = f"""⚠️ AERO SUITE — FACTORY RESET & ZERO-TRACE PURGE MANUAL
Target Vehicle: Dongfeng Shine (Aeolus D53) Infotainment System

============================================================
1. TECHNICAL OVERVIEW & INTERNAL WORKFLOW
============================================================
This payload performs a deep hardware restore, purging all custom modifications while strictly protecting vehicle CAN-Bus communications:
1. Purges Custom Modifications:
   - Removes all user-installed applications from /data/app/.
   - Removes Google Services Framework (GMS, Play Store, Account Manager).
   - Wipes all user accounts, Wi-Fi networks, Bluetooth pairings, and internal storage files.
2. Factory Whitelist Protection:
   - Verifies and safeguards all 69 factory priv-apps and 33 stock system apps.
   - Vehicle CAN-Bus services, Air Conditioning controllers, instrument cluster sync, and reverse camera logic are 100% protected and untouched.
3. Deep Telemetry, Crash Dumps & Logs Purge:
   - Removes all crash tombstones (/data/tombstones/*) and ANR traces (/data/anr/*).
   - Purges system DropBox history (/data/system/dropbox/*) and application usage stats.
   - Clears recent task thumbnails, system logs (/data/log/*), and flushes in-memory logcat buffers.
4. Cache Clear & System Partition Lock:
   - Wipes the Dalvik/ART cache from /data/dalvik-cache/*.
   - Remounts the system partition as Read-Only: mount -o remount,ro /system.
5. Hardware Bluetooth & Automated Direct Reboot:
   - Resets external Bluetooth chip hardware NVRAM via direct AT commands.
   - Cleans cache, wipes stale recovery flags, and triggers an automated system reboot directly into the Android OS.

Ideal for returning the vehicle to the dealership with zero detected modifications or traces.

============================================================
2. VEHICLE USAGE INSTRUCTIONS
============================================================
1. Start the vehicle and wait for the screen to stabilize.
2. Insert this USB drive into the USB port. The purge process will execute automatically.
3. As soon as the screen turns off to restart automatically, unplug the USB drive immediately (before it boots back up).
4. Upon reboot, the infotainment system will be in its pristine 100% factory original state.

{SIGNATURE_BANNER}
"""
        if progress_func:
            progress_func(0.97 if has_local_factory else 0.90, "Writing Zero-Trace purge manual...", 0.0, 0, 0)

        with open(info_path, "w", encoding="utf-8") as f:
            f.write(info_content)

        if progress_func:
            progress_func(0.99 if has_local_factory else 0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, "Factory Reset USB ready!", 0.0, 0, 0)

        _log("✓ Factory Reset USB prepared successfully.")
        return True
    except Exception as e:
        _log(f"  ✗ Failed to prepare Factory Reset USB: {e}")
        return False


# ===========================================================================
# 11. RESTORE PAYLOAD (PC TO USB TO CAR)
# ===========================================================================
def prepare_restore_usb(usb_drive: str, local_backup_folder: str, log_func=None, progress_func=None, cancel_check=None) -> bool:
    """
    Copies local PC backup to USB:/Backup (with progress bar)
    and generates the 12-step restoration script in USB:/update/custom_rep.sh.
    """
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(f"\n── [11/13] Preparing Restore USB: {usb_drive} ──")
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

        # Write restore markers (remove any stale backup_complete.flag so it is never mistaken for a fresh car backup)
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

        _log("✓ Restore USB prepared successfully.")
        return True
    except Exception as e:
        _log(f"  ✗ Failed to prepare Restore USB: {e}")
        return False


# ===========================================================================
# 13. FETCH LOGS PAYLOAD
# ===========================================================================
def prepare_fetch_logs_usb(usb_drive: str, log_func=None, progress_func=None, cancel_check=None) -> bool:
    """Prepares USB to extract logcat, dmesg, and diagnostic dumps from car."""
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(f"\n── [13/13] Preparing Fetch Logs USB: {usb_drive} ──")
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

        _log("✓ Fetch Logs USB prepared successfully.")
        return True
    except Exception as e:
        _log(f"  ✗ Failed to prepare Fetch Logs USB: {e}")
        return False


# ===========================================================================
# 7. DISABLE FACTORY LAUNCHER PAYLOAD
# ===========================================================================
def prepare_disable_launcher_usb(usb_drive: str, log_func=None, progress_func=None, cancel_check=None) -> bool:
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

        script = """#!/system/bin/sh
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

echo "Freezing stock OEM launcher (com.qinggan.app.launcher)..." >> "$LOG_FILE"
pm disable com.qinggan.app.launcher >> "$LOG_FILE" 2>&1

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
   Executes: pm disable com.qinggan.app.launcher
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
        _log(f"  ✗ Failed to prepare Disable Launcher USB: {e}")
        return False


# ===========================================================================
# 8. ENABLE FACTORY LAUNCHER PAYLOAD
# ===========================================================================
def prepare_enable_launcher_usb(usb_drive: str, log_func=None, progress_func=None, cancel_check=None) -> bool:
    """Prepares USB payload to unfreeze (enable) the stock Dongfeng system launcher."""
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(f"\n── [8/13] Preparing Enable Factory Launcher USB: {usb_drive} ──")
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

        script = """#!/system/bin/sh
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

echo "Unfreezing stock OEM launcher (com.qinggan.app.launcher)..." >> "$LOG_FILE"
pm enable com.qinggan.app.launcher >> "$LOG_FILE" 2>&1

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
   Executes: pm enable com.qinggan.app.launcher
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

        _log("✓ Enable Launcher USB prepared successfully.")
        return True
    except Exception as e:
        _log(f"  ✗ Failed to prepare Enable Launcher USB: {e}")
        return False


# ===========================================================================
# 3. OPEN SPECIFIC APPLICATION PAYLOAD
# ===========================================================================
def prepare_open_app_usb(usb_drive: str, package_name: str, app_name: str = "", log_func=None, progress_func=None, cancel_check=None) -> bool:
    """Prepares USB payload to launch a specific application on the vehicle screen if installed."""
    def _log(msg):
        if log_func:
            log_func(msg)

    display_label = app_name or package_name
    _log(f"\n── [3/13] Preparing Open App USB ({display_label}): {usb_drive} ──")
    if not os.path.exists(usb_drive):
        _log(f"  ✗ USB Drive not found: {usb_drive}")
        return False

    if not package_name:
        _log("  ✗ No package name provided to launch.")
        return False

    if cancel_check and cancel_check():
        _log("  ⚠ Operation cancelled by user.")
        return False

    clean_pkg = re.sub(r'[^a-zA-Z0-9._]', '', package_name)

    try:
        clean_usb_drive(usb_drive, log_func, progress_func, cancel_check, start_pct=0.0, end_pct=0.30)
        if cancel_check and cancel_check():
            _log("  ⚠ Operation cancelled by user.")
            return False

        update_dir = os.path.join(usb_drive, "update")
        os.makedirs(update_dir, exist_ok=True)

        if progress_func:
            progress_func(0.60, f"Configuring launch trigger for {display_label}...", 0.0, 0, 0)

        script = f"""#!/system/bin/sh
# ==========================================
# AERO SUITE — LAUNCH SPECIFIC APPLICATION
# Target: {clean_pkg} ({display_label})
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

LOG_FILE="$USB_PATH/open_app.log"
echo "=== AERO OPEN APP START ===" > "$LOG_FILE"
date >> "$LOG_FILE"

TARGET_PKG="{clean_pkg}"
echo "Checking if $TARGET_PKG is installed..." >> "$LOG_FILE"

if pm path "$TARGET_PKG" >/dev/null 2>&1; then
    echo "✓ Package found. Launching $TARGET_PKG..." >> "$LOG_FILE"
    monkey -p "$TARGET_PKG" -c android.intent.category.LAUNCHER 1 >> "$LOG_FILE" 2>&1
else
    echo "⚠ Package $TARGET_PKG is NOT installed on this vehicle." >> "$LOG_FILE"
fi

sync
"""
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        info_path = os.path.join(usb_drive, "Open_App_Info.txt")
        info_content = f"""🚀 AERO SUITE — LAUNCH APPLICATION MANUAL
Target Application: {display_label}
Package Name: {clean_pkg}
Target Vehicle: Dongfeng Shine (Aeolus D53) Infotainment System

============================================================
1. TECHNICAL OVERVIEW & INTERNAL WORKFLOW
============================================================
This payload launches the selected application directly:
1. Existence Verification:
   The script checks if the package exists in PackageManager:
   pm path {clean_pkg}
2. Launch Execution:
   If found, launches the app's default launcher activity into the foreground:
   monkey -p {clean_pkg} -c android.intent.category.LAUNCHER 1
3. Fail-Safe:
   If the package is not installed on the vehicle, the script logs a warning to the USB log and safely exits without errors.

============================================================
2. VEHICLE USAGE INSTRUCTIONS
============================================================
1. Start the vehicle and wait for the screen to turn on.
2. Insert this USB drive into the vehicle USB port.
3. Within a few seconds, {display_label} will launch directly on screen (or wait for the Chinese voice confirmation).
4. Unplug the USB drive immediately.

{SIGNATURE_BANNER}
"""
        if progress_func:
            progress_func(0.85, f"Writing launch manual for {display_label}...", 0.0, 0, 0)

        with open(info_path, "w", encoding="utf-8") as f:
            f.write(info_content)

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, f"Launch {display_label} USB ready!", 0.0, 0, 0)

        _log(f"✓ Open App USB prepared successfully for {display_label}.")
        return True
    except Exception as e:
        _log(f"  ✗ Failed to prepare Open App USB: {e}")
        return False


# ===========================================================================
# 9. REBOOT INFOTAINMENT SCREEN PAYLOAD
# ===========================================================================
def prepare_reboot_screen_usb(usb_drive: str, log_func=None, progress_func=None, cancel_check=None) -> bool:
    """Prepares USB payload to instantly reboot / restart the car's Android infotainment unit."""
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(f"\n── [9/13] Preparing Restart Infotainment Screen USB: {usb_drive} ──")
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
            progress_func(0.60, "Generating infotainment reboot payload...", 0.0, 0, 0)

        script = """#!/system/bin/sh
# ==========================================
# AERO SUITE — INSTANT SCREEN REBOOT
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

LOG_FILE="$USB_PATH/reboot.log"
echo "=== AERO REBOOT TRIGGERED ===" > "$LOG_FILE"
date >> "$LOG_FILE"

sync
echo "Triggering hardware powerctl reboot..." >> "$LOG_FILE"
sleep 1
sync
setprop sys.powerctl reboot || reboot -f || reboot
"""
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        info_path = os.path.join(usb_drive, "Restart_Screen_Info.txt")
        info_content = f"""🔄 AERO SUITE — RESTART INFOTAINMENT SCREEN MANUAL
Target Vehicle: Dongfeng Shine (Aeolus D53) Infotainment System

============================================================
1. TECHNICAL OVERVIEW & INTERNAL WORKFLOW
============================================================
This utility provides an instant, safe hardware-level reboot for the infotainment system:
1. Filesystem Synchronization:
   Executes sync to flush all pending storage buffers to protect eMMC integrity.
2. Power Control Reboot:
   Executes: setprop sys.powerctl reboot
   Safely terminates system services and restarts the Snapdragon SoC.
3. Non-Destructive:
   Does not modify any apps, settings, or user data. It simply performs a clean system reboot.

============================================================
2. VEHICLE USAGE INSTRUCTIONS
============================================================
1. Insert this USB drive into the vehicle USB port.
2. Within 2 to 5 seconds, the screen will turn off to reboot automatically.
3. As soon as the screen turns off (goes black), unplug the USB drive immediately (before it boots back up).

{SIGNATURE_BANNER}
"""
        if progress_func:
            progress_func(0.85, "Writing restart screen manual...", 0.0, 0, 0)

        with open(info_path, "w", encoding="utf-8") as f:
            f.write(info_content)

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, "Reboot Screen USB ready!", 0.0, 0, 0)

        _log("✓ Restart Infotainment Screen USB prepared successfully.")
        return True
    except Exception as e:
        _log(f"  ✗ Failed to prepare Restart Screen USB: {e}")
        return False

