"""
restore.py — Feature 11: 12-Step Full ROM, System Apps & Data Restoration Payload Generator.
Restores saved vehicle PC Vault archives with intelligent UID mapping, SELinux relabeling, and hard reboot.
"""
import os
import time
from core.exceptions import log_exception
from core.i18n import t
from payloads.base import clean_usb_drive, write_script_file, copy_tree_with_progress
from payloads.bash_builder import (
    gen_bash_header,
    gen_state_init,
    gen_wait_for_boot_completed,
    gen_stage_reboot,
    gen_mount_rw,
    gen_mount_ro,
    gen_restore_header_check,
    gen_restore_pkg_resolver,
    gen_restore_custom_system_apps,
    gen_restore_voice_and_keystore,
    gen_restore_accounts,
    gen_restore_properties_and_flags,
    gen_restore_settings_xml,
    gen_restore_package_restrictions,
    gen_restore_user_apps,
    gen_restore_app_data_with_uid_mapping,
    gen_restore_connectivity,
    gen_restore_user_media,
    gen_restore_final_hardening,
)
from payloads.manual_generator import write_payload_manuals


def prepare_restore_usb(
    usb_drive: str,
    local_backup_folder: str,
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """
    Copies local PC backup to USB:/Backup (with progress bar)
    and generates the 12-step restoration script in USB:/update/custom_rep.sh.
    """
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(t("logs.prep_usb_header", f"\n── Preparing Restore USB: {usb_drive} ──", title=t("nav.restore_title", "Restore"), drive=usb_drive))
    if not os.path.exists(usb_drive):
        _log(t("logs.usb_not_found", f"  ✗ USB Drive not found: {usb_drive}", drive=usb_drive))
        return False
    if not os.path.exists(local_backup_folder):
        _log(t("logs.local_backup_not_found", f"  ✗ Local backup folder not found: {local_backup_folder}", path=local_backup_folder))
        return False

    if cancel_check and cancel_check():
        _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
        return False

    try:
        clean_usb_drive(usb_drive, log_func, progress_func, cancel_check, start_pct=0.0, end_pct=0.15)
        if cancel_check and cancel_check():
            _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
            return False

        update_dir = os.path.join(usb_drive, "update")
        os.makedirs(update_dir, exist_ok=True)

        # Check where backup contents are
        src_backup_data = os.path.join(local_backup_folder, "Backup")
        if not os.path.isdir(src_backup_data):
            src_backup_data = local_backup_folder

        dest_usb_backup = os.path.join(usb_drive, "Backup")
        _log(t("logs.transferring_backup_files", "  Transferring PC backup files to USB..."))
        ok_copy = copy_tree_with_progress(src_backup_data, dest_usb_backup, progress_func, log_func, cancel_check=cancel_check, scale_range=(0.15, 0.88))
        if not ok_copy or (cancel_check and cancel_check()):
            _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
            return False

        if progress_func:
            progress_func(0.90, "Verifying backup metadata & vehicle profile...", 0.0, 0, 0)

        folder_bname = os.path.basename(local_backup_folder.rstrip("/\\"))
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
            _log(t("logs.preset_community", "  ✓ Community Preset: Safe Restore (Google accounts, Wi-Fi & BT preserved)."))
        else:
            _log(t("logs.preset_personal", "  ✓ Personal Vault: 1:1 Full Vehicle State Restore."))

        # Write restore markers (remove any stale backup_complete.flag)
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

        # 12-Step Restore Script (Multi-Stage State Machine Architecture)
        stage1_body = (
            gen_mount_rw(log_var="LOG_FILE")
            + 'echo "1/12 Unfreezing stock launcher..." >> "$LOG_FILE"\n'
            + 'pm enable com.qinggan.app.launcher >> "$LOG_FILE" 2>&1\n'
            + gen_restore_custom_system_apps(target_dir_var="$TARGET_DIR", log_var="LOG_FILE")
            + gen_restore_voice_and_keystore(target_dir_var="$TARGET_DIR", log_var="LOG_FILE")
            + gen_mount_ro(log_var="LOG_FILE")
            + gen_stage_reboot(
                "restore_stage1",
                reboot_delay=3,
                reboot_msg="Rebooting infotainment system to initialize restored system apps..."
            )
        )

        stage2_body = (
            '\necho "=== STAGE 2: RESTORING DATA, APPS & CONFIGURATIONS ===" >> "$LOG_FILE"\n'
            + gen_wait_for_boot_completed(settle_seconds=5, log_var="LOG_FILE")
            + gen_restore_accounts(target_dir_var="$TARGET_DIR", log_var="LOG_FILE")
            + gen_restore_properties_and_flags(target_dir_var="$TARGET_DIR", log_var="LOG_FILE")
            + gen_restore_settings_xml(target_dir_var="$TARGET_DIR", log_var="LOG_FILE")
            + gen_restore_package_restrictions(target_dir_var="$TARGET_DIR", log_var="LOG_FILE")
            + gen_restore_user_apps(target_dir_var="$TARGET_DIR", log_var="LOG_FILE")
            + gen_restore_app_data_with_uid_mapping(target_dir_var="$TARGET_DIR", log_var="LOG_FILE")
            + gen_restore_connectivity(target_dir_var="$TARGET_DIR", log_var="LOG_FILE")
            + gen_restore_user_media(target_dir_var="$TARGET_DIR", log_var="LOG_FILE")
            + gen_restore_final_hardening(target_dir_var="$TARGET_DIR", log_var="LOG_FILE")
        )

        script = (
            gen_bash_header("COMPLETE 12-STEP RESTORE\n# Multi-Stage State Machine Architecture", "restore.log")
            + gen_state_init()
            + gen_restore_header_check(log_var="LOG_FILE")
            + gen_restore_pkg_resolver(target_dir_var="$TARGET_DIR")
            + 'if [ ! -f "$STATE_DIR/restore_stage1.done" ]; then\n'
            + 'echo "=== STAGE 1: RESTORING SYSTEM PARTITION & PRIV-APPS ===" >> "$LOG_FILE"\n'
            + stage1_body
            + '\nfi\n'
            + stage2_body
        )
        if progress_func:
            progress_func(0.93, "Generating 12-step restoration script (custom_rep.sh)...", 0.0, 0, 0)

        os.makedirs(update_dir, exist_ok=True)
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        if progress_func:
            progress_func(0.96, "Writing restoration manual & verification flags...", 0.0, 0, 0)

        write_payload_manuals(usb_drive, "Restore_Info", "restore", folder_bname=folder_bname, is_community=is_community)

        if progress_func:
            progress_func(0.99, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, "Restore USB ready!", 0.0, 0, 0)

        _log(t("logs.prep_usb_success", "✓ Restore USB prepared successfully.", title=t("nav.restore_title", "Restore")))
        return True
    except Exception as e:
        log_exception(e, "prepare_restore_usb")
        _log(t("logs.prep_failed", "  ✗ Failed to prepare {title} USB: {err}", title=t("nav.restore_title", "Restore"), err=str(e)))
        return False
