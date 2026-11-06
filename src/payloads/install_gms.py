"""
install_gms.py — Feature 5: Google Play Services (GMS) Injection Payload Generator.
Injects Google Services Framework, Play Services, Account Manager, and Play Store in calibrated dependency order.
"""
import os
import re
import time
from core.constants import SIGNATURE_BANNER, GMS_PACKAGES_SEQUENCE, GMS_FULL_PURGE_PACKAGES, GMS_FULL_PRIVAPP_PATTERNS
from core.exceptions import log_exception
from core.i18n import t
from payloads.base import (
    clean_usb_drive,
    count_usb_clean_ops,
    write_script_file,
    extract_so_libs,
    copy_file_with_chunk_progress,
    generate_user_apps_install_script
)
from payloads.bash_builder import (
    gen_bash_header,
    gen_state_init,
    gen_wait_for_boot_completed,
    gen_stage_reboot,
    gen_mount_rw,
    gen_mount_ro,
    gen_purge_apps,
    gen_purge_stale_gms,
    gen_install_system_apps,
    gen_gms_compatibility_and_arabic,
    gen_install_user_apps,
    gen_gboard_config,
    gen_direct_settings_xml_patch,
    gen_bash_footer
)
from payloads.manual_generator import generate_info_content, write_payload_manuals

GMS_STALE_PACKAGES = GMS_FULL_PURGE_PACKAGES
GMS_STALE_PATTERNS = GMS_FULL_PRIVAPP_PATTERNS


def _get_gms_order_prefix(filename: str) -> str:
    """
    Determines calibrated installation order prefix (1..6) based on GMS & system component role.
    Ensures shell globbing executes components in strict dependency sequence:
    1: Framework (GSF) -> 2: Account Manager (Login) -> 3: Play Services (GMS) -> 4: Play Store (Vending) -> 5: Speech Services (TTS) -> 6: Files by Google
    """
    f_lower = filename.lower()
    if "framework" in f_lower or ("gsf" in f_lower and "login" not in f_lower):
        return "1_"
    elif "login" in f_lower or "account" in f_lower:
        return "2_"
    elif ("gms" in f_lower and "gsf" not in f_lower) or "gmscore" in f_lower or "play_services" in f_lower:
        return "3_"
    elif "store" in f_lower or "vending" in f_lower or "phonesky" in f_lower:
        return "4_"
    elif "speech" in f_lower or "tts" in f_lower:
        return "5_"
    elif "files" in f_lower or "nbu" in f_lower:
        return "6_"
    elif "search" in f_lower or "quicksearch" in f_lower or "googleapp" in f_lower or "velvet" in f_lower:
        return "7_"
    return "8_"



def _is_system_priv_app(filename: str) -> bool:
    """Identifies core Google Services components that MUST reside in /system/priv-app/."""
    f_lower = filename.lower()
    # Exclude userland applications
    if any(k in f_lower for k in ["gboard", "chrome", "maps"]):
        return False
    return any(k in f_lower for k in ["gsf", "framework", "gms", "login", "store", "vending", "phonesky", "speech", "tts", "files", "nbu", "search", "quicksearch", "googleapp", "velvet"])


