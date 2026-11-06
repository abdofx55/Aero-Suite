"""
install_hvac_bar.py — Feature: Aero Bar & System Navigation Deployment.
Deploys Aero Bar as a persistent privileged system application (/system/priv-app/AeroBar/),
pre-grants permissions (Overlay, Accessibility), hides the stock HVAC navigation bar,
and reboots the system to activate the modern navigation dock automatically.
"""
import os
import time
from core.paths import AEROBAR_APK, HVAC_MOD_APK
from core.exceptions import log_exception
from core.i18n import t
from payloads.base import clean_usb_drive, count_usb_clean_ops, write_script_file, copy_file_with_chunk_progress
from payloads.bash_builder import (
    gen_bash_header,
    gen_mount_rw,
    gen_mount_ro,
    gen_bash_footer,
    gen_install_system_apps
)
from payloads.manual_generator import write_payload_manuals


def prepare_install_hvac_bar_usb(
    usb_drive: str,
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """Prepares USB drive to deploy the enhanced Aero Bar to the vehicle."""
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(t("logs.prep_usb_header", f"\n── Preparing Install Aero Bar USB: {usb_drive} ──", title=t("nav.install_hvac_bar_title", "Install Aero Bar"), drive=usb_drive))
    if not os.path.exists(usb_drive):
        _log(t("logs.usb_not_found", f"  ✗ USB Drive not found: {usb_drive}", drive=usb_drive))
        return False

    apk_source = AEROBAR_APK if os.path.isfile(AEROBAR_APK) else HVAC_MOD_APK
    if not os.path.isfile(apk_source):
        _log(f"  ✗ Aero Bar APK not found at: {AEROBAR_APK}")
        return False

    if cancel_check and cancel_check():
        _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
        return False

    try:
        clean_ops = count_usb_clean_ops(usb_drive)
        clean_work_units = (clean_ops / 350.0) * 15.0 if clean_ops > 0 else 0.0
        apk_bytes = os.path.getsize(apk_source)
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
        soft_dir = os.path.join(update_dir, "soft", "AeroBar")
        os.makedirs(soft_dir, exist_ok=True)
        dest_apk = os.path.join(soft_dir, "AeroBar.apk")

        _log(f"  Staging Aero Bar System APK ({apk_mb:.1f} MB)...")

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
                progress_func(pct, "AeroBar.apk", speed_mb_s, c_mb, t_mb)

        ok_copy = copy_file_with_chunk_progress(
            apk_source,
            dest_apk,
            chunk_size=256 * 1024,
            chunk_callback=_on_chunk,
            cancel_check=cancel_check
        )
        if not ok_copy or (cancel_check and cancel_check()):
            _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
            return False

        if progress_func:
            progress_func(0.92, "Generating Aero Bar deployment script...", 0.0, apk_mb, apk_mb)

        script = (
            gen_bash_header("AERO BAR & NAVIGATION DEPLOYMENT", "aerobar_install.log")
            + gen_mount_rw()
            + '\n# 1. Deploy Aero Bar as System Privileged Application\n'
            + 'SOFT_DIR="$USB_PATH/update/soft"\n'
            + gen_install_system_apps("SOFT_DIR", "LOG_FILE")
            + '\n# Pre-grant Overlay & Accessibility permissions\n'
            + 'echo "Pre-granting SYSTEM_ALERT_WINDOW..." >> "$LOG_FILE"\n'
            + 'appops set com.aero.bar.dongfeng_shine SYSTEM_ALERT_WINDOW allow >> "$LOG_FILE" 2>&1\n'
            + 'appops set com.aero.bar.dongfeng_shine.debug SYSTEM_ALERT_WINDOW allow >> "$LOG_FILE" 2>&1\n'
            + 'appops set com.aero.bar SYSTEM_ALERT_WINDOW allow >> "$LOG_FILE" 2>&1\n'
            + 'echo "Enabling AeroAccessibilityService..." >> "$LOG_FILE"\n'
            + 'settings put secure enabled_accessibility_services com.aero.bar.dongfeng_shine/com.aero.bar.service.AeroAccessibilityService:com.aero.bar.dongfeng_shine.debug/com.aero.bar.service.AeroAccessibilityService >> "$LOG_FILE" 2>&1\n'
            + 'settings put secure accessibility_enabled 1 >> "$LOG_FILE" 2>&1\n'
            + '\n# 2. Hide / Disable Stock Navigation & HVAC Bar\n'
            + 'echo "Eliminating stock 200px OEM bar & restoring window insets..." >> "$LOG_FILE"\n'
            + 'settings delete global policy_control >> "$LOG_FILE" 2>&1\n'
            + 'if [ -f /system/build.prop ]; then\n'
            + '    grep -q "qemu.hw.mainkeys" /system/build.prop && sed -i "s/qemu.hw.mainkeys=.*/qemu.hw.mainkeys=1/" /system/build.prop || echo "qemu.hw.mainkeys=1" >> /system/build.prop\n'
            + 'fi\n'
            + 'setprop qemu.hw.mainkeys 1 >> "$LOG_FILE" 2>&1\n'
            + 'killall com.android.systemui >> "$LOG_FILE" 2>&1\n'
            + gen_mount_ro()
            + gen_bash_footer(
                success_status="SUCCESS",
                with_reboot=True,
                reboot_delay=3,
                reboot_msg="Rebooting infotainment system to activate Aero Bar..."
            )
        )
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        if progress_func:
            progress_func(0.96, "Writing Aero Bar User Manual (HTML)...", 0.0, apk_mb, apk_mb)

        write_payload_manuals(usb_drive, "Install_HVAC_Bar_Info", "install_hvac_bar")

        if progress_func:
            progress_func(0.99, "Flushing filesystem buffers to USB drive...", 0.0, apk_mb, apk_mb)
            time.sleep(0.04)
            progress_func(1.0, "Install Aero Bar USB Ready!", 0.0, apk_mb, apk_mb)

        _log(t("logs.prep_usb_success", "✓ Install Aero Bar USB prepared successfully.", title=t("nav.install_hvac_bar_title", "Install Aero Bar")))
        return True

    except Exception as e:
        log_exception(e, "prepare_install_hvac_bar_usb")
        _log(t("logs.prep_failed", "  ✗ Failed to prepare {title} USB: {err}", title=t("nav.install_hvac_bar_title", "Install Aero Bar"), err=str(e)))
        return False
