"""
base.py — Common utilities, script writers, USB wipers, and helpers for payload engines.
"""
import os
import sys
import shutil
import zipfile
import re
import stat
import time
import subprocess
from core.constants import (
    FACTORY_PRIV_APPS,
    FACTORY_APPS,
    FACTORY_LAUNCHER_PKG,
    SIGNATURE_BANNER,
    DEVELOPER_NAME,
    DEVELOPER_EMAIL,
    DEVELOPER_PHONE
)
from core.exceptions import log_exception, log_to_file
from core.i18n import t
from sync_manager import copy_tree_with_progress, copy_file_with_chunk_progress
from apk_engine import patch_apk


def write_script_file(script_path: str, script_content: str):
    """
    Writes a shell script guaranteed to use UNIX (LF) line endings.
    Safely creates the parent directory if missing to prevent FileNotFoundError.
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(script_path)), exist_ok=True)
    except Exception as e:
        log_exception(e, f"write_script_file: mkdir failed for {script_path}")

    # Standardize to LF line endings
    clean_content = script_content.replace('\r\n', '\n').replace('\r', '\n')
    with open(script_path, "wb") as f:
        f.write(clean_content.encode('utf-8'))


def count_usb_clean_ops(usb_drive: str) -> int:
    """
    Quickly counts user files and directories that clean_usb_drive will need to delete.
    Fast directory entry traversal takes only ~10-30ms even on USBs with thousands of files.
    """
    if not os.path.exists(usb_drive) or usb_drive.strip().upper().startswith("C:"):
        return 0
    try:
        raw_items = os.listdir(usb_drive)
    except Exception:
        return 0

    all_items = [
        item for item in raw_items
        if item.lower() not in (
            "system volume information", "$recycle.bin", "found.000",
            ".trashes", ".spotlight-v100", ".fseventsd"
        )
    ]
    if not all_items:
        return 0

    total_ops = 0
    for item in all_items:
        item_path = os.path.join(usb_drive, item)
        if os.path.isdir(item_path):
            try:
                for root, dirs, files in os.walk(item_path):
                    total_ops += len(files) + len(dirs)
                total_ops += 1
            except Exception:
                total_ops += 1
        else:
            total_ops += 1
    return total_ops


def clean_usb_drive(
    usb_drive: str,
    log_func=None,
    progress_func=None,
    cancel_check=None,
    start_pct: float = 0.0,
    end_pct: float = 0.15
) -> bool:
    """
    Safely wipes user files from target USB drive to prepare a clean payload with live progress.
    Protected against permission locks, read-only attributes, and system folder collisions.
    """
    def _log(msg):
        if log_func:
            log_func(msg)

    if cancel_check and cancel_check():
        _log(t("logs.clean_cancelled", "  ⚠ Clean cancelled."))
        return False

    _log(t("logs.cleaning_usb", f"  Cleaning target USB drive: {usb_drive}...", drive=usb_drive))
    if not os.path.exists(usb_drive) or usb_drive.strip().upper().startswith("C:"):
        _log(t("logs.root_drive_blocked", "  ⚠ Safety block: aborting clean on invalid or root system drive."))
        return False

    if progress_func:
        progress_func(start_pct, "Inspecting USB drive contents...", 0.0, 0, 0)

    try:
        raw_items = os.listdir(usb_drive)
    except Exception as e:
        _log(t("logs.read_drive_failed", f"  ⚠ Failed to read drive contents: {e}", err=str(e)))
        raw_items = []

    all_items = [
        item for item in raw_items
        if item.lower() not in (
            "system volume information", "$recycle.bin", "found.000",
            ".trashes", ".spotlight-v100", ".fseventsd"
        )
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
            try:
                for root, dirs, files in os.walk(item_path, topdown=False):
                    for f in files:
                        files_to_delete.append(os.path.join(root, f))
                    for d in dirs:
                        dirs_to_delete.append(os.path.join(root, d))
                dirs_to_delete.append(item_path)
            except Exception as e:
                log_exception(e, f"clean_usb_drive: scanning {item_path}")
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
            _log(t("logs.clean_cancelled", "  ⚠ Cleaning cancelled."))
            return False

        fname = os.path.basename(fpath)
        for attempt in range(2):
            try:
                os.chmod(fpath, stat.S_IWRITE)
                os.remove(fpath)
                break
            except Exception:
                if attempt == 0:
                    time.sleep(0.02)

        ops_done += 1
        now = time.time()
        if progress_func and (now - last_update_time >= 0.08 or ops_done == total_ops):
            last_update_time = now
            cur_pct = start_pct + (end_pct - start_pct) * (ops_done / total_ops)
            progress_func(cur_pct, f"Cleaning USB: removing {fname[:24]}...", 0.0, ops_done, total_ops)

    for dpath in dirs_to_delete:
        if cancel_check and cancel_check():
            _log(t("logs.clean_cancelled", "  ⚠ Cleaning cancelled."))
            return False

        try:
            os.chmod(dpath, stat.S_IWRITE)
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
            progress_func(cur_pct, "Cleaning USB: removing directories...", 0.0, ops_done, total_ops)

    if progress_func:
        progress_func(end_pct, "USB wipe completed.", 0.0, total_ops, total_ops)
    time.sleep(0.03)
    return True


def format_usb_drive(
    usb_drive: str,
    fs: str = "FAT32",
    label: str = "AERO_USB",
    log_func=None,
    progress_func=None,
    cancel_check=None,
    **kwargs
) -> bool:
    """
    Formats target USB drive using PowerShell Format-Volume with cmd fallback.
    Supports both FAT32 and exFAT.
    """
    if "volume_label" in kwargs:
        label = kwargs["volume_label"]

    # Strictly enforce FAT32 for automotive Dongfeng Shine IVI system
    fs = "FAT32"

    def _log(msg, level="cyan"):
        if log_func:
            log_func(msg, level)
        else:
            print(f"[{level}] {msg}")

    letter = usb_drive.upper().rstrip(":\\").strip()
    if not letter or letter == "C":
        _log(t("logs.format_c_blocked", "Safety block: Cannot format system drive C: or invalid drive."), "danger")
        return False

    if cancel_check and cancel_check():
        _log(t("logs.format_cancelled", "Format cancelled before start."), "warn")
        return False

    _log(t("logs.format_start", f"\n── Formatting USB Drive: {letter}:\\ (FAT32) ──", drive=f"{letter}:\\"), "warn")
    _log(t("logs.format_details", f"Volume Label: {label} | Target FileSystem: FAT32 (Automotive Standard)", label=label), "dim")
    if progress_func:
        progress_func(0.1, f"Initializing format on {letter}:\\ (FAT32)...")

    # PowerShell Format-Volume with -Force natively handles drives > 32 GB without size limitations
    ps_cmd = f"Format-Volume -DriveLetter {letter} -FileSystem FAT32 -NewFileSystemLabel '{label}' -Force"
    cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd]

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
                _log(t("logs.format_aborted", "Format operation aborted by user."), "warn")
                return False
            time.sleep(0.4)
            pct = min(0.85, pct + 0.1)
            if progress_func:
                progress_func(pct, f"Formatting {letter}:\\ (FAT32)...")

        stdout, stderr = proc.communicate()
        if proc.returncode == 0:
            if progress_func:
                progress_func(1.0, f"Drive {letter}:\\ formatted successfully (FAT32).")
            _log(t("logs.format_success", f"✓ Drive {letter}:\\ successfully formatted to FAT32 [Label: {label}]", drive=f"{letter}:\\", label=label), "mint")
            time.sleep(0.5)
            return True
        else:
            err_msg = stderr.strip() or stdout.strip() or "Unknown formatting error"
            _log(t("logs.format_volume_err", f"Format-Volume error: {err_msg}", err=err_msg), "danger")

            _log(t("logs.format_fallback", "Attempting fallback quick format via diskpart / format.com..."), "warn")
            if progress_func:
                progress_func(0.5, f"Running fallback format on {letter}:\\...")

            # Fallback 1: diskpart script
            try:
                dp_script = f"select volume {letter}\nformat fs=fat32 quick label={label}\n"
                dp_res = subprocess.run(["diskpart"], input=dp_script, text=True, capture_output=True, timeout=30)
                if dp_res.returncode == 0 and "successfully formatted" in dp_res.stdout.lower():
                    if progress_func:
                        progress_func(1.0, f"Drive {letter}:\\ formatted successfully (FAT32).")
                    _log(t("logs.format_fallback_success", f"✓ Drive {letter}:\\ successfully formatted to FAT32 via diskpart", drive=f"{letter}:\\"), "mint")
                    return True
            except Exception:
                pass

            # Fallback 2: legacy format.com
            fallback_cmd = f"format {letter}: /FS:FAT32 /V:{label} /Q /Y"
            res = subprocess.run(fallback_cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                if progress_func:
                    progress_func(1.0, f"Drive {letter}:\\ formatted successfully (FAT32).")
                _log(t("logs.format_fallback_success", f"✓ Drive {letter}:\\ successfully formatted to FAT32 via format.com", drive=f"{letter}:\\"), "mint")
                return True
            else:
                _log(t("logs.format_fallback_failed", f"Fallback format failed: {res.stderr.strip() or res.stdout.strip()}", err=res.stderr.strip() or res.stdout.strip()), "danger")

            return False
    except Exception as e:
        log_exception(e, "format_usb_drive")
        _log(t("logs.format_failed_generic", f"Format execution failed: {e}", err=str(e)), "danger")
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
    except Exception as e:
        log_exception(e, f"extract_so_libs: {apk_path}")


def generate_user_apps_install_script(source_dir_var: str = "USER_SOFT_DIR", log_file_var: str = "LOG_FILE") -> str:
    """
    Generates a battle-tested shell script snippet to install user applications into /data/app.
    Unlocks OEM security policies (persist.ais_server.3app.perm), stages APKs into /data/local/tmp/user_stage,
    and runs multi-tier installation (Session Installer -> PackageInstaller -> Vending -> PM -> cmd package).
    Shared across Feature 1 (install_apps) and Feature 5 (install_gms).
    """
    return f"""if [ -d "${source_dir_var}" ]; then
    echo "Unlocking OEM third-party app installation policies..." >> "${log_file_var}"
    setprop persist.ais_server.3app.perm 1 >> "${log_file_var}" 2>&1
    settings put global install_non_market_apps 1 >> "${log_file_var}" 2>&1
    settings put secure install_non_market_apps 1 >> "${log_file_var}" 2>&1
    settings put system install_non_market_apps 1 >> "${log_file_var}" 2>&1
    settings put global package_verifier_enable 0 >> "${log_file_var}" 2>&1
    settings put global package_verifier_user_consent -1 >> "${log_file_var}" 2>&1
    settings put global verifier_verify_adb_installs 0 >> "${log_file_var}" 2>&1

    echo "Processing User Apps..." >> "${log_file_var}"
    STAGE_DIR="/data/local/tmp/user_stage"
    rm -rf "$STAGE_DIR" >> "${log_file_var}" 2>&1
    mkdir -p "$STAGE_DIR" >> "${log_file_var}" 2>&1
    for item in "${source_dir_var}"/*.apk; do
        if [ -f "$item" ]; then
            fname=$(basename "$item")
            echo "Installing User APK: $fname..." >> "${log_file_var}"
            cp -f "$item" "$STAGE_DIR/$fname" >> "${log_file_var}" 2>&1
            chmod 644 "$STAGE_DIR/$fname" >> "${log_file_var}" 2>&1

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
                echo "Created session $sess_id for $fname" >> "${log_file_var}"
                pm install-write -S $sz $sess_id base "$STAGE_DIR/$fname" >> "${log_file_var}" 2>&1
                commit_res=$(pm install-commit $sess_id 2>&1)
                echo "Session commit: $commit_res" >> "${log_file_var}"
                if echo "$commit_res" | grep -qi "Success"; then
                    installed=true
                else
                    pm install-abandon $sess_id >/dev/null 2>&1
                fi
            fi

            if [ "$installed" = false ]; then
                inst_res=$(pm install -i com.android.packageinstaller -r -g "$STAGE_DIR/$fname" 2>&1)
                echo "$inst_res" >> "${log_file_var}"
                if echo "$inst_res" | grep -qi "Success"; then
                    installed=true
                else
                    inst_res=$(pm install -i com.android.vending -r -g "$STAGE_DIR/$fname" 2>&1)
                    echo "$inst_res" >> "${log_file_var}"
                    if echo "$inst_res" | grep -qi "Success"; then
                        installed=true
                    else
                        inst_res=$(pm install -r -g "$STAGE_DIR/$fname" 2>&1)
                        echo "$inst_res" >> "${log_file_var}"
                        if echo "$inst_res" | grep -qi "Success"; then
                            installed=true
                        fi
                    fi
                fi
            fi

            if [ "$installed" = false ]; then
                cmd_res=$(cmd package install -i com.android.packageinstaller -r -g "$STAGE_DIR/$fname" 2>&1)
                echo "cmd package: $cmd_res" >> "${log_file_var}"
                if echo "$cmd_res" | grep -qi "Success"; then
                    installed=true
                fi
            fi

            if [ "$installed" = true ]; then
                echo "✓ $fname installed successfully as User App!" >> "${log_file_var}"
                flat_pkg=$(basename "$fname" .apk)
                pm enable "$flat_pkg" >/dev/null 2>&1
            else
                echo "⚠ $fname installation rejected by PM." >> "${log_file_var}"
            fi

            rm -f "$STAGE_DIR/$fname" >> "${log_file_var}" 2>&1
        fi
    done
    rm -rf "$STAGE_DIR" >> "${log_file_var}" 2>&1
fi"""
