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
            _log("  ⚠ Cleaning cancelled.")
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
            _log("  ⚠ Cleaning cancelled.")
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
    cancel_check=None
) -> bool:
    """
    Formats target USB drive using PowerShell Format-Volume with cmd fallback.
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

    ps_cmd = f"Format-Volume -DriveLetter {letter} -FileSystem {fs} -NewFileSystemLabel '{label}' -Force -Confirm:$false"
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
        log_exception(e, "format_usb_drive")
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
    except Exception as e:
        log_exception(e, f"extract_so_libs: {apk_path}")
