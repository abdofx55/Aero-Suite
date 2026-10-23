"""
payload_engine.py — High-Level Facade for Aero Suite Automotive Payload Generation.
Re-exports modular generators from src/payloads/ while maintaining 100% backward compatibility.
Calibrated for Dongfeng Shine (Aeolus D53) Android 8.1 / 9 / 10 IVI Systems.
"""

from payloads import (
    FACTORY_PRIV_APPS,
    FACTORY_APPS,
    FACTORY_LAUNCHER_PKG,
    SIGNATURE_BANNER,
    write_script_file,
    clean_usb_drive,
    format_usb_drive,
    extract_so_libs,
    copy_tree_with_progress,
    copy_file_with_chunk_progress,
    patch_apk,
    prepare_install_apps_usb,
    prepare_uninstall_apps_usb,
    prepare_open_app_usb,
    prepare_open_settings_usb,
    prepare_install_gms_usb,
    prepare_uninstall_gms_usb,
    prepare_disable_launcher_usb,
    prepare_enable_launcher_usb,
    prepare_reboot_screen_usb,
    prepare_backup_usb,
    prepare_restore_usb,
    prepare_factory_reset_usb,
    prepare_fetch_logs_usb,
)

__all__ = [
    "FACTORY_PRIV_APPS",
    "FACTORY_APPS",
    "FACTORY_LAUNCHER_PKG",
    "SIGNATURE_BANNER",
    "write_script_file",
    "clean_usb_drive",
    "format_usb_drive",
    "extract_so_libs",
    "copy_tree_with_progress",
    "copy_file_with_chunk_progress",
    "patch_apk",
    "prepare_install_apps_usb",
    "prepare_uninstall_apps_usb",
    "prepare_open_app_usb",
    "prepare_open_settings_usb",
    "prepare_install_gms_usb",
    "prepare_uninstall_gms_usb",
    "prepare_disable_launcher_usb",
    "prepare_enable_launcher_usb",
    "prepare_reboot_screen_usb",
    "prepare_backup_usb",
    "prepare_restore_usb",
    "prepare_factory_reset_usb",
    "prepare_fetch_logs_usb",
]
