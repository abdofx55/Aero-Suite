"""
backup.py — Feature 10: Vehicle System & Data Extraction (Car-to-USB) Payload Generator.
Supports 1:1 Personal Private clone and Zero-Leakage Community Shared presets.
"""
import os
import time
from core.constants import FACTORY_PRIV_APPS, FACTORY_APPS
from core.exceptions import log_exception
from core.i18n import t
from payloads.base import clean_usb_drive, write_script_file
from payloads.bash_builder import (
    gen_bash_header,
    gen_backup_init,
    gen_backup_system_settings,
    gen_backup_custom_system_apps,
    gen_backup_user_apks,
    gen_backup_app_data,
    gen_backup_connectivity,
    gen_backup_user_media,
    gen_backup_manifest_and_flags,
)
from payloads.manual_generator import write_payload_manuals


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

    _log(t("logs.prep_usb_header", f"\n── Preparing {b_type_clean.upper()} Backup USB: {usb_drive} ──", title=t("nav.backup_title", "Backup"), drive=usb_drive))
    if b_type_clean == "community":
        _log(t("logs.backup_scope_community", "  Scope:       🌐 Community Shared Preset (Safe for sharing)"))
        _log(t("logs.backup_preset_name", f"  Preset Name: {preset_name or 'Community Preset'}", name=preset_name or "Community Preset"))
        _log(t("logs.backup_author", f"  Author:      {author or 'Anonymous'}", author=author or "Anonymous"))
    else:
        _log(t("logs.backup_scope_personal", "  Scope:       🔒 Personal Private (1:1 Vehicle Clone)"))

    if include_media:
        _log(t("logs.backup_media_included", "  User Media:  Included (Audio, Videos & Downloads)"))
    else:
        _log(t("logs.backup_media_skipped", "  User Media:  Excluded (Apps & Settings only)"))

    if not os.path.exists(usb_drive):
        _log(t("logs.usb_not_found", f"  ✗ USB Drive not found: {usb_drive}", drive=usb_drive))
        return False

    if cancel_check and cancel_check():
        _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
        return False

    try:
        clean_usb_drive(usb_drive, log_func, progress_func, cancel_check, start_pct=0.0, end_pct=0.30)
        if cancel_check and cancel_check():
            _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
            return False
        update_dir = os.path.join(usb_drive, "update")
        os.makedirs(update_dir, exist_ok=True)

        if progress_func:
            progress_func(0.60, f"Writing {b_type_clean.upper()} car backup scripts...", 0.0, 0, 0)

        b_type_sh = b_type_clean.upper()

        script = (
            gen_bash_header(f"{b_type_sh} SYSTEM & DATA BACKUP", "backup.log")
            + gen_backup_init(target_dir_var="TARGET_DIR", b_type=b_type_sh, inc_media=include_media, log_var="LOG_FILE")
            + gen_backup_system_settings(target_dir_var="TARGET_DIR", b_type=b_type_sh, log_var="LOG_FILE")
            + gen_backup_custom_system_apps(target_dir_var="TARGET_DIR", priv_whitelist=FACTORY_PRIV_APPS, app_whitelist=FACTORY_APPS, log_var="LOG_FILE")
            + gen_backup_user_apks(target_dir_var="TARGET_DIR", log_var="LOG_FILE")
            + gen_backup_app_data(target_dir_var="TARGET_DIR", b_type=b_type_sh, log_var="LOG_FILE")
            + gen_backup_connectivity(target_dir_var="TARGET_DIR", b_type=b_type_sh, log_var="LOG_FILE")
            + gen_backup_user_media(target_dir_var="TARGET_DIR", inc_media=include_media, log_var="LOG_FILE")
            + gen_backup_manifest_and_flags(
                target_dir_var="TARGET_DIR",
                b_type=b_type_sh,
                preset_name=preset_name,
                author=author,
                inc_media=include_media,
                log_var="LOG_FILE"
            )
        )
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        if progress_func:
            progress_func(0.85, f"Writing {b_type_clean.upper()} backup manual (HTML)...", 0.0, 0, 0)

        write_payload_manuals(
            usb_drive,
            "Backup_Info",
            "backup",
            b_type=b_type_clean,
            preset_name=preset_name,
            author=author,
            include_media=include_media
        )

        if progress_func:
            progress_func(0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, f"{b_type_clean.capitalize()} Backup USB ready!", 0.0, 0, 0)

        _log(t("logs.prep_usb_success", f"✓ {b_type_sh} Backup USB prepared successfully.", title=t("nav.backup_title", "Backup")))
        return True
    except Exception as e:
        log_exception(e, "prepare_backup_usb")
        _log(t("logs.prep_failed", "  ✗ Failed to prepare {title} USB: {err}", title=t("nav.backup_title", "Backup"), err=str(e)))
        return False
