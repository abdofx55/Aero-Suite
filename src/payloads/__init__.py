"""
payloads package — Modular automotive payload generators for Dongfeng Shine.
Re-exports all payload functions for clean imports and backward compatibility.
"""
from core.constants import FACTORY_PRIV_APPS, FACTORY_APPS, FACTORY_LAUNCHER_PKG, SIGNATURE_BANNER
from payloads.base import (
    write_script_file,
    count_usb_clean_ops,
    clean_usb_drive,
    format_usb_drive,
    extract_so_libs,
    copy_tree_with_progress,
    copy_file_with_chunk_progress,
    patch_apk,
    generate_user_apps_install_script
)
from payloads.install_apps import prepare_install_apps_usb
from payloads.uninstall_apps import prepare_uninstall_apps_usb
from payloads.open_app import prepare_open_app_usb
from payloads.open_settings import prepare_open_settings_usb
from payloads.install_gms import prepare_install_gms_usb
from payloads.uninstall_gms import prepare_uninstall_gms_usb
from payloads.disable_launcher import prepare_disable_launcher_usb
from payloads.enable_launcher import prepare_enable_launcher_usb
from payloads.reboot_screen import prepare_reboot_screen_usb
from payloads.backup import prepare_backup_usb
from payloads.restore import prepare_restore_usb
from payloads.factory_reset import prepare_factory_reset_usb
from payloads.fetch_logs import prepare_fetch_logs_usb
from payloads.vehicle_tweaks import prepare_vehicle_tweaks_usb
from payloads.install_hvac_bar import prepare_install_hvac_bar_usb
from payloads.restore_hvac_bar import prepare_restore_hvac_bar_usb
from payloads.quick_setup import prepare_quick_setup_usb

__all__ = [
    "FACTORY_PRIV_APPS",
    "FACTORY_APPS",
    "FACTORY_LAUNCHER_PKG",
    "SIGNATURE_BANNER",
    "write_script_file",
    "count_usb_clean_ops",
    "clean_usb_drive",
    "format_usb_drive",
    "extract_so_libs",
    "copy_tree_with_progress",
    "copy_file_with_chunk_progress",
    "patch_apk",
    "generate_user_apps_install_script",
    "prepare_install_apps_usb",
    "prepare_uninstall_apps_usb",
    "prepare_open_app_usb",
    "prepare_open_settings_usb",
    "prepare_install_gms_usb",
    "prepare_uninstall_gms_usb",
    "prepare_install_hvac_bar_usb",
    "prepare_restore_hvac_bar_usb",
    "prepare_disable_launcher_usb",
    "prepare_enable_launcher_usb",
    "prepare_reboot_screen_usb",
    "prepare_backup_usb",
    "prepare_restore_usb",
    "prepare_factory_reset_usb",
    "prepare_fetch_logs_usb",
    "prepare_vehicle_tweaks_usb",
    "prepare_quick_setup_usb",
]
