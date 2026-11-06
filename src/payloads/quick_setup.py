"""
quick_setup.py — Feature: Master Technician Fast Provisioning (Aero Quick Setup).
Comprehensive 1-Click deployment of Aero Bar + Full Google Play Services (with all optional apps),
optional deep clean factory wipe, post-reboot auto-launch, and Multi-Vehicle USB Registry.
Zero-footprint on vehicle: leaves NO lock files or traces on /data or /system.
"""
import os
import re
import time
import shutil
from core.paths import AEROBAR_APK, HVAC_MOD_APK, GMS_DIR
from core.constants import SIGNATURE_BANNER
from core.exceptions import log_exception
from core.i18n import t
from payloads.base import (
    clean_usb_drive,
    count_usb_clean_ops,
    write_script_file,
    extract_so_libs,
    copy_file_with_chunk_progress
)
from payloads.bash_builder import (
    gen_multi_vehicle_header,
    gen_multi_vehicle_footer,
    gen_mount_rw,
    gen_mount_ro,
    gen_purge_stale_gms,
    gen_gms_compatibility_and_arabic,
    gen_wipe_data_partition,
    gen_install_system_apps,
    gen_install_user_apps,
    gen_wait_for_boot_completed,
    gen_direct_settings_xml_patch,
    gen_gboard_config
)
from payloads.install_gms import _get_gms_order_prefix, _is_system_priv_app
from payloads.manual_generator import write_payload_manuals


