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

        if wipe_factory_data:
            script_parts.append("""
STATE_DIR="$USB_PATH/completed_cars/${CAR_SERIAL}"
mkdir -p "$STATE_DIR" >> "$LOG_FILE" 2>&1

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

echo "=== STAGE 2: INJECTING AEROBAR & GOOGLE SERVICES AFTER CLEAN ROM INIT ===" >> "$LOG_FILE"
""")

        script_parts.append(gen_mount_rw())
        script_parts.append(gen_purge_stale_gms(log_var="LOG_FILE"))

        # Inject System Priv-Apps (AeroBar + GMS)
        script_parts.append("""
# ==========================================
# INJECT SYSTEM PRIVILEGED APPLICATIONS
# ==========================================
SOFT_DIR="$USB_PATH/update/soft"
if [ -d "$SOFT_DIR" ]; then
    echo "Injecting Privileged System Applications..." >> "$LOG_FILE"
    for dir in "$SOFT_DIR"/*; do
        if [ -d "$dir" ]; then
            appname=$(basename "$dir")
            TARGET_DIR="/system/priv-app/$appname"
            echo "Installing privileged app: $appname -> $TARGET_DIR" >> "$LOG_FILE"
            mkdir -p "$TARGET_DIR" >> "$LOG_FILE" 2>&1
            for apk in "$dir"/*.apk; do
                if [ -f "$apk" ]; then
                    cp "$apk" "$TARGET_DIR/$appname.apk" >> "$LOG_FILE" 2>&1
                    chmod 755 "$TARGET_DIR" >> "$LOG_FILE" 2>&1
                    chmod 644 "$TARGET_DIR/$appname.apk" >> "$LOG_FILE" 2>&1
                    chown -R system:system "$TARGET_DIR" >> "$LOG_FILE" 2>&1
                fi
            done
            # Copy native .so libraries if extracted
            for libdir in "$dir"/lib "$dir"/arm; do
                if [ -d "$libdir" ]; then
                    echo "Copying native libraries for $appname..." >> "$LOG_FILE"
                    cp -r "$libdir" "$TARGET_DIR/" >> "$LOG_FILE" 2>&1
                    chmod -R 755 "$TARGET_DIR/lib" 2>/dev/null
                    chmod -R 755 "$TARGET_DIR/arm" 2>/dev/null
                    chown -R system:system "$TARGET_DIR" >> "$LOG_FILE" 2>&1
                fi
            done
        fi
    done
fi
""")

        # Inject Google Permissions XML & Compatibility Patches
        script_parts.append(gen_gms_compatibility_and_arabic(log_var="LOG_FILE"))

        # Configure Aero Bar
        script_parts.append("""
# ==========================================
# CONFIGURE AERO BAR PRIVILEGES & NAVIGATION
# ==========================================
echo "Configuring Aero Bar system permissions..." >> "$LOG_FILE"
AEROBAR_STAGE="$USB_PATH/update/soft/AeroBar/AeroBar.apk"
if [ -f "$AEROBAR_STAGE" ]; then
    pm install -r -g "$AEROBAR_STAGE" >> "$LOG_FILE" 2>&1
    appops set com.aero.bar.dongfeng_shine SYSTEM_ALERT_WINDOW allow >> "$LOG_FILE" 2>&1
    appops set com.aero.bar.dongfeng_shine.debug SYSTEM_ALERT_WINDOW allow >> "$LOG_FILE" 2>&1
    appops set com.aero.bar SYSTEM_ALERT_WINDOW allow >> "$LOG_FILE" 2>&1
    settings put secure enabled_accessibility_services com.aero.bar.dongfeng_shine/com.aero.bar.service.AeroAccessibilityService:com.aero.bar.dongfeng_shine.debug/com.aero.bar.service.AeroAccessibilityService >> "$LOG_FILE" 2>&1
    settings put secure accessibility_enabled 1 >> "$LOG_FILE" 2>&1
fi

# Hide stock HVAC & navigation bar (keeps factory launcher 100% active)
echo "Hiding stock bottom bar..." >> "$LOG_FILE"
settings put global policy_control immersive.navigation=* >> "$LOG_FILE" 2>&1
if [ -f /system/build.prop ]; then
    grep -q "qemu.hw.mainkeys" /system/build.prop && sed -i "s/qemu.hw.mainkeys=.*/qemu.hw.mainkeys=1/" /system/build.prop || echo "qemu.hw.mainkeys=1" >> /system/build.prop
fi
setprop qemu.hw.mainkeys 1 >> "$LOG_FILE" 2>&1
""")

        # Install User Apps (Chrome, Gboard, Maps)
        script_parts.append("""
# ==========================================
# INSTALL GOOGLE USER APPS
# ==========================================
USER_APPS_DIR="$USB_PATH/update/user_apps"
if [ -d "$USER_APPS_DIR" ]; then
    echo "Installing Google User Applications..." >> "$LOG_FILE"
    for apk in "$USER_APPS_DIR"/*.apk; do
        if [ -f "$apk" ]; then
            echo "Installing user package: $(basename "$apk")" >> "$LOG_FILE"
            pm install -r -g "$apk" >> "$LOG_FILE" 2>&1
        fi
    done
fi
""")

        # Configure Gboard Arabic Preset
        script_parts.append(gen_gboard_config(log_var="LOG_FILE"))

        # Configure Post-Boot Auto-Launch for Aero Bar
        script_parts.append("""
# ==========================================
# POST-BOOT AUTO-LAUNCH AERO BAR
# ==========================================
echo "Enabling Aero Bar post-boot startup..." >> "$LOG_FILE"
(
    # Launch Aero Bar once Android finishes booting
    BOOT_COUNT=0
    while [ "$(getprop sys.boot_completed)" != "1" ]; do
        sleep 2
        BOOT_COUNT=$((BOOT_COUNT + 1))
        [ $BOOT_COUNT -gt 45 ] && break
    done
    sleep 3
    am start -n com.aero.bar.dongfeng_shine/com.aero.bar.presentation.MainActivity 2>/dev/null || \
    am start -n com.aero.bar/com.aero.bar.presentation.MainActivity 2>/dev/null
) &
""")

        script_parts.append(gen_mount_ro())
        script_parts.append(gen_multi_vehicle_footer(
            success_status="SUCCESS",
            with_reboot=True,
            reboot_delay=3,
            reboot_msg="Rebooting infotainment system to activate Aero Bar & Google Services..."
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
