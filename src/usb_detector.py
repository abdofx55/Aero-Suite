"""
usb_detector.py — Automatic USB Drive Detection & Monitoring for Windows.
Detects removable flash drives, queries volume label, disk space, and car backup flags.
"""
import os
import time
import shutil
import string
import threading
import ctypes


class UsbDriveInfo:
    def __init__(self, letter: str):
        self.letter = letter.upper().rstrip(":\\") + ":\\"
        self.drive_letter_only = letter.upper()[0]
        self.label = ""
        self.fs_name = ""
        self.total_gb = 0.0
        self.free_gb = 0.0
        self.used_gb = 0.0
        self.has_backup = False
        self.is_restore_ready = False
        self.has_update = False
        self.has_logs = False
        self.backup_date = ""
        self.car_model = ""
        self.backup_type = "PERSONAL"
        self.preset_name = ""
        self.author = ""
        self._refresh()

    def _refresh(self):
        try:
            # Volume Label and File System
            vol_buf = ctypes.create_unicode_buffer(260)
            fs_buf = ctypes.create_unicode_buffer(260)
            ctypes.windll.kernel32.GetVolumeInformationW(
                self.letter, vol_buf, 260, None, None, None, fs_buf, 260
            )
            self.label = vol_buf.value or "Removable Disk"
            self.fs_name = fs_buf.value or "FAT32"
        except Exception:
            self.label = "Removable Disk"
            self.fs_name = "FAT32"

        try:
            total, used, free = shutil.disk_usage(self.letter)
            self.total_gb = round(total / (1024 ** 3), 1)
            self.used_gb = round(used / (1024 ** 3), 1)
            self.free_gb = round(free / (1024 ** 3), 1)
        except Exception:
            self.total_gb = 0.0
            self.free_gb = 0.0

        # Check if USB is prepared as a Restore payload
        self.is_restore_ready = (
            os.path.exists(os.path.join(self.letter, "restore_ready.flag")) or
            os.path.exists(os.path.join(self.letter, "Restore_Info.txt"))
        )

        flag_path = os.path.join(self.letter, "backup_complete.flag")
        backup_dir1 = os.path.join(self.letter, "Backup")
        backup_dir2 = os.path.join(self.letter, "PersonalBackup")

        if os.path.exists(flag_path):
            try:
                with open(flag_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("BACKUP_DATE="):
                            self.backup_date = line.split("=", 1)[1].strip()
                        elif line.startswith("DEVICE_MODEL="):
                            self.car_model = line.split("=", 1)[1].strip()
                        elif line.startswith("BACKUP_TYPE="):
                            self.backup_type = line.split("=", 1)[1].strip().upper()
                        elif line.startswith("PRESET_NAME="):
                            self.preset_name = line.split("=", 1)[1].strip()
                        elif line.startswith("AUTHOR="):
                            self.author = line.split("=", 1)[1].strip()
                        elif "RESTORE_READY=true" in line:
                            self.is_restore_ready = True
            except Exception:
                pass

        rep_sh = os.path.join(self.letter, "update", "custom_rep.sh")
        if os.path.exists(rep_sh):
            try:
                with open(rep_sh, "r", encoding="utf-8", errors="ignore") as f:
                    content_head = f.read(500)
                    if "RESTORE" in content_head:
                        self.is_restore_ready = True
            except Exception:
                pass

        # has_backup is ONLY True for real car backups taken FROM the car (not restore payloads!)
        if self.is_restore_ready:
            self.has_backup = False
        else:
            self.has_backup = bool(self.backup_date and os.path.exists(flag_path) and (os.path.isdir(backup_dir1) or os.path.isdir(backup_dir2)))

        self.has_update = os.path.exists(os.path.join(self.letter, "update", "custom_rep.sh"))
        self.has_logs = any(os.path.exists(os.path.join(self.letter, f)) for f in ["install_log.txt", "backup.log", "factory_extract.log", "personal_backup.log", "personal_restore.log", "logcat.txt"])

    def __repr__(self):
        return f"<UsbDrive {self.letter} [{self.label}] {self.free_gb}GB free>"


def get_removable_drives() -> list:
    """Returns a list of all detected removable USB drives."""
    drives = []
    for letter in string.ascii_uppercase:
        drive_path = f"{letter}:\\"
        try:
            # DRIVE_REMOVABLE = 2
            if ctypes.windll.kernel32.GetDriveTypeW(drive_path) == 2:
                drives.append(UsbDriveInfo(drive_path))
        except Exception:
            continue
    return drives


class UsbWatcher:
    """
    Background worker that monitors USB insertion/removal and fires callbacks.
    """
    def __init__(self, callback, interval_sec: float = 1.5):
        self.callback = callback
        self.interval = interval_sec
        self._running = False
        self._thread = None
        self._last_drives = set()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _monitor_loop(self):
        while self._running:
            try:
                current_drives = get_removable_drives()
                current_state = {(d.letter, d.has_backup) for d in current_drives}
                
                # Check for changes in drive letters or backup status
                if current_state != self._last_drives:
                    self._last_drives = current_state
                    if self.callback:
                        self.callback(current_drives)
            except Exception:
                pass
            time.sleep(self.interval)