def prepare_install_gms_usb(
    usb_drive: str,
    gms_dir: str,
    include_gboard: bool = True,
    include_chrome: bool = False,
    include_maps: bool = False,
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """Prepares USB to inject Google Services Framework into Dongfeng head unit with optional user apps."""
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(t("logs.prep_usb_header", f"\n── Preparing Install GMS USB: {usb_drive} ──", title=t("nav.install_gms_title", "Install GMS"), drive=usb_drive))
    if not os.path.exists(usb_drive):
        _log(t("logs.usb_not_found", f"  ✗ USB Drive not found: {usb_drive}", drive=usb_drive))
        return False
    if not os.path.exists(gms_dir):
        _log(t("logs.gms_dir_not_found", f"  ✗ Google Services folder not found: {gms_dir}", path=gms_dir))
        return False

    if cancel_check and cancel_check():
        _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
        return False

    try:
        clean_ops = count_usb_clean_ops(usb_drive)
        clean_work_units = (clean_ops / 350.0) * 15.0 if clean_ops > 0 else 0.0

        all_apks = [f for f in os.listdir(gms_dir) if f.lower().endswith(".apk")]

        # Segregate system apps and optional user apps
        system_apks = sorted([f for f in all_apks if _is_system_priv_app(f)], key=_get_gms_order_prefix)
        user_apks = []
        for f in all_apks:
            f_lower = f.lower()
            if "gboard" in f_lower and include_gboard:
                user_apks.append(f)
            elif "chrome" in f_lower and include_chrome:
                user_apks.append(f)
            elif "maps" in f_lower and include_maps:
                user_apks.append(f)

        total_system_bytes = sum(os.path.getsize(os.path.join(gms_dir, f)) for f in system_apks if os.path.isfile(os.path.join(gms_dir, f)))
        total_user_bytes = sum(os.path.getsize(os.path.join(gms_dir, f)) for f in user_apks if os.path.isfile(os.path.join(gms_dir, f)))
        total_payload_bytes = max(1, total_system_bytes + total_user_bytes)
        payload_mb = total_payload_bytes / (1024 * 1024)

        if clean_work_units <= 0:
            clean_end_pct = 0.02
        else:
            clean_ratio = clean_work_units / (clean_work_units + payload_mb)
            clean_end_pct = max(0.02, min(0.35, clean_ratio * 0.95))

        clean_usb_drive(usb_drive, log_func, progress_func, cancel_check, start_pct=0.0, end_pct=clean_end_pct)
        if cancel_check and cancel_check():
            _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
            return False

        update_dir = os.path.join(usb_drive, "update")
        soft_dir = os.path.join(update_dir, "soft")
        user_apps_dir = os.path.join(update_dir, "user_apps")
        os.makedirs(soft_dir, exist_ok=True)
        if user_apks:
            os.makedirs(user_apps_dir, exist_ok=True)

        total_pkgs = len(system_apks) + len(user_apks)
        _log(t("logs.staging_gms_pkgs", f"  Staging {total_pkgs} component(s) ({payload_mb:.1f} MB total)...", count=total_pkgs, mb=f"{payload_mb:.1f}"))

        copied_cumulative_bytes = 0
        range_start = clean_end_pct
        range_span = 0.92 - range_start
        start_transfer_time = time.time()

        # 1. Stage System Priv-Apps
        for idx, apk_name in enumerate(system_apks, 1):
            if cancel_check and cancel_check():
                _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
                return False

            src_f = os.path.join(gms_dir, apk_name)
            base = os.path.splitext(apk_name)[0]
            clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '', base)
            order_prefix = _get_gms_order_prefix(apk_name)
            folder_name = f"{order_prefix}{clean_name}" if not clean_name.startswith(order_prefix) else clean_name
            dest_dir = os.path.join(soft_dir, folder_name)
            os.makedirs(dest_dir, exist_ok=True)
            dest_f = os.path.join(dest_dir, f"{folder_name}.apk")

            _log(t("logs.gms_component_item", f"  [System {idx}/{len(system_apks)}] Component: {folder_name}", idx=idx, total=len(system_apks), order=str(idx), name=folder_name))

            def _on_chunk(chunk_len, file_copied, file_total):
                nonlocal copied_cumulative_bytes
                copied_cumulative_bytes += chunk_len
                elapsed = max(0.05, time.time() - start_transfer_time)
                speed_mb_s = (copied_cumulative_bytes / (1024 * 1024)) / elapsed
                pct = range_start + range_span * min(1.0, copied_cumulative_bytes / total_payload_bytes)
                c_mb = copied_cumulative_bytes / (1024 * 1024)
                t_mb = total_payload_bytes / (1024 * 1024)
                if progress_func:
                    progress_func(pct, apk_name, speed_mb_s, c_mb, t_mb)

            ok_stream = copy_file_with_chunk_progress(
                src_f,
                dest_f,
                chunk_size=256 * 1024,
                chunk_callback=_on_chunk,
                cancel_check=cancel_check
            )
            if not ok_stream or (cancel_check and cancel_check()):
                _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
                return False

            extract_so_libs(src_f, dest_dir, log_func)

        # 2. Stage User Applications (if selected)
        for idx, apk_name in enumerate(user_apks, 1):
            if cancel_check and cancel_check():
                _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
                return False

            src_f = os.path.join(gms_dir, apk_name)
            dest_f = os.path.join(user_apps_dir, apk_name)
            _log(f"  [User App {idx}/{len(user_apks)}] Staging: {apk_name}")

            def _on_chunk_user(chunk_len, file_copied, file_total):
                nonlocal copied_cumulative_bytes
                copied_cumulative_bytes += chunk_len
                elapsed = max(0.05, time.time() - start_transfer_time)
                speed_mb_s = (copied_cumulative_bytes / (1024 * 1024)) / elapsed
                pct = range_start + range_span * min(1.0, copied_cumulative_bytes / total_payload_bytes)
                c_mb = copied_cumulative_bytes / (1024 * 1024)
                t_mb = total_payload_bytes / (1024 * 1024)
                if progress_func:
                    progress_func(pct, apk_name, speed_mb_s, c_mb, t_mb)

            ok_stream = copy_file_with_chunk_progress(
                src_f,
                dest_f,
                chunk_size=256 * 1024,
                chunk_callback=_on_chunk_user,
                cancel_check=cancel_check
            )
            if not ok_stream or (cancel_check and cancel_check()):
                _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
                return False

        # 3. Stage Gboard Custom Preset Data if present
        gboard_src_dir = os.path.join(gms_dir, "gboard_data")
        if include_gboard and os.path.isdir(gboard_src_dir):
            _log("  Staging custom Gboard profile preset...")
            import shutil
            dest_gb_data = os.path.join(update_dir, "gboard_data")
            if os.path.exists(dest_gb_data):
                shutil.rmtree(dest_gb_data, ignore_errors=True)
            shutil.copytree(gboard_src_dir, dest_gb_data)

        if progress_func:
            progress_func(0.93, "Generating GMS injection script & configurations...", 0.0, total_payload_bytes / (1024 * 1024), total_payload_bytes / (1024 * 1024))

        # Generate custom_rep.sh using modular 2-stage state-machine architecture
        stage1_body = (
            gen_mount_rw()
            + gen_purge_stale_gms(log_var="LOG_FILE")
            + '\nSOFT_DIR="$USB_PATH/update/soft"\n'
            + gen_install_system_apps("SOFT_DIR", "LOG_FILE")
            + gen_gms_compatibility_and_arabic("LOG_FILE")
            + '\nUSER_APPS_DIR="$USB_PATH/update/user_apps"\n'
            + gen_install_user_apps("USER_APPS_DIR", "LOG_FILE")
            + gen_mount_ro()
            + gen_stage_reboot(
                "gms_stage1",
                reboot_delay=3,
                reboot_msg="Rebooting infotainment system to register GMS system framework..."
            )
        )

        stage2_body = (
            '\necho "=== STAGE 2: POST-BOOT GBOARD CONFIGURATION & SETTINGS ===" >> "$LOG_FILE"\n'
            + gen_wait_for_boot_completed(settle_seconds=5, log_var="LOG_FILE")
            + gen_gboard_config("GBOARD_PRESET", "LOG_FILE")
            + gen_direct_settings_xml_patch("LOG_FILE")
            + gen_bash_footer(
                success_status="SUCCESS",
                with_reboot=False,
                log_var="LOG_FILE"
            )
        )

        script = (
            gen_bash_header("GMS & GOOGLE ECOSYSTEM INSTALLER\n# Dual-Stage State Machine Architecture", "gms_install.log")
            + gen_state_init()
            + 'if [ ! -f "$STATE_DIR/gms_stage1.done" ]; then\n'
            + 'echo "=== STAGE 1: INJECTING GMS SYSTEM PACKAGES & USER APPS ===" >> "$LOG_FILE"\n'
            + stage1_body
            + '\nfi\n'
            + stage2_body
        )
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        if progress_func:
            progress_func(0.96, "Writing Google Services manual (HTML)...", 0.0, total_payload_bytes / (1024 * 1024), total_payload_bytes / (1024 * 1024))

        write_payload_manuals(
            usb_drive,
            "Install_GMS_Info",
            "install_gms",
            include_gboard=include_gboard,
            include_chrome=include_chrome,
            include_maps=include_maps
        )

        if progress_func:
            progress_func(0.99, "Flushing filesystem buffers to USB drive...", 0.0, total_payload_bytes / (1024 * 1024), total_payload_bytes / (1024 * 1024))
            time.sleep(0.04)
            progress_func(1.0, "Install GMS USB ready!", 0.0, total_payload_bytes / (1024 * 1024), total_payload_bytes / (1024 * 1024))

        _log(t("logs.prep_usb_success", "✓ Install GMS USB prepared successfully.", title=t("nav.install_gms_title", "Install GMS")))
        return True
    except Exception as e:
        log_exception(e, "prepare_install_gms_usb")
        _log(t("logs.prep_failed", "  ✗ Failed to prepare {title} USB: {err}", title=t("nav.install_gms_title", "Install GMS"), err=str(e)))
        return False
