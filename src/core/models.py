"""
models.py — Core domain models and dataclasses for Aero Suite.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class ApkMetadata:
    """Represents an indexed APK package in the repository."""
    filename: str
    path: str
    package: str
    display_name: str
    version_name: str = ""
    version_code: int = 0
    size_mb: float = 0.0
    install_target: str = "user"    # "user" or "system"
    force_portrait: bool = False
    block_boot: bool = False
    auto_launch: bool = False


@dataclass
class UsbDriveModel:
    """Represents a removable USB storage device."""
    letter: str
    drive_letter_only: str
    label: str = "Removable Disk"
    fs_name: str = "FAT32"
    total_gb: float = 0.0
    free_gb: float = 0.0
    used_gb: float = 0.0
    has_backup: bool = False
    is_restore_ready: bool = False
    backup_date: str = ""
    car_model: str = ""
    backup_type: str = "PERSONAL"
    preset_name: str = ""
    author: str = ""


@dataclass
class ProgressUpdate:
    """Represents a progress milestone during payload transfer."""
    percentage: float
    status_text: str
    speed_mb_s: float = 0.0
    current_mb: float = 0.0
    total_mb: float = 0.0
