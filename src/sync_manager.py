"""
sync_manager.py — High-Performance File Sync with Real-Time Progress Engine.
Handles bi-directional synchronization between PC Vault and USB with ETA, MB/s, and chunked streaming.
"""
import os
import re
import time
import shutil
import datetime


def calculate_dir_size(directory: str) -> tuple:
    """Calculates total byte count and file count of a directory."""
    total_bytes = 0
    file_count = 0
    if not os.path.exists(directory):
        return 0, 0
    for root, _, files in os.walk(directory):
        for f in files:
            p = os.path.join(root, f)
            try:
                total_bytes += os.path.getsize(p)
                file_count += 1
            except Exception:
                pass
    return total_bytes, file_count


def copy_file_with_chunk_progress(
    src_file: str,
    dest_file: str,
    chunk_size: int = 256 * 1024,
    chunk_callback=None,
    cancel_check=None
) -> bool:
    """
    Copies a single file from src_file to dest_file in chunks (default 256KB),
    calling chunk_callback(chunk_bytes_copied, file_copied_bytes, file_total_bytes) after each chunk.
    Preserves file timestamps and attributes.
    Returns True on success, False if cancelled or on error.
    """
    if not os.path.isfile(src_file):
        return False

    if cancel_check and cancel_check():
        return False

    os.makedirs(os.path.dirname(os.path.abspath(dest_file)), exist_ok=True)
    file_total_bytes = os.path.getsize(src_file)
    file_copied_bytes = 0

    try:
        with open(src_file, "rb") as f_in, open(dest_file, "wb") as f_out:
            while True:
                if cancel_check and cancel_check():
                    f_out.close()
                    try:
                        os.remove(dest_file)
                    except Exception:
                        pass
                    return False
                chunk = f_in.read(chunk_size)
                if not chunk:
                    break
                f_out.write(chunk)
                file_copied_bytes += len(chunk)
                if chunk_callback:
                    chunk_callback(len(chunk), file_copied_bytes, file_total_bytes)

        try:
            shutil.copystat(src_file, dest_file)
        except Exception:
            pass
        return True
    except Exception:
        return False


def copy_tree_with_progress(src: str, dst: str, progress_callback=None, log_func=None, cancel_check=None, scale_range: tuple = (0.0, 1.0)):
    """
    Copies directory tree from src to dst in 1MB chunks, emitting fine-grained progress.
    progress_callback format:
        progress_callback(percent: float, current_file: str, speed_mb_s: float, copied_mb: float, total_mb: float)
    """
    def _log(msg):
        if log_func:
            log_func(msg)

    total_bytes, total_files = calculate_dir_size(src)
    if total_bytes == 0:
        total_bytes = 1  # prevent div by zero

    copied_bytes = 0
    start_time = time.time()
    chunk_size = 1024 * 1024  # 1MB buffer

    os.makedirs(dst, exist_ok=True)

    for root, _, files in os.walk(src):
        rel_dir = os.path.relpath(root, src)
        dest_dir = os.path.join(dst, rel_dir) if rel_dir != "." else dst
        os.makedirs(dest_dir, exist_ok=True)

        for f in files:
            if cancel_check and cancel_check():
                _log("  ⚠ Operation cancelled by user.")
                return False

            src_file = os.path.join(root, f)
            dest_file = os.path.join(dest_dir, f)
            fname_short = os.path.basename(f)

            try:
                f_size = os.path.getsize(src_file)
                with open(src_file, "rb") as f_in, open(dest_file, "wb") as f_out:
                    while True:
                        if cancel_check and cancel_check():
                            _log("  ⚠ Transfer cancelled.")
                            return False
                        chunk = f_in.read(chunk_size)
                        if not chunk:
                            break
                        f_out.write(chunk)
                        copied_bytes += len(chunk)

                        elapsed = time.time() - start_time
                        speed_mb_s = (copied_bytes / (1024 * 1024)) / max(elapsed, 0.1)
                        s_min, s_max = scale_range
                        percent = s_min + (s_max - s_min) * min(1.0, copied_bytes / total_bytes)
                        copied_mb = copied_bytes / (1024 * 1024)
                        total_mb = total_bytes / (1024 * 1024)

                        if progress_callback:
                            progress_callback(percent, fname_short, speed_mb_s, copied_mb, total_mb)

                # Preserve file timestamps
                shutil.copystat(src_file, dest_file)
            except Exception as e:
                _log(f"  ⚠ Failed copying {fname_short}: {e}")

    if progress_callback:
        progress_callback(scale_range[1], "Complete", 0.0, total_bytes / (1024 * 1024), total_bytes / (1024 * 1024))
    return True


