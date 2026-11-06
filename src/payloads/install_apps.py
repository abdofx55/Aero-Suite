"""
install_apps.py — Feature 1: Automated Application Installation Payload Generator.
Supports User Apps (/data/app), System Apps (/system/priv-app), AXML patching, and Auto-Launch.
"""
import os
import re
import time
import tempfile
from core.constants import SIGNATURE_BANNER
from core.exceptions import log_exception
from core.i18n import t
from payloads.base import (
    clean_usb_drive,
    count_usb_clean_ops,
    write_script_file,
    extract_so_libs,
    copy_file_with_chunk_progress,
    patch_apk,
    generate_user_apps_install_script
)
from payloads.bash_builder import (
    gen_bash_header,
    gen_mount_rw,
    gen_mount_ro,
    gen_install_system_apps,
    gen_install_user_apps,
    gen_launch_app,
    gen_bash_footer
)
from payloads.manual_generator import generate_info_content, write_payload_manuals


def prepare_install_apps_usb(
    usb_drive: str,
    selected_apks: list,
    options: dict = None,
    log_func=None,
    progress_func=None,
    cancel_check=None,
    auto_launch_package: str = ""
) -> bool:
    """
    Copies selected APKs to USB with per-app options:
    - install_target: 'user' (User App) or 'system' (System App)
    - force_portrait: bool (Overrides orientation in AXML)
    - block_boot: bool (Neutralizes boot receivers in AXML)
    - auto_launch_package: str (Package name to launch immediately after install)
    """
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(t("logs.prep_usb_header", f"\n── Preparing Install Apps USB: {usb_drive} ──", title=t("nav.install_apps_title", "Install Apps"), drive=usb_drive))
    if not os.path.exists(usb_drive):
        _log(t("logs.usb_not_found", f"  ✗ USB Drive not found: {usb_drive}", drive=usb_drive))
        return False

    if cancel_check and cancel_check():
        _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
        return False

    try:
        # Pre-scan USB and APK workload to calculate dynamic time-weighted allocation:
        # 1. USB Cleaning: An empty USB takes ~0.2s (allocate ~2%).
        #    A USB with an old full Backup (thousands of files) takes 15-30s.
        #    We count items in ~20ms and allocate dynamic progress weight accordingly.
        clean_ops = count_usb_clean_ops(usb_drive)
        # ~350 file deletions on FAT32/exFAT takes ~1s, roughly equal to ~15 MB of transfer workload
        clean_work_units = (clean_ops / 350.0) * 15.0 if clean_ops > 0 else 0.0

        total_apks = len(selected_apks)
        total_bytes = sum(
            os.path.getsize(a["path"]) for a in selected_apks
            if os.path.isfile(a.get("path", ""))
        )
        if total_bytes <= 0:
            total_bytes = 1

        # 2. APK Workload: Patching (repack, sign v1/v2, zipalign) is CPU-bound
        #    and empirically takes ~4x more time per MB than direct USB file copy.
        apk_weights = []
        for a in selected_apks:
            p = a.get("path", "")
            sz = os.path.getsize(p) if os.path.isfile(p) else (1024 * 1024)
            force_p = a.get("force_portrait", False)
            block_b = a.get("block_boot", True)
            target_o = "portrait" if force_p else "default"
            needs_p = (target_o == "portrait" or block_b)
            w = (sz / (1024 * 1024)) * (4.0 if needs_p else 1.0)
            apk_weights.append(max(0.1, w))

        total_apk_weight = sum(apk_weights) if sum(apk_weights) > 0 else 1.0
        total_weight = total_apk_weight

        # Calculate adaptive clean_end_pct so progress moves at an identical speed
        # whether cleaning 0 files or 10,000 files from a previous backup!
        if clean_work_units <= 0:
            clean_end_pct = 0.02
        else:
            clean_ratio = clean_work_units / (clean_work_units + total_apk_weight)
            clean_end_pct = max(0.02, min(0.40, clean_ratio * 0.95))

        clean_usb_drive(usb_drive, log_func, progress_func, cancel_check, start_pct=0.0, end_pct=clean_end_pct)
        if cancel_check and cancel_check():
            _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
            return False

        update_dir = os.path.join(usb_drive, "update")
        soft_dir = os.path.join(update_dir, "soft")           # System apps
        user_soft_dir = os.path.join(update_dir, "user_soft") # User apps
        os.makedirs(soft_dir, exist_ok=True)
        os.makedirs(user_soft_dir, exist_ok=True)

        _log(t("logs.staging_apks", f"  Staging {total_apks} selected APK(s) ({total_bytes / (1024 * 1024):.1f} MB total) with custom parameters...", count=total_apks, mb=f"{total_bytes / (1024 * 1024):.1f}"))

        range_start = clean_end_pct
        range_span = 0.95 - range_start

        system_app_count = 0
        user_app_count = 0
        copied_cumulative_bytes = 0
        bytes_processed_so_far = 0
        accumulated_weight = 0.0
        start_transfer_time = time.time()

        for idx, apk_info in enumerate(selected_apks, 1):
            if cancel_check and cancel_check():
                _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
                return False

            src_apk = apk_info["path"]
            fname = os.path.basename(src_apk)
            base = os.path.splitext(fname)[0]
            clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '', base)
            apk_size = os.path.getsize(src_apk) if os.path.isfile(src_apk) else (1024 * 1024)

            this_weight = apk_weights[idx - 1]
            apk_global_start = range_start + (accumulated_weight / total_weight) * range_span
            apk_global_span = (this_weight / total_weight) * range_span

            target_type = apk_info.get("install_target", "user")
            force_portrait = apk_info.get("force_portrait", False)
            block_boot = apk_info.get("block_boot", True)

            _log(t("logs.processing_app_item", f"  [{idx}/{total_apks}] Processing {fname} (Target: {target_type.upper()})", idx=idx, total=total_apks, fname=fname, target=target_type.upper()))

            target_ori = "portrait" if force_portrait else "default"
            needs_patch = (target_ori == "portrait" or block_boot)

            if target_type == "system":
                system_app_count += 1
                app_dest_dir = os.path.join(soft_dir, clean_name)
                os.makedirs(app_dest_dir, exist_ok=True)
                dest_apk = os.path.join(app_dest_dir, f"{clean_name}.apk")
                if progress_func:
                    progress_func(apk_global_start, f"Extracting native libraries for {fname}...", 0.0, 0, 0)
                extract_so_libs(src_apk, app_dest_dir, log_func)
            else:
                user_app_count += 1
                dest_apk = os.path.join(user_soft_dir, f"{clean_name}.apk")

            temp_patched_apk = None
            source_to_stream = src_apk

            if needs_patch:
                temp_patched_apk = os.path.join(tempfile.gettempdir(), f"aero_{clean_name}_{int(time.time()*1000)}.apk")

                def _on_patch_progress(frac: float, stage: str):
                    current_pct = apk_global_start + (apk_global_span * 0.75 * frac)
                    if stage == "repack":
                        stage_msg = f"Configuring & repacking: {fname}..."
                    elif stage == "sign":
                        stage_msg = f"Signing package: {fname}..."
                    elif stage == "align":
                        stage_msg = f"Page-aligning package: {fname}..."
                    else:
                        stage_msg = f"Configuring & repacking: {fname}..."
                    if progress_func:
                        progress_func(current_pct, stage_msg)

                patch_success = patch_apk(
                    src_apk,
                    temp_patched_apk,
                    log_func=log_func,
                    target_orientation=target_ori,
                    disable_boot_launch=block_boot,
                    progress_callback=_on_patch_progress
                )
                if patch_success and os.path.isfile(temp_patched_apk):
                    source_to_stream = temp_patched_apk
                else:
                    source_to_stream = src_apk

            def _on_chunk(chunk_len, file_copied, file_total):
                nonlocal copied_cumulative_bytes
                copied_cumulative_bytes += chunk_len
                elapsed = max(0.05, time.time() - start_transfer_time)
                speed_mb_s = (copied_cumulative_bytes / (1024 * 1024)) / elapsed
                file_ratio = min(1.0, file_copied / max(1, file_total))
                if needs_patch:
                    current_pct = apk_global_start + (apk_global_span * 0.75) + (apk_global_span * 0.25 * file_ratio)
                else:
                    current_pct = apk_global_start + (apk_global_span * file_ratio)
                c_mb = copied_cumulative_bytes / (1024 * 1024)
                t_mb = total_bytes / (1024 * 1024)
                if progress_func:
                    progress_func(current_pct, fname, speed_mb_s, c_mb, t_mb)

            ok_stream = copy_file_with_chunk_progress(
                source_to_stream,
                dest_apk,
                chunk_size=256 * 1024,
                chunk_callback=_on_chunk,
                cancel_check=cancel_check
            )

            accumulated_weight += this_weight
            bytes_processed_so_far += apk_size

            if temp_patched_apk and os.path.exists(temp_patched_apk):
                try:
                    os.remove(temp_patched_apk)
                except Exception:
                    pass

            if not ok_stream or (cancel_check and cancel_check()):
                _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
                return False

        auto_pkg_clean = auto_launch_package.strip() if auto_launch_package else ""

        # Generate custom_rep.sh for both System Apps and User Apps using bash_builder
        script = (
            gen_bash_header("APP INSTALL", "install_log.txt")
            + gen_mount_rw()
            + """
SOFT_DIR="$USB_PATH/update/soft"
USER_SOFT_DIR="$USB_PATH/update/user_soft"
"""
            + gen_install_system_apps("SOFT_DIR", "LOG_FILE")
            + gen_install_user_apps("USER_SOFT_DIR", "LOG_FILE")
            + 'sync\necho "=== INSTALLATION COMPLETED ===" >> "$LOG_FILE"\n'
        )

        if auto_pkg_clean:
            script += f'\necho "Auto-launching primary application: {auto_pkg_clean}..." >> "$LOG_FILE"\n'
            script += gen_launch_app(auto_pkg_clean, log_var="LOG_FILE")

        if system_app_count > 0:
            script += (
                gen_mount_ro()
                + gen_bash_footer(
                    success_status="SUCCESS",
                    with_reboot=True,
                    reboot_delay=3,
                    reboot_msg="System app(s) installed. Rebooting infotainment system to register system components..."
                )
            )
        else:
            script += gen_bash_footer(success_status="SUCCESS", with_reboot=False)

        if progress_func:
            progress_func(0.96, "Generating automated installer script (custom_rep.sh)...", 0.0, total_bytes / (1024*1024), total_bytes / (1024*1024))

        os.makedirs(update_dir, exist_ok=True)
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        if progress_func:
            progress_func(0.98, "Writing vehicle manual & manifest flags...", 0.0, total_bytes / (1024*1024), total_bytes / (1024*1024))

        write_payload_manuals(
            usb_drive,
            "Install_Apps_Info",
            "install_apps",
            selected_apks=selected_apks,
            system_app_count=system_app_count,
            user_app_count=user_app_count,
            auto_launch_package=auto_launch_package,
            total_apks=total_apks
        )

        if progress_func:
            progress_func(0.99, "Flushing filesystem buffers to USB drive...", 0.0, total_bytes / (1024*1024), total_bytes / (1024*1024))
            time.sleep(0.04)
            progress_func(1.0, "Install Apps USB ready!", 0.0, total_bytes / (1024 * 1024), total_bytes / (1024 * 1024))

        _log(t("logs.prep_install_summary", f"✓ Install Apps USB prepared successfully ({user_app_count} User Apps, {system_app_count} System Apps).", user_count=user_app_count, sys_count=system_app_count))
        return True
    except Exception as e:
        log_exception(e, "prepare_install_apps_usb")
        _log(t("logs.prep_failed", "  ✗ Failed to prepare {title} USB: {err}", title=t("nav.install_apps_title", "Install Apps"), err=str(e)))
        return False