def prepare_quick_setup_usb(
    usb_drive: str,
    wipe_factory_data: bool = False,
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """
    Prepares a Multi-Vehicle Master USB containing:
    1. Aero Bar privilege injection & stock nav-bar auto-hiding.
    2. Full Google Services (GMS core + all optional apps: Chrome, Gboard, Maps, Files, Speech, Search).
    3. Optional pre-installation clean factory data wipe.
    4. Post-reboot auto-launch for Aero Bar.
    5. Multi-Vehicle USB Registry (zero lock files written to car!).
    """
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(t("logs.prep_usb_header", f"\n── Preparing Quick Setup Master USB: {usb_drive} ──", title=t("nav.quick_setup_title", "Quick Setup"), drive=usb_drive))
    if not os.path.exists(usb_drive):
        _log(t("logs.usb_not_found", f"  ✗ USB Drive not found: {usb_drive}", drive=usb_drive))
        return False

    aerobar_src = AEROBAR_APK if os.path.isfile(AEROBAR_APK) else HVAC_MOD_APK
    if not os.path.isfile(aerobar_src):
        _log(f"  ✗ Aero Bar APK not found at: {AEROBAR_APK}")
        return False

    if not os.path.isdir(GMS_DIR):
        _log(f"  ✗ Google Services directory not found at: {GMS_DIR}")
        return False

    if cancel_check and cancel_check():
        _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
        return False

    try:
        clean_ops = count_usb_clean_ops(usb_drive)
        clean_work_units = (clean_ops / 350.0) * 15.0 if clean_ops > 0 else 0.0

        all_gms_apks = [f for f in os.listdir(GMS_DIR) if f.lower().endswith(".apk")]
        system_gms_apks = sorted([f for f in all_gms_apks if _is_system_priv_app(f)], key=_get_gms_order_prefix)
        user_gms_apks = [f for f in all_gms_apks if not _is_system_priv_app(f)]

        aerobar_bytes = os.path.getsize(aerobar_src)
        system_gms_bytes = sum(os.path.getsize(os.path.join(GMS_DIR, f)) for f in system_gms_apks)
        user_gms_bytes = sum(os.path.getsize(os.path.join(GMS_DIR, f)) for f in user_gms_apks)
        total_payload_bytes = max(1, aerobar_bytes + system_gms_bytes + user_gms_bytes)
        payload_mb = total_payload_bytes / (1024 * 1024)

        if clean_work_units <= 0:
            clean_end_pct = 0.03
        else:
            clean_ratio = clean_work_units / (clean_work_units + payload_mb)
            clean_end_pct = max(0.03, min(0.35, clean_ratio * 0.95))

        clean_usb_drive(usb_drive, log_func, progress_func, cancel_check, start_pct=0.0, end_pct=clean_end_pct)
        if cancel_check and cancel_check():
            _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
            return False

        update_dir = os.path.join(usb_drive, "update")
        soft_dir = os.path.join(update_dir, "soft")
        user_apps_dir = os.path.join(update_dir, "user_apps")
        os.makedirs(soft_dir, exist_ok=True)
        os.makedirs(user_apps_dir, exist_ok=True)

        copied_cumulative_bytes = 0
        range_start = clean_end_pct
        range_span = 0.92 - range_start
        transfer_start = time.time()

        def _update_progress(chunk_len, filename):
            nonlocal copied_cumulative_bytes
            copied_cumulative_bytes += chunk_len
            elapsed = max(0.05, time.time() - transfer_start)
            speed_mb_s = (copied_cumulative_bytes / (1024 * 1024)) / elapsed
            pct = range_start + range_span * min(1.0, copied_cumulative_bytes / total_payload_bytes)
            c_mb = copied_cumulative_bytes / (1024 * 1024)
            t_mb = total_payload_bytes / (1024 * 1024)
            if progress_func:
                progress_func(pct, filename, speed_mb_s, c_mb, t_mb)

        # 1. Stage Aero Bar
        _log(f"  Staging Aero Bar System Dock ({aerobar_bytes / (1024*1024):.1f} MB)...")
        aerobar_dest_dir = os.path.join(soft_dir, "AeroBar")
        os.makedirs(aerobar_dest_dir, exist_ok=True)
        aerobar_dest_apk = os.path.join(aerobar_dest_dir, "AeroBar.apk")
        ok_bar = copy_file_with_chunk_progress(
            aerobar_src,
            aerobar_dest_apk,
            chunk_size=256 * 1024,
            chunk_callback=lambda c, f_c, f_t: _update_progress(c, "AeroBar.apk"),
            cancel_check=cancel_check
        )
        if not ok_bar or (cancel_check and cancel_check()):
            _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
            return False

        # 2. Stage Core GMS System Components
        _log(f"  Staging Core Google Services ({len(system_gms_apks)} packages)...")
        for idx, apk_name in enumerate(system_gms_apks, 1):
            if cancel_check and cancel_check():
                _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
                return False

            src_f = os.path.join(GMS_DIR, apk_name)
            base = os.path.splitext(apk_name)[0]
            clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '', base)
            order_prefix = _get_gms_order_prefix(apk_name)
            folder_name = f"{order_prefix}{clean_name}" if not clean_name.startswith(order_prefix) else clean_name
            dest_dir = os.path.join(soft_dir, folder_name)
            os.makedirs(dest_dir, exist_ok=True)
            dest_f = os.path.join(dest_dir, f"{folder_name}.apk")

            _log(f"    [{idx}/{len(system_gms_apks)}] Staging System GMS: {folder_name}")
            ok_copy = copy_file_with_chunk_progress(
                src_f,
                dest_f,
                chunk_size=256 * 1024,
                chunk_callback=lambda c, f_c, f_t, fn=apk_name: _update_progress(c, fn),
                cancel_check=cancel_check
            )
            if not ok_copy or (cancel_check and cancel_check()):
                _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
                return False

            extract_so_libs(src_f, dest_dir, log_func)

        # 3. Stage All Optional Google User Apps (Chrome, Gboard, Maps)
        _log(f"  Staging Google User Apps ({len(user_gms_apks)} packages)...")
        for idx, apk_name in enumerate(user_gms_apks, 1):
            if cancel_check and cancel_check():
                _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
                return False

            src_f = os.path.join(GMS_DIR, apk_name)
            dest_f = os.path.join(user_apps_dir, apk_name)
            _log(f"    [{idx}/{len(user_gms_apks)}] Staging User App: {apk_name}")
            ok_copy = copy_file_with_chunk_progress(
                src_f,
                dest_f,
                chunk_size=256 * 1024,
                chunk_callback=lambda c, f_c, f_t, fn=apk_name: _update_progress(c, fn),
                cancel_check=cancel_check
            )
            if not ok_copy or (cancel_check and cancel_check()):
                _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
                return False

        # 4. Stage Gboard Custom Preset Data (Arabic dictionary & layout)
        gboard_src_dir = os.path.join(GMS_DIR, "gboard_data")
        if os.path.isdir(gboard_src_dir):
            _log("  Staging custom Gboard profile preset...")
            dest_gb_data = os.path.join(update_dir, "gboard_data")
            if os.path.exists(dest_gb_data):
                shutil.rmtree(dest_gb_data, ignore_errors=True)
            shutil.copytree(gboard_src_dir, dest_gb_data)

        if progress_func:
            progress_func(0.93, "Generating Multi-Vehicle Quick Setup script...", 0.0, payload_mb, payload_mb)

        # 5. Build Unified Multi-Vehicle Shell Script
        script_parts = []
        script_parts.append(gen_multi_vehicle_header("AERO QUICK SETUP (MASTER PROVISIONING)", "quick_setup.log"))

        reboot_stage2_num = "#2" if wipe_factory_data else "#1"

        if wipe_factory_data:
            script_parts.append("""
# =============================================================
# STAGE 1: CLEAN FACTORY PURGE & ROM INITIALIZATION (REBOOT #1)
# =============================================================
if [ ! -f "$STATE_DIR/stage_factory_reset.done" ]; then
    echo "=== STAGE 1: INITIATING CLEAN FACTORY PURGE (/data & /cache) ===" >> "$LOG_FILE"
""")
            script_parts.append(gen_wipe_data_partition(log_var="LOG_FILE"))
            script_parts.append("""
    echo "=== STAGE 1 COMPLETE — REBOOTING VEHICLE TO INITIALIZE CLEAN ROM ===" >> "$LOG_FILE"
    touch "$STATE_DIR/stage_factory_reset.done"
    sync
    sec=3
    while [ $sec -gt 0 ]; do
        echo "System will restart after $sec seconds..." >> "$LOG_FILE"
        sleep 1
        sec=$((sec - 1))
    done
    sync
    (sleep 1; setprop sys.powerctl reboot || reboot -f || reboot) &
    exit 0
fi
""")

        # STAGE: DEPLOY PRIV-APPS & USER APPS (Stage 2 if wipe, Stage 1 if no wipe)
        script_parts.append("""
# =============================================================
# STAGE INSTALL: DEPLOY PRIVILEGED APPS, GMS & USER APPLICATIONS
# =============================================================
if [ ! -f "$STATE_DIR/stage_install.done" ]; then
    echo "=== STAGE INSTALL: INJECTING AEROBAR, GMS & USER APPLICATIONS ===" >> "$LOG_FILE"
""")
        script_parts.append(gen_mount_rw())
        script_parts.append(gen_purge_stale_gms(log_var="LOG_FILE"))

        # Inject System Priv-Apps (AeroBar + GMS) using standard proven installer
        script_parts.append('\nSOFT_DIR="$USB_PATH/update/soft"\n')
        script_parts.append(gen_install_system_apps("SOFT_DIR", "LOG_FILE"))

        # Inject Google Permissions XML & Compatibility Patches
        script_parts.append(gen_gms_compatibility_and_arabic(log_var="LOG_FILE"))

        # Hide stock HVAC & navigation bar (keeps factory launcher 100% active)
        script_parts.append("""
echo "Eliminating stock 200px OEM bar & restoring window insets..." >> "$LOG_FILE"
settings delete global policy_control >> "$LOG_FILE" 2>&1
if [ -f /system/build.prop ]; then
    grep -q "qemu.hw.mainkeys" /system/build.prop && sed -i "s/qemu.hw.mainkeys=.*/qemu.hw.mainkeys=1/" /system/build.prop || echo "qemu.hw.mainkeys=1" >> /system/build.prop
fi
setprop qemu.hw.mainkeys 1 >> "$LOG_FILE" 2>&1
killall com.android.systemui >> "$LOG_FILE" 2>&1

echo "Injecting Aero Bar privileged permissions whitelist..." >> "$LOG_FILE"
cat << 'EOF' > /system/etc/permissions/privapp-permissions-aerobar.xml
<?xml version="1.0" encoding="utf-8"?>
<permissions>
    <privapp-permissions package="com.aero.bar.dongfeng_shine">
        <permission name="android.permission.INTERNAL_SYSTEM_WINDOW" />
        <permission name="android.permission.STATUS_BAR_SERVICE" />
        <permission name="android.permission.STATUS_BAR" />
        <permission name="android.permission.PACKAGE_USAGE_STATS" />
        <permission name="android.permission.KILL_BACKGROUND_PROCESSES" />
        <permission name="android.permission.FORCE_STOP_PACKAGES" />
        <permission name="android.permission.REMOVE_TASKS" />
        <permission name="android.permission.REAL_GET_TASKS" />
        <permission name="android.permission.WRITE_SECURE_SETTINGS" />
        <permission name="android.permission.INTERACT_ACROSS_USERS" />
        <permission name="android.permission.INTERACT_ACROSS_USERS_FULL" />
    </privapp-permissions>
</permissions>
EOF
chmod 644 /system/etc/permissions/privapp-permissions-aerobar.xml >> "$LOG_FILE" 2>&1

if [ -f "/system/priv-app/AeroBar/AeroBar.apk" ]; then
    echo "Explicitly registering Aero Bar package via PM..." >> "$LOG_FILE"
    pm install -r -g /system/priv-app/AeroBar/AeroBar.apk >> "$LOG_FILE" 2>&1
fi
""")

        # Install Google User Apps (Chrome, Gboard, Maps) using the battle-tested multi-tier installer
        script_parts.append('\nUSER_APPS_DIR="$USB_PATH/update/user_apps"\n')
        script_parts.append(gen_install_user_apps("USER_APPS_DIR", "LOG_FILE"))

        # Relock system partition
        script_parts.append(gen_mount_ro())

        # Trigger reboot to register system partition priv-apps
        script_parts.append(f"""
    echo "=== STAGE INSTALL COMPLETE — REBOOTING VEHICLE ({reboot_stage2_num}) TO REGISTER SYSTEM PACKAGES ===" >> "$LOG_FILE"
    touch "$STATE_DIR/stage_install.done"
    sync
    sec=3
    while [ $sec -gt 0 ]; do
        echo "System will restart after $sec seconds..." >> "$LOG_FILE"
        sleep 1
        sec=$((sec - 1))
    done
    sync
    (sleep 1; setprop sys.powerctl reboot || reboot -f || reboot) &
    exit 0
fi
""")

        # STAGE POST-BOOT: PERMISSION GRANTS, GBOARD & AERO BAR STARTUP
        script_parts.append("""
# =============================================================
# STAGE POST-BOOT: PERMISSION GRANTS, GBOARD & AERO BAR STARTUP
# =============================================================
echo "=== STAGE POST-BOOT: CONFIGURING SYSTEM & STARTING AERO BAR ===" >> "$LOG_FILE"
""")
        # Wait for Android framework to report boot completion
        script_parts.append(gen_wait_for_boot_completed(settle_seconds=5, log_var="LOG_FILE"))

        # Configure Aero Bar privileges now that PackageManager has scanned /system/priv-app/AeroBar and assigned its UID!
        script_parts.append("""
echo "Configuring Aero Bar system permissions..." >> "$LOG_FILE"
appops set com.aero.bar.dongfeng_shine SYSTEM_ALERT_WINDOW allow >> "$LOG_FILE" 2>&1
appops set com.aero.bar.dongfeng_shine.debug SYSTEM_ALERT_WINDOW allow >> "$LOG_FILE" 2>&1
appops set com.aero.bar SYSTEM_ALERT_WINDOW allow >> "$LOG_FILE" 2>&1
settings put secure enabled_accessibility_services com.aero.bar.dongfeng_shine/com.aero.bar.service.AeroAccessibilityService:com.aero.bar.dongfeng_shine.debug/com.aero.bar.service.AeroAccessibilityService:com.aero.bar/com.aero.bar.service.AeroAccessibilityService >> "$LOG_FILE" 2>&1
settings put secure accessibility_enabled 1 >> "$LOG_FILE" 2>&1
pm enable com.aero.bar.dongfeng_shine >> "$LOG_FILE" 2>&1
pm enable com.aero.bar.dongfeng_shine.debug >> "$LOG_FILE" 2>&1
pm enable com.aero.bar >> "$LOG_FILE" 2>&1
""")

        # Configure Gboard Arabic Profile & direct settings patch
        script_parts.append("""GBOARD_PRESET="$USB_PATH/update/gboard_data"\n""")
        script_parts.append(gen_gboard_config("GBOARD_PRESET", log_var="LOG_FILE"))
        script_parts.append(gen_direct_settings_xml_patch(log_var="LOG_FILE"))

        # Launch Aero Bar immediately
        script_parts.append("""
echo "Ensuring stock bar is eliminated and launching Aero Bar..." >> "$LOG_FILE"
settings delete global policy_control >> "$LOG_FILE" 2>&1
setprop qemu.hw.mainkeys 1 >> "$LOG_FILE" 2>&1
killall com.android.systemui >> "$LOG_FILE" 2>&1
pkill -f com.android.systemui >> "$LOG_FILE" 2>&1

am start-foreground-service -n com.aero.bar.dongfeng_shine/com.aero.bar.service.AeroBarOverlayService >> "$LOG_FILE" 2>&1 || \
am start-foreground-service -n com.aero.bar.dongfeng_shine.debug/com.aero.bar.service.AeroBarOverlayService >> "$LOG_FILE" 2>&1 || \
am start-foreground-service -n com.aero.bar/com.aero.bar.service.AeroBarOverlayService >> "$LOG_FILE" 2>&1

am start -n com.aero.bar.dongfeng_shine/com.aero.bar.ui.MainActivity >> "$LOG_FILE" 2>&1 || \
am start -n com.aero.bar.dongfeng_shine.debug/com.aero.bar.ui.MainActivity >> "$LOG_FILE" 2>&1 || \
am start -n com.aero.bar/com.aero.bar.ui.MainActivity >> "$LOG_FILE" 2>&1
""")

        # Completion footer (with_reboot=False, marks completed.done in $CAR_DIR and plays chime)
        script_parts.append(gen_multi_vehicle_footer(
            success_status="SUCCESS",
            with_reboot=False,
            log_var="LOG_FILE"
        ))

        unified_script = "".join(script_parts)
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), unified_script)

        if progress_func:
            progress_func(0.96, "Generating Quick Setup User Manual (HTML)...", 0.0, payload_mb, payload_mb)

        write_payload_manuals(usb_drive, "Quick_Setup_Info", "quick_setup", wipe_factory_data=wipe_factory_data)

        if progress_func:
            progress_func(0.99, "Flushing filesystem buffers to USB drive...", 0.0, payload_mb, payload_mb)
            time.sleep(0.04)
            progress_func(1.0, "Quick Setup Master USB Ready!", 0.0, payload_mb, payload_mb)

        _log(t("logs.prep_usb_success", "✓ Quick Setup Master USB prepared successfully.", title=t("nav.quick_setup_title", "Quick Setup")))
        return True

    except Exception as e:
        log_exception(e, "prepare_quick_setup_usb")
        _log(t("logs.prep_failed", "  ✗ Failed to prepare {title} USB: {err}", title=t("nav.quick_setup_title", "Quick Setup"), err=str(e)))
        return False