def get_usb_backup_info(usb_drive: str) -> dict:
    """Reads backup metadata (flag, date, model, type, preset, author, media) from USB."""
    usb_drive = usb_drive.rstrip("\\") + "\\"
    flag_path = os.path.join(usb_drive, "backup_complete.flag")
    info = {
        "has_flag": False,
        "backup_date": "",
        "model": "",
        "build": "",
        "status": "",
        "backup_type": "PERSONAL",
        "preset_name": "",
        "author": "",
        "include_media": False
    }
    if os.path.isfile(flag_path):
        info["has_flag"] = True
        try:
            with open(flag_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("BACKUP_DATE="):
                        info["backup_date"] = line.split("=", 1)[1].strip()
                    elif line.startswith("DEVICE_MODEL="):
                        info["model"] = line.split("=", 1)[1].strip()
                    elif line.startswith("BUILD_ID="):
                        info["build"] = line.split("=", 1)[1].strip()
                    elif line.startswith("STATUS="):
                        info["status"] = line.split("=", 1)[1].strip()
                    elif line.startswith("BACKUP_TYPE="):
                        info["backup_type"] = line.split("=", 1)[1].strip().upper()
                    elif line.startswith("PRESET_NAME="):
                        info["preset_name"] = line.split("=", 1)[1].strip()
                    elif line.startswith("AUTHOR="):
                        info["author"] = line.split("=", 1)[1].strip()
                    elif line.startswith("INCLUDE_MEDIA="):
                        val = line.split("=", 1)[1].strip().lower()
                        info["include_media"] = (val in ("1", "true", "yes"))
        except Exception:
            pass
    return info


def find_existing_vault_backup(usb_drive: str, pc_vault_root: str) -> str:
    """
    Checks if this exact car backup has already been synced to the PC Vault.
    Returns path of matching backup folder, or empty string if not found.
    """
    if not os.path.isdir(pc_vault_root):
        return ""

    usb_info = get_usb_backup_info(usb_drive)
    usb_date = usb_info.get("backup_date", "").strip()

    if not usb_date:
        return ""

    for item in sorted(os.listdir(pc_vault_root), reverse=True):
        vault_folder = os.path.join(pc_vault_root, item)
        if not os.path.isdir(vault_folder):
            continue
        flag_file = os.path.join(vault_folder, "backup_complete.flag")
        if os.path.isfile(flag_file):
            try:
                with open(flag_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if line.startswith("BACKUP_DATE="):
                            v_date = line.split("=", 1)[1].strip()
                            if v_date == usb_date:
                                return vault_folder
            except Exception:
                continue
    return ""


def cleanup_duplicate_vault_backups(pc_vault_root: str, log_func=None) -> int:
    """
    Scans the PC Vault, identifies identical duplicate backups by BACKUP_DATE,
    retains the newest folder for each unique date, and deletes redundant copies.
    Returns the number of duplicate folders removed.
    """
    def _log(msg):
        if log_func:
            log_func(msg)

    if not os.path.isdir(pc_vault_root):
        return 0

    seen_dates = {}
    duplicates = []

    # Sort descending by datetime so newest backup comes first
    vault_items = [
        os.path.join(pc_vault_root, i)
        for i in os.listdir(pc_vault_root)
        if os.path.isdir(os.path.join(pc_vault_root, i))
    ]
    vault_items.sort(key=lambda p: parse_backup_datetime(os.path.basename(p), "", p), reverse=True)

    for vault_folder in vault_items:

        flag_file = os.path.join(vault_folder, "backup_complete.flag")
        b_date = ""
        if os.path.isfile(flag_file):
            try:
                with open(flag_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if line.startswith("BACKUP_DATE="):
                            b_date = line.split("=", 1)[1].strip()
                            break
            except Exception:
                pass

        if b_date:
            if b_date not in seen_dates:
                seen_dates[b_date] = vault_folder
            else:
                duplicates.append(vault_folder)

    removed_count = 0
    for dup in duplicates:
        try:
            _log(f"  🗑 Removing duplicate vault folder: {os.path.basename(dup)}...")
            shutil.rmtree(dup, ignore_errors=True)
            removed_count += 1
        except Exception as e:
            _log(f"  ⚠ Failed to remove {dup}: {e}")

    if removed_count > 0:
        _log(f"✓ Cleaned up {removed_count} duplicate backup(s) from PC Vault.")
    return removed_count


def sync_backup_from_usb_to_pc(usb_drive: str, pc_vault_root: str, progress_callback=None, log_func=None, force: bool = False, cancel_check=None) -> str:
    """
    Automatically detects car backup on USB and syncs it to the PC vault.
    Checks for duplicates before copying to avoid redundant disk usage.
    Returns path to created backup folder, or empty string on failure.
    """
    def _log(msg):
        if log_func:
            log_func(msg)

    if cancel_check and cancel_check():
        _log("  ⚠ Backup sync cancelled before start.")
        return ""

    usb_drive = usb_drive.rstrip("\\") + "\\"
    backup_candidates = [
        os.path.join(usb_drive, "Backup"),
        os.path.join(usb_drive, "PersonalBackup"),
    ]
    usb_backup_dir = None
    for c in backup_candidates:
        if os.path.isdir(c):
            usb_backup_dir = c
            break

    if not usb_backup_dir:
        _log(f"  ✗ No backup folder found on USB drive {usb_drive}")
        return ""

    flag_path = os.path.join(usb_drive, "backup_complete.flag")
    if not os.path.isfile(flag_path):
        _log("  ⚠ backup_complete.flag not found on USB. The backup might be incomplete.")

    # Deduplication check: check if this backup has already been synced
    existing = find_existing_vault_backup(usb_drive, pc_vault_root)
    if existing and not force:
        _log(f"\n── Duplicate Backup Detected ──")
        _log(f"  ✓ This exact car backup is ALREADY vaulted on PC at:")
        _log(f"    {os.path.basename(existing)}")
        _log(f"  Skipped duplicate transfer to save ~3.8 GB of disk space.")
        if progress_callback:
            progress_callback(1.0, "Already Synced", 0.0, 1.0, 1.0)
        return existing

    if existing and force:
        # Re-sync into the SAME existing folder, updating in place to avoid duplicate 3.8GB folders
        dest_folder = existing
        _log(f"\n── Updating Existing Vault Backup ──")
        _log(f"  Source (USB): {usb_backup_dir}")
        _log(f"  Target (PC):  {dest_folder} (Overwriting / Refreshing)")
    else:
        info = get_usb_backup_info(usb_drive)
        b_type = info.get("backup_type", "PERSONAL")
        p_name = info.get("preset_name", "")
        author = info.get("author", "")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        if b_type == "COMMUNITY" and p_name:
            clean_p = re.sub(r'[^a-zA-Z0-9_\-]', '_', p_name)
            folder_name = f"Community_{clean_p}_{timestamp}"
        elif b_type == "COMMUNITY":
            folder_name = f"Community_Preset_{timestamp}"
        else:
            folder_name = f"Dongfeng_Backup_{timestamp}"

        dest_folder = os.path.join(pc_vault_root, folder_name)
        os.makedirs(dest_folder, exist_ok=True)
        _log(f"\n── Syncing Car Backup to Local Vault ──")
        _log(f"  Type:         {'🌐 Community Shared Preset' if b_type == 'COMMUNITY' else '🔒 Personal Private Vault'}")
        if p_name:
            _log(f"  Preset:       {p_name}")
        if author:
            _log(f"  Author:       {author}")
        _log(f"  Source (USB): {usb_backup_dir}")
        _log(f"  Target (PC):  {dest_folder}")

    # Copy the backup directory tree with progress and cancellation check
    dest_backup_content = os.path.join(dest_folder, "Backup")
    success = copy_tree_with_progress(usb_backup_dir, dest_backup_content, progress_callback, log_func, cancel_check=cancel_check)

    if cancel_check and cancel_check():
        _log("  ⚠ Backup sync aborted by user.")
        return ""

    if success:
        # Copy flag and log files if present
        for extra in ["backup_complete.flag", "backup.log", "factory_extract.log", "personal_backup.log", "personal_restore.log", "Backup_Info.txt"]:
            extra_path = os.path.join(usb_drive, extra)
            if os.path.isfile(extra_path):
                try:
                    shutil.copy2(extra_path, dest_folder)
                except Exception:
                    pass

        # Update latest pointer file
        latest_file = os.path.join(pc_vault_root, "latest_backup.txt")
        try:
            with open(latest_file, "w", encoding="utf-8") as f:
                f.write(dest_folder)
        except Exception:
            pass

        _log(f"✓ Backup sync completed successfully! Saved to: {dest_folder}")
        return dest_folder
    else:
        _log("✗ Backup sync failed or was cancelled.")
        return ""


def parse_backup_datetime(folder_name: str, b_date_str: str = "", fpath: str = "") -> datetime.datetime:
    """
    Parses a precise datetime object from folder name or backup flag string.
    Supports both legacy (YYYYMMDD_HHMMSS) and clean (YYYY-MM-DD_HH-MM-SS) folder timestamps.
    Falls back to filesystem modification time (mtime).
    """
    # 1. Match YYYY-MM-DD_HH-MM-SS or YYYYMMDD_HHMMSS in folder name
    m = re.search(r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})[-_](\d{2})[-_]?(\d{2})[-_]?(\d{2})', folder_name)
    if m:
        try:
            y, mo, d, h, mi, s = map(int, m.groups())
            return datetime.datetime(y, mo, d, h, mi, s)
        except Exception:
            pass

    # 2. Try parsing BACKUP_DATE from flag
    if b_date_str:
        for fmt in [
            '%a %b %d %H:%M:%S %Z %Y',
            '%a %b %d %H:%M:%S %Y',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S'
        ]:
            try:
                clean_str = re.sub(r'\s+[A-Z]{3,4}\s+', ' ', b_date_str)
                return datetime.datetime.strptime(clean_str, '%a %b %d %H:%M:%S %Y')
            except Exception:
                pass

    # 3. Fallback to filesystem mtime
    try:
        if fpath and os.path.exists(fpath):
            return datetime.datetime.fromtimestamp(os.path.getmtime(fpath))
    except Exception:
        pass

    return datetime.datetime(2000, 1, 1)


def get_local_backups(pc_vault_root: str) -> list:
    """
    Lists all valid local backups stored in the PC vault, strictly sorted from NEWEST to OLDEST.
    Enriches each backup with clear dates (12-hour AM/PM), formatted sizes (GB/MB), order badges, and latest indicators.
    """
    if not os.path.isdir(pc_vault_root):
        return []

    backups = []
    for item in os.listdir(pc_vault_root):
        fpath = os.path.join(pc_vault_root, item)
        if os.path.isdir(fpath) and (os.path.isdir(os.path.join(fpath, "Backup")) or os.path.isdir(os.path.join(fpath, "settings"))):
            size_mb = sum(
                os.path.getsize(os.path.join(root, f))
                for root, _, files in os.walk(fpath)
                for f in files
            ) / (1024 * 1024)

            # Metadata parsing
            b_type = ""
            p_name = ""
            author = ""
            b_date = ""

            flag_file = os.path.join(fpath, "backup_complete.flag")
            if not os.path.isfile(flag_file):
                flag_file = os.path.join(fpath, "Backup", "backup_complete.flag")

            if os.path.isfile(flag_file):
                try:
                    with open(flag_file, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("BACKUP_TYPE="):
                                b_type = line.split("=", 1)[1].strip().upper()
                            elif line.startswith("PRESET_NAME="):
                                p_name = line.split("=", 1)[1].strip()
                            elif line.startswith("AUTHOR="):
                                author = line.split("=", 1)[1].strip()
                            elif line.startswith("BACKUP_DATE="):
                                b_date = line.split("=", 1)[1].strip()
                except Exception:
                    pass

            # If flag did not explicitly specify BACKUP_TYPE (legacy/existing car backups)
            if not b_type:
                if item.startswith("Community_"):
                    b_type = "COMMUNITY"
                elif item.startswith("Dongfeng_Backup_"):
                    b_type = "PERSONAL"
                else:
                    has_private = (
                        os.path.isdir(os.path.join(fpath, "Backup", "wifi_bt")) or
                        os.path.isdir(os.path.join(fpath, "wifi_bt")) or
                        os.path.isfile(os.path.join(fpath, "Backup", "accounts", "accounts.db")) or
                        os.path.isfile(os.path.join(fpath, "Backup", "accounts", "accounts_de.db"))
                    )
                    b_type = "PERSONAL" if has_private else "COMMUNITY"

            dt = parse_backup_datetime(item, b_date, fpath)
            formatted_dt = dt.strftime("%d/%m/%Y — %I:%M %p")
            size_str = f"{size_mb / 1024:.2f} GB" if size_mb >= 1024 else f"{round(size_mb, 1)} MB"

            backups.append({
                "folder_name": item,
                "path": fpath,
                "size_mb": round(size_mb, 1),
                "size_str": size_str,
                "dt": dt,
                "date": b_date or formatted_dt,
                "formatted_datetime": formatted_dt,
                "backup_type": b_type,
                "preset_name": p_name,
                "author": author,
            })

    # Sort strictly from NEWEST to OLDEST (Descending by datetime)
    backups.sort(key=lambda x: x["dt"], reverse=True)

    # Assign order, latest flag, and formulate unambiguous display labels
    for idx, b in enumerate(backups):
        b["order"] = idx + 1
        b["is_latest"] = (idx == 0)
        tag = "★ [الأحدث / LATEST]" if idx == 0 else f"#{idx + 1}"

        if b["backup_type"] == "COMMUNITY":
            lbl_name = b["preset_name"] or b["folder_name"]
            auth = f" (by {b['author']})" if b.get("author") else ""
            b["display_label"] = f"{tag} 🌐 {lbl_name}{auth} • {b['formatted_datetime']} • {b['size_str']}"
        else:
            b["display_label"] = f"{tag} 🔒 {b['formatted_datetime']}  ({b['size_str']})  [{b['folder_name']}]"

    return backups
