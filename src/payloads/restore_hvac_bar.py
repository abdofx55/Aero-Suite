"""
restore_hvac_bar.py — Feature: Restore Factory OEM HVAC Climate Control Bar.
Reverts customized SystemUI back to the untouched factory original SystemUI.
"""
import os
import time
from core.paths import HVAC_STOCK_APK, FACTORY_BACKUP_DIR
from core.exceptions import log_exception
from core.i18n import t
from payloads.base import clean_usb_drive, count_usb_clean_ops, write_script_file, copy_file_with_chunk_progress
from payloads.bash_builder import (
    gen_bash_header,
    gen_mount_rw,
    gen_replace_systemui,
    gen_mount_ro,
    gen_bash_footer
)
from payloads.manual_generator import write_payload_manuals


def prepare_restore_hvac_bar_usb(
    usb_drive: str,
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """Prepares USB drive to revert back to the factory stock OEM HVAC Climate Navigation Bar."""
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(t("logs.prep_usb_header", f"\n── Preparing Restore Factory HVAC Bar USB: {usb_drive} ──", title=t("nav.restore_hvac_bar_title", "Restore Stock HVAC Bar"), drive=usb_drive))
    if not os.path.exists(usb_drive):
        _log(t("logs.usb_not_found", f"  ✗ USB Drive not found: {usb_drive}", drive=usb_drive))
        return False

    stock_source = HVAC_STOCK_APK
    if not os.path.isfile(stock_source):
        fallback_stock = os.path.join(FACTORY_BACKUP_DIR, "priv-app", "SystemUI-release-signed", "SystemUI-release-signed.apk")
        if os.path.isfile(fallback_stock):
            stock_source = fallback_stock
        else:
            _log(f"  ✗ Original factory SystemUI APK not found at: {HVAC_STOCK_APK}")
            return False

    if cancel_check and cancel_check():
        _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
        return False

    try:
        clean_ops = count_usb_clean_ops(usb_drive)
        clean_work_units = (clean_ops / 350.0) * 15.0 if clean_ops > 0 else 0.0
        apk_bytes = os.path.getsize(stock_source)
        apk_mb = apk_bytes / (1024 * 1024)

        if clean_work_units <= 0:
            clean_end_pct = 0.05
        else:
            clean_ratio = clean_work_units / (clean_work_units + apk_mb)
            clean_end_pct = max(0.05, min(0.35, clean_ratio * 0.95))

        clean_usb_drive(usb_drive, log_func, progress_func, cancel_check, start_pct=0.0, end_pct=clean_end_pct)
        if cancel_check and cancel_check():
            _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
            return False

        update_dir = os.path.join(usb_drive, "update")
        soft_dir = os.path.join(update_dir, "soft", "SystemUI-release-signed")
        os.makedirs(soft_dir, exist_ok=True)
        dest_apk = os.path.join(soft_dir, "SystemUI-release-signed.apk")

        _log(f"  Staging Factory Stock SystemUI APK ({apk_mb:.1f} MB)...")

        range_start = clean_end_pct
        range_span = 0.90 - range_start
        copied_bytes = 0
        transfer_start = time.time()

        def _on_chunk(chunk_len, file_copied, file_total):
            nonlocal copied_bytes
            copied_bytes += chunk_len
            elapsed = max(0.05, time.time() - transfer_start)
            speed_mb_s = (copied_bytes / (1024 * 1024)) / elapsed
            pct = range_start + range_span * min(1.0, copied_bytes / max(1, apk_bytes))
            c_mb = copied_bytes / (1024 * 1024)
            t_mb = apk_bytes / (1024 * 1024)
            if progress_func:
                progress_func(pct, "SystemUI_stock_200px.apk", speed_mb_s, c_mb, t_mb)

        ok_copy = copy_file_with_chunk_progress(
            stock_source,
            dest_apk,
            chunk_size=256 * 1024,
            chunk_callback=_on_chunk,
            cancel_check=cancel_check
        )
        if not ok_copy or (cancel_check and cancel_check()):
            _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
            return False

        if progress_func:
            progress_func(0.92, "Generating SystemUI restoration script...", 0.0, apk_mb, apk_mb)

        script = (
            gen_bash_header("FACTORY OEM HVAC CLIMATE BAR & SYSTEM RESTORATION", "hvac_bar_restore.log")
            + gen_mount_rw()
            + '\n# 1. Restore Stock SystemUI\n'
            + 'HVAC_STAGE_APK="$USB_PATH/update/soft/SystemUI-release-signed/SystemUI-release-signed.apk"\n'
            + gen_replace_systemui("HVAC_STAGE_APK", "LOG_FILE")
            + '\n# 2. Remove Aero Bar System Package\n'
            + 'echo "Cleaning up Aero Bar from /system/priv-app/AeroBar..." >> "$LOG_FILE"\n'
            + 'rm -rf /system/priv-app/AeroBar >> "$LOG_FILE" 2>&1\n'
            + 'pm uninstall com.aero.bar.dongfeng_shine >> "$LOG_FILE" 2>&1\n'
            + 'pm uninstall com.aero.bar.dongfeng_shine.debug >> "$LOG_FILE" 2>&1\n'
            + 'pm uninstall com.aero.bar >> "$LOG_FILE" 2>&1\n'
            + '\n# 3. Restore Stock Navigation & HVAC Bar Settings\n'
            + 'echo "Restoring stock navigation & HVAC bar display..." >> "$LOG_FILE"\n'
            + 'settings delete global policy_control >> "$LOG_FILE" 2>&1\n'
            + 'if [ -f /system/build.prop ]; then\n'
            + '    sed -i "s/qemu.hw.mainkeys=1/qemu.hw.mainkeys=0/" /system/build.prop\n'
            + 'fi\n'
            + 'setprop qemu.hw.mainkeys 0 >> "$LOG_FILE" 2>&1\n'
            + gen_mount_ro()
            + gen_bash_footer(
                success_status="SUCCESS",
                with_reboot=True,
                reboot_delay=3,
                reboot_msg="Rebooting infotainment system to restore factory interface..."
            )
        )
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        if progress_func:
            progress_func(0.96, "Writing HVAC Bar Restoration Manual (HTML)...", 0.0, apk_mb, apk_mb)

        write_payload_manuals(usb_drive, "Restore_HVAC_Bar_Info", "restore_hvac_bar")

        if progress_func:
            progress_func(0.99, "Flushing filesystem buffers to USB drive...", 0.0, apk_mb, apk_mb)
            time.sleep(0.04)
            progress_func(1.0, "Restore HVAC Bar USB Ready!", 0.0, apk_mb, apk_mb)

        _log(t("logs.prep_usb_success", "✓ Restore Factory HVAC Bar USB prepared successfully.", title=t("nav.restore_hvac_bar_title", "Restore Stock HVAC Bar")))
        return True

    except Exception as e:
        log_exception(e, "prepare_restore_hvac_bar_usb")
        _log(t("logs.prep_failed", "  ✗ Failed to prepare {title} USB: {err}", title=t("nav.restore_hvac_bar_title", "Restore Stock HVAC Bar"), err=str(e)))
        return False
