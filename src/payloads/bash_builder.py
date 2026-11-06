"""
bash_builder.py — Reusable, atomic shell snippet and script generators for Aero Suite.
Adheres strictly to SOLID principles, specifically the Single Responsibility Principle (SRP).
Provides standardized, battle-tested building blocks for individual payloads
and multi-action batch operations (Pipeline / Cart).
"""
import os
import re
from core.constants import (
    FACTORY_LAUNCHER_PKG,
    FACTORY_PRIV_APPS,
    FACTORY_APPS,
    GMS_FULL_PURGE_PACKAGES,
    GMS_FULL_PRIVAPP_PATTERNS
)
from core.templating import render_template_file

BASH_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "bash")

# ============================================================================
# SECTION 1: SHELL CORE & LIFECYCLE
# ============================================================================

def gen_bash_header(title: str, log_filename: str = "payload.log") -> str:
    """
    Generates standard bash header with dynamic vehicle USB detection,
    smart one-time execution guard (process_complete), and log initialization.
    """
    safe_title = title.strip().upper()
    template_path = os.path.join(BASH_TEMPLATES_DIR, "header.sh")
    if os.path.exists(template_path):
        return render_template_file(template_path, title=safe_title, log_filename=log_filename)

    return f"""#!/system/bin/sh
# ==========================================
# AERO SUITE — {safe_title}
# ==========================================

USB_PATH=""
for dir in /storage/* /mnt/media_rw/* /mnt/usb* /storage/usb* /mnt/udisk* /udisk* /media* /mnt/media*; do
    if [ -f "$dir/update/custom_rep.sh" ]; then
        USB_PATH="$dir"
        break
    fi
done

if [ -z "$USB_PATH" ] || [ ! -d "$USB_PATH/update" ]; then
    for mnt in $(cut -d ' ' -f 2 /proc/mounts 2>/dev/null); do
        if [ -f "$mnt/update/custom_rep.sh" ]; then
            USB_PATH="$mnt"
            break
        fi
    done
fi

if [ -z "$USB_PATH" ] || [ "$USB_PATH" = "/" ]; then
    SCRIPT_DIR=$(cd "$(dirname "$0")" 2>/dev/null && pwd)
    USB_PATH=$(dirname "$SCRIPT_DIR")
fi

# Read Vehicle Hardware Telemetry
CAR_SERIAL=$(getprop ro.serialno 2>/dev/null)
if [ -z "$CAR_SERIAL" ] || [ "$CAR_SERIAL" = "unknown" ]; then
    CAR_SERIAL=$(getprop ro.boot.serialno 2>/dev/null)
fi
if [ -z "$CAR_SERIAL" ] || [ "$CAR_SERIAL" = "unknown" ]; then
    CAR_SERIAL=$(settings get secure android_id 2>/dev/null)
fi
if [ -z "$CAR_SERIAL" ] || [ "$CAR_SERIAL" = "unknown" ]; then
    CAR_SERIAL="CAR_$(getprop ro.product.model 2>/dev/null | tr -cd 'A-Za-z0-9_')"
fi
[ -z "$CAR_SERIAL" ] && CAR_SERIAL="DF_UNKNOWN"

CAR_MODEL=$(getprop ro.product.model 2>/dev/null)
[ -z "$CAR_MODEL" ] && CAR_MODEL=$(getprop ro.product.name 2>/dev/null)
[ -z "$CAR_MODEL" ] && CAR_MODEL="Dongfeng_Shine"

CAR_DIR="$USB_PATH/completed_cars/${{CAR_SERIAL}}"
mkdir -p "$CAR_DIR" 2>/dev/null
STATE_DIR="$CAR_DIR"
LOG_FILE="$CAR_DIR/{log_filename}"

if [ -f "$CAR_DIR/completed.done" ] || [ -f "$USB_PATH/completed_cars/${{CAR_SERIAL}}.done" ]; then
    echo "=== CAR [$CAR_MODEL | $CAR_SERIAL] ALREADY PROVISIONED BY THIS USB — SKIPPING ===" >> "$LOG_FILE"
    exit 0
fi

if [ ! -f "$LOG_FILE" ]; then
    echo "=== AERO {safe_title} START ===" > "$LOG_FILE"
else
    echo "" >> "$LOG_FILE"
    echo "=== AERO {safe_title} RESUMED ACROSS REBOOT ===" >> "$LOG_FILE"
fi
echo "Vehicle Model:  $CAR_MODEL" >> "$LOG_FILE"
echo "Vehicle Serial: $CAR_SERIAL" >> "$LOG_FILE"
date >> "$LOG_FILE"
"""


def gen_state_init(log_var: str = "LOG_FILE") -> str:
    """Initializes multi-stage checkpoint directory scoped per vehicle serial on USB."""
    return f"""STATE_DIR="$USB_PATH/completed_cars/${{CAR_SERIAL}}"
mkdir -p "$STATE_DIR" >> "${{log_var}}" 2>&1
"""


def gen_wait_for_boot_completed(settle_seconds: int = 5, log_var: str = "LOG_FILE") -> str:
    """Waits for Android system to announce boot completion, then settles system services."""
    return f"""echo "Waiting for Android framework to report boot completion..." >> "${log_var}"
BOOT_WAIT=0
while [ "$(getprop sys.boot_completed)" != "1" ]; do
    sleep 1
    BOOT_WAIT=$((BOOT_WAIT + 1))
    if [ $BOOT_WAIT -gt 60 ]; then
        echo "Boot wait timeout (60s) reached, proceeding with settling..." >> "${log_var}"
        break
    fi
done
echo "Android core booted. Settling system services for {settle_seconds} seconds..." >> "${log_var}"
sleep {settle_seconds}
"""


def gen_stage_reboot(stage_name: str, reboot_delay: int = 3, reboot_msg: str = "Rebooting for next stage...", log_var: str = "LOG_FILE") -> str:
    """Marks a stage as completed, logs countdown, and initiates hard reboot for next stage."""
    return f"""echo "=== STAGE [{stage_name}] FINISHED — REBOOTING ===" >> "${log_var}"
echo "{reboot_msg}" >> "${log_var}"
touch "$STATE_DIR/{stage_name}.done"
sync
sec={reboot_delay}
while [ $sec -gt 0 ]; do
    echo "System will restart in $sec seconds..." >> "${log_var}"
    sleep 1
    sec=$((sec - 1))
done
sync
(sleep 1; setprop sys.powerctl reboot || reboot -f || reboot) &
exit 0
"""


def gen_mount_rw(log_var: str = "LOG_FILE") -> str:
    """Generates standard commands to remount /system partition as Read-Write."""
    return f"""echo "Remounting /system partition as Read-Write..." >> "${log_var}"
mount -o remount,rw /system >> "${log_var}" 2>&1
mount -o rw,remount /system >> "${log_var}" 2>&1
busybox mount -o remount,rw /system >> "${log_var}" 2>&1
"""


def gen_mount_ro(log_var: str = "LOG_FILE") -> str:
    """Generates standard commands to lock /system partition back to Read-Only."""
    return f"""echo "Locking /system partition back to Read-Only..." >> "${log_var}"
mount -o remount,ro /system >> "${log_var}" 2>&1
busybox mount -o remount,ro /system >> "${log_var}" 2>&1
"""


def gen_reboot(delay_seconds: int = 2) -> str:
    """Generates dual sync and clean hardware/powerctl reboot command."""
    return f"""sync
sleep {delay_seconds}
sync
setprop sys.powerctl reboot || reboot -f || reboot
"""


def gen_bash_footer(
    success_status: str = "SUCCESS",
    with_reboot: bool = False,
    reboot_delay: int = 3,
    reboot_msg: str = "Rebooting infotainment system...",
    log_var: str = "LOG_FILE"
) -> str:
    """
    Generates standard process completion footer:
    Logs success, touches process_complete guard flag, syncs filesystem,
    and optionally performs clean hardware reboot with configurable countdown logging.
    """
    template_path = os.path.join(BASH_TEMPLATES_DIR, "footer.sh")
    if os.path.exists(template_path):
        return render_template_file(
            template_path,
            success_status=success_status,
            with_reboot=with_reboot,
            reboot_delay=reboot_delay,
            reboot_msg=reboot_msg,
            countdown=(reboot_delay > 0),
            target_log=f"${{{log_var}}}"
        )

    if with_reboot:
        if reboot_delay > 0:
            countdown_block = f"""sec={reboot_delay}
while [ $sec -gt 0 ]; do
    echo "System will restart after $sec seconds..." >> "${log_var}"
    sleep 1
    sec=$((sec - 1))
done
sync
"""
        else:
            countdown_block = ""

        return f"""sync
echo "=== AERO PROCESS STATUS: {success_status} ===" >> "${log_var}"
date >> "${log_var}"

# Record vehicle completion on USB registry (Zero trace on car filesystem!)
mkdir -p "$USB_PATH/completed_cars/${{CAR_SERIAL}}" 2>/dev/null
touch "$USB_PATH/completed_cars/${{CAR_SERIAL}}/completed.done"
touch "$USB_PATH/completed_cars/${{CAR_SERIAL}}.done"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] MODEL: $CAR_MODEL | SERIAL: $CAR_SERIAL | STATUS: {success_status}" >> "$USB_PATH/completed_cars/registry.txt"
sync

echo "{reboot_msg}" >> "${log_var}"
sync
{countdown_block}(sleep 1; setprop sys.powerctl reboot || reboot -f || reboot) &
"""
    else:
        return f"""sync
echo "=== AERO PROCESS STATUS: {success_status} ===" >> "${log_var}"
date >> "${log_var}"

# Record vehicle completion on USB registry (Zero trace on car filesystem!)
mkdir -p "$USB_PATH/completed_cars/${{CAR_SERIAL}}" 2>/dev/null
touch "$USB_PATH/completed_cars/${{CAR_SERIAL}}/completed.done"
touch "$USB_PATH/completed_cars/${{CAR_SERIAL}}.done"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] MODEL: $CAR_MODEL | SERIAL: $CAR_SERIAL | STATUS: {success_status}" >> "$USB_PATH/completed_cars/registry.txt"
sync
"""


def gen_multi_vehicle_header(title: str, log_filename: str = "quick_setup.log") -> str:
    """
    Generates bash header with dynamic vehicle USB detection and Multi-Vehicle USB Registry.
    Identifies car via ro.serialno / ro.boot.serialno / android_id.
    Checks car serial against $USB_PATH/completed_cars/${CAR_SERIAL}.done on the USB drive.
    STRICT USER PRIVACY GUARD: NEVER writes or touches any lock files on vehicle internal storage!
    """
    safe_title = title.strip().upper()
    return f"""#!/system/bin/sh
# ==========================================
# AERO SUITE — {safe_title}
# MULTI-VEHICLE TECHNICIAN PROVISIONING
# ==========================================

USB_PATH=""
for dir in /storage/* /mnt/media_rw/* /mnt/usb* /storage/usb* /mnt/udisk* /udisk* /media* /mnt/media*; do
    if [ -f "$dir/update/custom_rep.sh" ]; then
        USB_PATH="$dir"
        break
    fi
done

if [ -z "$USB_PATH" ] || [ ! -d "$USB_PATH/update" ]; then
    for mnt in $(cut -d ' ' -f 2 /proc/mounts 2>/dev/null); do
        if [ -f "$mnt/update/custom_rep.sh" ]; then
            USB_PATH="$mnt"
            break
        fi
    done
fi

if [ -z "$USB_PATH" ] || [ "$USB_PATH" = "/" ]; then
    SCRIPT_DIR=$(cd "$(dirname "$0")" 2>/dev/null && pwd)
    USB_PATH=$(dirname "$SCRIPT_DIR")
fi

# Read Vehicle Hardware Telemetry
CAR_SERIAL=$(getprop ro.serialno 2>/dev/null)
if [ -z "$CAR_SERIAL" ] || [ "$CAR_SERIAL" = "unknown" ]; then
    CAR_SERIAL=$(getprop ro.boot.serialno 2>/dev/null)
fi
if [ -z "$CAR_SERIAL" ] || [ "$CAR_SERIAL" = "unknown" ]; then
    CAR_SERIAL=$(settings get secure android_id 2>/dev/null)
fi
if [ -z "$CAR_SERIAL" ] || [ "$CAR_SERIAL" = "unknown" ]; then
    CAR_SERIAL="CAR_$(getprop ro.product.model 2>/dev/null | tr -cd 'A-Za-z0-9_')"
fi
[ -z "$CAR_SERIAL" ] && CAR_SERIAL="DF_UNKNOWN"

CAR_MODEL=$(getprop ro.product.model 2>/dev/null)
[ -z "$CAR_MODEL" ] && CAR_MODEL=$(getprop ro.product.name 2>/dev/null)
[ -z "$CAR_MODEL" ] && CAR_MODEL="Dongfeng_Shine"

CAR_DIR="$USB_PATH/completed_cars/${{CAR_SERIAL}}"
mkdir -p "$CAR_DIR" 2>/dev/null
STATE_DIR="$CAR_DIR"
LOG_FILE="$CAR_DIR/{log_filename}"

if [ -f "$CAR_DIR/completed.done" ] || [ -f "$USB_PATH/completed_cars/${{CAR_SERIAL}}.done" ]; then
    echo "=== CAR [$CAR_MODEL | $CAR_SERIAL] ALREADY PROVISIONED BY THIS USB — SKIPPING ===" >> "$LOG_FILE"
    exit 0
fi

if [ ! -f "$LOG_FILE" ]; then
    echo "=== AERO {safe_title} START ===" > "$LOG_FILE"
else
    echo "" >> "$LOG_FILE"
    echo "=== AERO {safe_title} RESUMED ===" >> "$LOG_FILE"
fi
echo "Vehicle Model:  $CAR_MODEL" >> "$LOG_FILE"
echo "Vehicle Serial: $CAR_SERIAL" >> "$LOG_FILE"
date >> "$LOG_FILE"
"""


def gen_multi_vehicle_footer(
    success_status: str = "SUCCESS",
    with_reboot: bool = True,
    reboot_delay: int = 3,
    reboot_msg: str = "Rebooting infotainment system...",
    log_var: str = "LOG_FILE"
) -> str:
    """
    Generates Multi-Vehicle completion footer:
    Records vehicle completion strictly in $USB_PATH/completed_cars/${CAR_SERIAL}/completed.done
    and appends a clean human-readable log entry to $USB_PATH/completed_cars/registry.txt.
    ZERO footprint on car storage: leaves NO lock files or traces on /data or /system!
    """
    countdown_block = f"""sec={reboot_delay}
while [ $sec -gt 0 ]; do
    echo "System will restart after $sec seconds..." >> "${{log_var}}"
    sleep 1
    sec=$((sec - 1))
done
sync
""" if (with_reboot and reboot_delay > 0) else ""

    reboot_cmd = "(sleep 1; setprop sys.powerctl reboot || reboot -f || reboot) &\n" if with_reboot else ""

    return f"""sync
echo "=== AERO PROCESS STATUS: {success_status} ===" >> "${log_var}"
date >> "${log_var}"

# Record vehicle completion on USB registry ONLY (Zero trace on car filesystem!)
mkdir -p "$USB_PATH/completed_cars/${{CAR_SERIAL}}" 2>/dev/null
touch "$USB_PATH/completed_cars/${{CAR_SERIAL}}/completed.done"
touch "$USB_PATH/completed_cars/${{CAR_SERIAL}}.done"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] MODEL: $CAR_MODEL | SERIAL: $CAR_SERIAL | STATUS: {success_status}" >> "$USB_PATH/completed_cars/registry.txt"
sync

echo "{reboot_msg}" >> "${log_var}"
sync
{countdown_block}{reboot_cmd}"""



# ============================================================================
# SECTION 2: APP INSTALLATION & LAUNCH (SRP)
# ============================================================================

def gen_install_system_apps(soft_dir_var: str = "SOFT_DIR", log_var: str = "LOG_FILE") -> str:
    """
    Installs System Privileged Applications from a staging folder into /system/priv-app.
    Sets ownership (system:system), permissions (755/644), and native .so libraries.
    """
    return f"""if [ -d "${soft_dir_var}" ]; then
    echo "Processing System Privileged Applications..." >> "${log_var}"
    for item in "${soft_dir_var}"/*; do
        if [ -e "$item" ]; then
            filename=$(basename "$item")
            appname="${{filename%.*}}"
            TARGET_DIR="/system/priv-app/$appname"
            if [ ! -d "/system/priv-app" ]; then
                TARGET_DIR="/system/app/$appname"
            fi
            mkdir -p "$TARGET_DIR" >> "${log_var}" 2>&1

            if [ -d "$item" ]; then
                echo "Installing System folder $filename to $TARGET_DIR..." >> "${log_var}"
                cp -r "$item"/* "$TARGET_DIR/" >> "${log_var}" 2>&1
                chown -R system:system "$TARGET_DIR" >> "${log_var}" 2>&1
                chmod -R 755 "$TARGET_DIR" >> "${log_var}" 2>&1
                chmod 644 "$TARGET_DIR"/*.apk >> "${log_var}" 2>&1
                if [ -d "$TARGET_DIR/lib" ]; then
                    chmod -R 755 "$TARGET_DIR/lib" >> "${log_var}" 2>&1
                    chmod 644 "$TARGET_DIR/lib/arm"/*.so >> "${log_var}" 2>&1
                fi
            else
                echo "Installing System APK $filename to $TARGET_DIR..." >> "${log_var}"
                cp "$item" "$TARGET_DIR/$filename" >> "${log_var}" 2>&1
                chmod 755 "$TARGET_DIR" >> "${log_var}" 2>&1
                chmod 644 "$TARGET_DIR/$filename" >> "${log_var}" 2>&1
                chown system:system "$TARGET_DIR" >> "${log_var}" 2>&1
                chown system:system "$TARGET_DIR/$filename" >> "${log_var}" 2>&1
            fi
        fi
    done
fi
"""


def gen_replace_systemui(apk_source_var: str = "SYSTEMUI_APK_SRC", log_var: str = "LOG_FILE") -> str:
    """
    Safely deploys or restores SystemUI into /system/priv-app/SystemUI-release-signed/.
    Removes stale dex/odex caches (oat/arm), sets ownership to system:system,
    and assigns 755/644 permissions.
    """
    return f"""if [ -f "${apk_source_var}" ]; then
    echo "Processing SystemUI modification..." >> "${log_var}"
    TARGET_DIR="/system/priv-app/SystemUI-release-signed"
    TARGET_APK="$TARGET_DIR/SystemUI-release-signed.apk"

    if [ ! -d "$TARGET_DIR" ] && [ -d "/system/priv-app/SystemUI" ]; then
        TARGET_DIR="/system/priv-app/SystemUI"
        TARGET_APK="$TARGET_DIR/SystemUI.apk"
    fi

    mkdir -p "$TARGET_DIR" >> "${log_var}" 2>&1
    echo "Deploying SystemUI to $TARGET_APK..." >> "${log_var}"
    cp -f "${apk_source_var}" "$TARGET_APK" >> "${log_var}" 2>&1
    chmod 755 "$TARGET_DIR" >> "${log_var}" 2>&1
    chmod 644 "$TARGET_APK" >> "${log_var}" 2>&1
    chown system:system "$TARGET_DIR" >> "${log_var}" 2>&1
    chown system:system "$TARGET_APK" >> "${log_var}" 2>&1

    # Clear stale oat/odex caches
    if [ -d "$TARGET_DIR/oat" ]; then
        echo "Clearing stale oat/odex caches in $TARGET_DIR/oat..." >> "${log_var}"
        rm -rf "$TARGET_DIR/oat" >> "${log_var}" 2>&1
    fi

    # Clear dalvik-cache entries for SystemUI
    echo "Purging dalvik-cache for SystemUI..." >> "${log_var}"
    rm -f /data/dalvik-cache/*SystemUI* 2>/dev/null
    rm -f /data/dalvik-cache/*/*SystemUI* 2>/dev/null
    sync
else
    echo "  ✗ ERROR: SystemUI payload source file not found at ${apk_source_var}" >> "${log_var}"
fi
"""


def gen_install_user_apps(user_soft_dir_var: str = "USER_SOFT_DIR", log_var: str = "LOG_FILE") -> str:
    """
    Installs User Applications directly into /data/app via PackageManager.
    Unlocks OEM security policies (persist.ais_server.3app.perm), stages APKs into /data/local/tmp/user_stage,
    and runs multi-tier installation (Session Installer -> PackageInstaller -> Vending -> PM -> cmd package).
    """
    return f"""if [ -d "${user_soft_dir_var}" ]; then
    echo "Unlocking OEM third-party app installation policies..." >> "${log_var}"
    setprop persist.ais_server.3app.perm 1 >> "${log_var}" 2>&1
    settings put global install_non_market_apps 1 >> "${log_var}" 2>&1
    settings put secure install_non_market_apps 1 >> "${log_var}" 2>&1
    settings put system install_non_market_apps 1 >> "${log_var}" 2>&1
    settings put global package_verifier_enable 0 >> "${log_var}" 2>&1
    settings put global package_verifier_user_consent -1 >> "${log_var}" 2>&1
    settings put global verifier_verify_adb_installs 0 >> "${log_var}" 2>&1

    echo "Processing User Apps..." >> "${log_var}"
    STAGE_DIR="/data/local/tmp/user_stage"
    rm -rf "$STAGE_DIR" >> "${log_var}" 2>&1
    mkdir -p "$STAGE_DIR" >> "${log_var}" 2>&1
    for item in "${user_soft_dir_var}"/*.apk; do
        if [ -f "$item" ]; then
            fname=$(basename "$item")
            echo "Installing User APK: $fname..." >> "${log_var}"
            cp -f "$item" "$STAGE_DIR/$fname" >> "${log_var}" 2>&1
            chmod 644 "$STAGE_DIR/$fname" >> "${log_var}" 2>&1

            sz=$(stat -c%s "$STAGE_DIR/$fname" 2>/dev/null || wc -c < "$STAGE_DIR/$fname")
            installed=false
            sess_id=$(pm install-create -i com.android.packageinstaller -r -g -S $sz 2>&1 | tr -cd '0-9')
            if [ -z "$sess_id" ]; then
                sess_id=$(pm install-create -i com.android.vending -r -g -S $sz 2>&1 | tr -cd '0-9')
            fi
            if [ -z "$sess_id" ]; then
                sess_id=$(pm install-create -r -g -S $sz 2>&1 | tr -cd '0-9')
            fi

            if [ -n "$sess_id" ]; then
                echo "Created session $sess_id for $fname" >> "${log_var}"
                pm install-write -S $sz $sess_id base "$STAGE_DIR/$fname" >> "${log_var}" 2>&1
                commit_res=$(pm install-commit $sess_id 2>&1)
                echo "Session commit: $commit_res" >> "${log_var}"
                if echo "$commit_res" | grep -qi "Success"; then
                    installed=true
                else
                    pm install-abandon $sess_id >/dev/null 2>&1
                fi
            fi

            if [ "$installed" = false ]; then
                inst_res=$(pm install -i com.android.packageinstaller -r -g "$STAGE_DIR/$fname" 2>&1)
                echo "$inst_res" >> "${log_var}"
                if echo "$inst_res" | grep -qi "Success"; then
                    installed=true
                else
                    inst_res=$(pm install -i com.android.vending -r -g "$STAGE_DIR/$fname" 2>&1)
                    echo "$inst_res" >> "${log_var}"
                    if echo "$inst_res" | grep -qi "Success"; then
                        installed=true
                    else
                        inst_res=$(pm install -r -g "$STAGE_DIR/$fname" 2>&1)
                        echo "$inst_res" >> "${log_var}"
                        if echo "$inst_res" | grep -qi "Success"; then
                            installed=true
                        fi
                    fi
                fi
            fi

            if [ "$installed" = false ]; then
                cmd_res=$(cmd package install -i com.android.packageinstaller -r -g "$STAGE_DIR/$fname" 2>&1)
                echo "cmd package: $cmd_res" >> "${log_var}"
                if echo "$cmd_res" | grep -qi "Success"; then
                    installed=true
                fi
            fi

            if [ "$installed" = true ]; then
                echo "✓ $fname installed successfully as User App!" >> "${log_var}"
                flat_pkg=$(basename "$fname" .apk)
                pm enable "$flat_pkg" >/dev/null 2>&1
            else
                echo "⚠ $fname installation rejected by PM." >> "${log_var}"
            fi

            rm -f "$STAGE_DIR/$fname" >> "${log_var}" 2>&1
        fi
    done
    rm -rf "$STAGE_DIR" >> "${log_var}" 2>&1
fi
"""


def gen_disable_app(package_name: str = FACTORY_LAUNCHER_PKG, log_var: str = "LOG_FILE") -> str:
    """Generates freeze / disable commands for an application (e.g. stock launcher), sets any custom home launcher as default, and triggers HOME intent."""
    return f"""echo "Freezing package: {package_name}..." >> "${log_var}"
pm disable {package_name} >> "${log_var}" 2>&1
pm disable-user --user 0 {package_name} >> "${log_var}" 2>&1

# Generic resolution for newly installed / third-party custom launcher
NEW_HOME=$(pm query-activities --brief -c android.intent.category.HOME -a android.intent.action.MAIN 2>/dev/null | grep -v "{package_name}" | head -n 1 | tr -d '\\r')
if [ -n "$NEW_HOME" ] && echo "$NEW_HOME" | grep -q "/"; then
    echo "Registering default Home launcher: $NEW_HOME..." >> "${log_var}"
    cmd package set-home-activity "$NEW_HOME" >> "${log_var}" 2>&1
fi

# Send Home keyevent to stabilize foreground activity
input keyevent KEYCODE_HOME 2>/dev/null
"""


def gen_enable_app(
    package_name: str = FACTORY_LAUNCHER_PKG,
    set_home_activity: str = None,
    log_var: str = "LOG_FILE"
) -> str:
    """Generates unfreeze / enable commands for an application, with optional default home activity."""
    snippet = f"""echo "Unfreezing package: {package_name}..." >> "${log_var}"
pm enable {package_name} >> "${log_var}" 2>&1
pm default-state {package_name} >> "${log_var}" 2>&1
"""
    if set_home_activity:
        snippet += f"""cmd package set-home-activity {set_home_activity} >> "${log_var}" 2>&1
"""
    return snippet


def gen_grant_permissions(
    package_name: str,
    permissions: list = None,
    appops: list = None,
    log_var: str = "LOG_FILE"
) -> str:
    """Generates permission grant commands via pm grant and appops set."""
    snippet = f"""echo "Granting permissions for {package_name}..." >> "${log_var}"
pm enable {package_name} >/dev/null 2>&1
"""
    if permissions:
        for p in permissions:
            snippet += f"""pm grant {package_name} {p} >/dev/null 2>&1
"""
    if appops:
        for op in appops:
            snippet += f"""appops set {package_name} {op} allow >/dev/null 2>&1
"""
    return snippet


def gen_launch_app(
    package_name: str,
    activity_name: str = None,
    log_var: str = "LOG_FILE",
    capture_debug_log: bool = False
) -> str:
    """
    Generates battle-tested Multi-Tier Launch Engine:
    - Wakes up display
    - Injects specific permissions/optimizations if needed (Files by Google, Play Store)
    - Tier 1: Dynamic Activity Resolution via PackageManager (`cmd package resolve-activity`)
    - Tier 2: Category LAUNCHER Intent (`am start -c android.intent.category.LAUNCHER`)
    - Tier 3: Known Specific Activity Component Fallbacks
    - Tier 4: Monkey Event Injection (Last Resort)
    - Optionally captures diagnostic logcat
    """
    clean_pkg = re.sub(r'[^a-zA-Z0-9._]', '', package_name)

    snippet = f"""TARGET_PKG="{clean_pkg}"
echo "Step: Checking if $TARGET_PKG is installed..." >> "${log_var}"

if pm path "$TARGET_PKG" >/dev/null 2>&1; then
    echo "  ✓ Package found on system. Launching $TARGET_PKG..." >> "${log_var}"
    input keyevent 224 2>/dev/null
"""
    if clean_pkg == "com.google.android.apps.nbu.files":
        snippet += f"""    echo "Configuring permissions for Files by Google..." >> "${log_var}"
    pm enable com.google.android.apps.nbu.files >/dev/null 2>&1
    pm grant com.google.android.apps.nbu.files android.permission.READ_EXTERNAL_STORAGE >/dev/null 2>&1
    pm grant com.google.android.apps.nbu.files android.permission.WRITE_EXTERNAL_STORAGE >/dev/null 2>&1
    pm grant com.google.android.apps.nbu.files android.permission.ACCESS_MEDIA_LOCATION >/dev/null 2>&1
    pm grant com.google.android.apps.nbu.files android.permission.WRITE_MEDIA_STORAGE >/dev/null 2>&1
    pm grant com.google.android.apps.nbu.files android.permission.PACKAGE_USAGE_STATS >/dev/null 2>&1
    appops set com.google.android.apps.nbu.files READ_EXTERNAL_STORAGE allow >/dev/null 2>&1
    appops set com.google.android.apps.nbu.files WRITE_EXTERNAL_STORAGE allow >/dev/null 2>&1
    appops set com.google.android.apps.nbu.files MANAGE_EXTERNAL_STORAGE allow >/dev/null 2>&1
"""
    elif clean_pkg == "com.android.vending":
        snippet += f"""    echo "Configuring environment for Google Play Store..." >> "${log_var}"
    pm enable com.android.vending >/dev/null 2>&1
    pm enable com.google.android.gms >/dev/null 2>&1
    pm enable com.google.android.gsf >/dev/null 2>&1
    pm enable com.google.android.gsf.login >/dev/null 2>&1
    settings put global device_provisioned 1 >/dev/null 2>&1
    settings put secure user_setup_complete 1 >/dev/null 2>&1
    rm -f /system/etc/permissions/privapp-permissions-google.xml /system/etc/permissions/privapp-permissions-documentsui.xml >/dev/null 2>&1
"""
    else:
        snippet += f"""    pm enable "$TARGET_PKG" >/dev/null 2>&1
"""

    snippet += f"""
    # --- TIER 1: Dynamic Activity Resolution via PackageManager ---
    RESOLVED_ACT=""
    if command -v cmd >/dev/null 2>&1; then
        RESOLVED_ACT=$(cmd package resolve-activity --brief "$TARGET_PKG" 2>/dev/null | tail -n 1 | tr -d '\\r')
    fi
    if [ -n "$RESOLVED_ACT" ] && [ "$RESOLVED_ACT" != "No activity found" ] && ! echo "$RESOLVED_ACT" | grep -qi "error"; then
        echo "  [Tier 1] Launching resolved activity: $RESOLVED_ACT..." >> "${log_var}"
        am start -f 0x10200000 -n "$RESOLVED_ACT" >> "${log_var}" 2>&1
        sleep 1
    fi

    # --- TIER 2: Category LAUNCHER Intent ---
    if ! (ps -A 2>/dev/null || ps) | grep -q "$TARGET_PKG"; then
        echo "  [Tier 2] Launching via Category LAUNCHER..." >> "${log_var}"
        am start -f 0x10200000 -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p "$TARGET_PKG" >> "${log_var}" 2>&1
        sleep 1
    fi

    # --- TIER 3: Known Specific Activity Fallbacks ---
    if ! (ps -A 2>/dev/null || ps) | grep -q "$TARGET_PKG"; then
"""
    if activity_name:
        snippet += f"""        echo "  [Tier 3] Launching specified activity: {activity_name}..." >> "${log_var}"
        am start -f 0x10200000 -n {activity_name} >> "${log_var}" 2>&1
        sleep 1
"""
    elif clean_pkg == "com.google.android.apps.nbu.files":
        snippet += f"""        echo "  [Tier 3] Launching Files HomeActivity..." >> "${log_var}"
        am start -f 0x10200000 -n com.google.android.apps.nbu.files/.home.HomeActivity >> "${log_var}" 2>&1
        sleep 1
        if ! (ps -A 2>/dev/null || ps) | grep -q "$TARGET_PKG"; then
            am start -f 0x10200000 -n com.google.android.apps.nbu.files/com.google.android.apps.nbu.files.home.HomeActivity >> "${log_var}" 2>&1
        fi
        sleep 1
"""
    elif clean_pkg == "com.android.vending":
        snippet += f"""        echo "  [Tier 3] Launching Play Store Activity..." >> "${log_var}"
        am start -f 0x10200000 -n com.android.vending/.AssetBrowserActivity >> "${log_var}" 2>&1
        sleep 1
        if ! (ps -A 2>/dev/null || ps) | grep -q "$TARGET_PKG"; then
            am start -f 0x10200000 -n com.android.vending/com.google.android.finsky.activities.MainActivity >> "${log_var}" 2>&1
        fi
        sleep 1
"""
    elif clean_pkg == "com.android.settings":
        snippet += f"""        echo "  [Tier 3] Launching Android Native Settings..." >> "${log_var}"
        am start -f 0x10200000 -n com.android.settings/.Settings >> "${log_var}" 2>&1
        sleep 1
        if ! (ps -A 2>/dev/null || ps) | grep -q "$TARGET_PKG"; then
            am start -f 0x10200000 -a android.settings.SETTINGS >> "${log_var}" 2>&1
        fi
        sleep 1
"""
    else:
        snippet += f"""        echo "  [Tier 3] Skipping Tier 3 (no specific component registered)." >> "${log_var}"
"""

    snippet += f"""    fi

    # --- TIER 4: Monkey Event Injection (Last Resort) ---
    if ! (ps -A 2>/dev/null || ps) | grep -q "$TARGET_PKG"; then
        echo "  [Tier 4] Dispatching Monkey trigger..." >> "${log_var}"
        monkey -p "$TARGET_PKG" -c android.intent.category.LAUNCHER --pct-syskeys 0 1 >> "${log_var}" 2>&1
        sleep 1
        if ! (ps -A 2>/dev/null || ps) | grep -q "$TARGET_PKG"; then
            monkey -p "$TARGET_PKG" 1 >> "${log_var}" 2>&1
        fi
    fi

    if (ps -A 2>/dev/null || ps) | grep -q "$TARGET_PKG"; then
        echo "  ✓ Application $TARGET_PKG process is ACTIVE and running." >> "${log_var}"
    else
        echo "  ⚠ Launch intents sent; process state indeterminate." >> "${log_var}"
    fi
"""
    if capture_debug_log:
        snippet += f"""    sleep 2
    echo "Capturing diagnostic logcat..." >> "${log_var}"
    logcat -d -v time -t 200 > "$USB_PATH/app_launch_debug.log" 2>&1
"""

    snippet += f"""else
    echo "  ✗ ERROR: Package $TARGET_PKG is NOT installed on this vehicle." >> "${log_var}"
fi
"""
    return snippet


# ============================================================================
# SECTION 3: APP UNINSTALLATION (SRP: System vs User App)
# ============================================================================

def _sanitize_pkg_spec(package_name: str) -> tuple:
    if package_name.startswith("$"):
        return package_name, package_name, True
    safe = re.sub(r'[^a-zA-Z0-9._\-]', '', package_name)
    clean = safe.split('.')[-1]
    return safe, clean, False


def gen_wipe_app_data(package_name: str, log_var: str = "LOG_FILE") -> str:
    """
    Wipes application user data directories, user_de storage, media storage,
    and compiled Dalvik bytecode cache for a specific package.
    """
    safe_pkg, _, _ = _sanitize_pkg_spec(package_name)
    return f"""echo "  Wiping user data & Dalvik cache for {safe_pkg}..." >> "${log_var}"
rm -rf "/data/data/{safe_pkg}" >> "${log_var}" 2>&1
rm -rf "/data/user/0/{safe_pkg}" >> "${log_var}" 2>&1
rm -rf "/data/user_de/0/{safe_pkg}" >> "${log_var}" 2>&1
rm -rf "/data/media/0/Android/data/{safe_pkg}" >> "${log_var}" 2>&1
rm -rf "/data/dalvik-cache/arm/*{safe_pkg}"* >> "${log_var}" 2>&1
"""


def gen_uninstall_user_app(package_name: str, log_var: str = "LOG_FILE") -> str:
    """
    Uninstalls a third-party User Application installed in /data/app.
    Calls pm clear, pm uninstall, removes staged APKs, and wipes all user data.
    """
    safe_pkg, _, _ = _sanitize_pkg_spec(package_name)
    return f"""echo "Uninstalling User App: {safe_pkg}..." >> "${log_var}"
pm clear "{safe_pkg}" >> "${log_var}" 2>&1
pm uninstall "{safe_pkg}" >> "${log_var}" 2>&1
rm -rf /data/app/{safe_pkg}* >> "${log_var}" 2>&1
rm -rf /data/app/*{safe_pkg}* >> "${log_var}" 2>&1
{gen_wipe_app_data(safe_pkg, log_var=log_var)}"""


def gen_uninstall_system_app(package_name: str, purge_data: bool = True, log_var: str = "LOG_FILE") -> str:
    """
    Uninstalls a Privileged or System Application from /system/priv-app and /system/app.
    Dynamically discovers installation directory via `pm path`, deletes the system directory,
    clears package state from PackageManager, and cleans user data.
    """
    safe_pkg, clean_name, is_var = _sanitize_pkg_spec(package_name)
    extra_patterns = f' "/system/priv-app/*{clean_name}*"' if not is_var else ''
    extra_app_patterns = f' "/system/app/*{clean_name}*"' if not is_var else ''
    snippet = f"""echo "Uninstalling System Privileged App: {safe_pkg}..." >> "${log_var}"
PKG_PATH=$(pm path "{safe_pkg}" 2>/dev/null | cut -d ':' -f 2)
if [ -n "$PKG_PATH" ]; then
    PKG_DIR=$(dirname "$PKG_PATH")
    echo "  Removing detected system install directory: $PKG_DIR" >> "${log_var}"
    rm -rf "$PKG_DIR" >> "${log_var}" 2>&1
    pm clear "{safe_pkg}" >/dev/null 2>&1
    pm uninstall "{safe_pkg}" >/dev/null 2>&1
fi
rm -rf "/system/priv-app/{safe_pkg}" "/system/priv-app/*{safe_pkg}*"{extra_patterns} >> "${log_var}" 2>&1
rm -rf "/system/app/{safe_pkg}" "/system/app/*{safe_pkg}*"{extra_app_patterns} >> "${log_var}" 2>&1
"""
    if purge_data:
        snippet += gen_wipe_app_data(safe_pkg, log_var=log_var)
    return snippet


def gen_uninstall_app(package_name: str, log_var: str = "LOG_FILE") -> str:
    """
    High-level Dual-Sweep application uninstaller:
    Safely purges the application whether installed as a User App (/data/app)
    or as a System App (/system/priv-app).
    """
    safe_pkg, clean_name, is_var = _sanitize_pkg_spec(package_name)
    extra_patterns = f' "/system/priv-app/*{clean_name}*"' if not is_var else ''
    extra_app_patterns = f' "/system/app/*{clean_name}*"' if not is_var else ''
    return f"""echo "Performing Dual-Sweep uninstallation for: {safe_pkg}" >> "${log_var}"
PKG_PATH=$(pm path "{safe_pkg}" 2>/dev/null | cut -d ':' -f 2)
if [ -n "$PKG_PATH" ]; then
    PKG_DIR=$(dirname "$PKG_PATH")
    echo "  Removing detected install directory: $PKG_DIR" >> "${log_var}"
    rm -rf "$PKG_DIR" >> "${log_var}" 2>&1
fi
pm clear "{safe_pkg}" >> "${log_var}" 2>&1
pm uninstall "{safe_pkg}" >> "${log_var}" 2>&1

# 1. Purge from User Apps (/data/app)
rm -rf /data/app/{safe_pkg}* /data/app/*{safe_pkg}* >> "${log_var}" 2>&1

# 2. Purge from System Apps (/system/priv-app & /system/app)
rm -rf "/system/priv-app/{safe_pkg}" "/system/priv-app/*{safe_pkg}*"{extra_patterns} >> "${log_var}" 2>&1
rm -rf "/system/app/{safe_pkg}" "/system/app/*{safe_pkg}*"{extra_app_patterns} >> "${log_var}" 2>&1

# 3. Clean user data & caches
{gen_wipe_app_data(safe_pkg, log_var=log_var)}"""


def gen_purge_apps(
    packages: list,
    wipe_privapp_patterns: list = None,
    wipe_accounts: bool = False,
    purge_system_apps: bool = False,
    log_var: str = "LOG_FILE"
) -> str:
    """
    Batch purge generator for a list of packages:
    Iterates through packages executing deep uninstalls, cache wipes,
    and optional system app remnants.
    """
    if not packages and not wipe_privapp_patterns and not wipe_accounts:
        return ""

    snippet = ""
    if packages:
        snippet += f"""echo "Uninstalling package instances and wiping caches..." >> "${log_var}"
for pkg in {" ".join(packages)}; do
"""
        if purge_system_apps:
            snippet += f"""    {gen_uninstall_app('$pkg', log_var=log_var)}
"""
        else:
            snippet += f"""    {gen_uninstall_user_app('$pkg', log_var=log_var)}
"""
        snippet += "done\n"

    if wipe_privapp_patterns:
        snippet += f"""echo "Purging system priv-app and app remnants matching patterns..." >> "${log_var}"
"""
        for pat in wipe_privapp_patterns:
            snippet += f"""rm -rf /system/priv-app/{pat} /system/app/{pat} >> "${log_var}" 2>&1
"""

    if wipe_accounts:
        snippet += gen_wipe_account_databases(log_var=log_var)

    return snippet


def gen_system_purge_reboot_check(log_var: str = "LOG_FILE") -> str:
    """Reboots if system app components were removed to clear framework caches."""
    return f"""if grep -q "Removing detected install directory: /system" "${log_var}" 2>/dev/null; then
    echo "System app components were removed. Rebooting infotainment system to clean framework cache..." >> "${log_var}"
    sync
    (sleep 3; setprop sys.powerctl reboot; reboot) &
fi
"""


# ============================================================================
# SECTION 4: GRANULAR DATA WIPING (SRP)
# ============================================================================

def gen_wipe_account_databases(log_var: str = "LOG_FILE") -> str:
    """Wipes Android account database files and sync states."""
    return f"""echo "Wiping account databases and sync states..." >> "${log_var}"
rm -rf /data/system/users/0/accounts.db* >> "${log_var}" 2>&1
rm -rf /data/system_de/0/accounts_de.db* >> "${log_var}" 2>&1
rm -rf /data/system/sync/* >> "${log_var}" 2>&1
"""


def gen_wipe_bluetooth_data(log_var: str = "LOG_FILE") -> str:
    """
    Terminates Bluetooth daemons, wipes pairing databases and hardware configs,
    clears Qinggan and Android Bluetooth providers, and sets factory reset flags.
    """
    return f"""echo "Terminating Bluetooth daemons & clearing pairing databases..." >> "${log_var}"
# 1. Disable Bluetooth stack
svc bluetooth disable >> "${log_var}" 2>&1
setprop bluetooth.status off >> "${log_var}" 2>&1

# 2. Force-stop all Bluetooth, phone, and settings processes
for pkg in com.android.bluetooth com.qinggan.btservice com.qinggan.bluetoothphone org.codeaurora.bluetooth com.qinggan.app.setting com.qinggan.providers.settings; do
    am force-stop "$pkg" >> "${log_var}" 2>&1
done

# 3. Aggressively kill daemons in memory to prevent flushing in-memory cache back to disk
pkill -9 -f "com.android.bluetooth" >> "${log_var}" 2>&1
pkill -9 -f "com.qinggan.btservice" >> "${log_var}" 2>&1
pkill -9 -f "com.qinggan.bluetoothphone" >> "${log_var}" 2>&1
pkill -9 -f "org.codeaurora.bluetooth" >> "${log_var}" 2>&1

# 4. Truncate and purge Fluoride / Bluedroid paired devices config files
for bt_file in \\
    /data/misc/bluedroid/bt_config.conf \\
    /data/misc/bluedroid/bt_config.bak \\
    /data/misc/bluetooth/bt_config.conf \\
    /data/misc/bluetooth/bt_config.bak \\
    /data/vendor/bluetooth/bt_config.conf \\
    /data/vendor/bluetooth/bt_config.bak; do
    if [ -f "$bt_file" ]; then
        echo "" > "$bt_file" 2>/dev/null
        rm -f "$bt_file" 2>/dev/null
    fi
done
rm -rf /data/misc/bluedroid/* /data/misc/bluetooth/* /data/vendor/bluetooth/* >> "${log_var}" 2>&1

# 5. Clear package runtime data and SQLite databases
for pkg in com.android.bluetooth com.qinggan.btservice com.qinggan.bluetoothphone org.codeaurora.bluetooth com.qinggan.app.setting com.qinggan.providers.settings; do
    pm clear "$pkg" >> "${log_var}" 2>&1
done

rm -rf /data/data/com.android.bluetooth /data/user_de/0/com.android.bluetooth >> "${log_var}" 2>&1
rm -rf /data/data/com.qinggan.btservice /data/user_de/0/com.qinggan.btservice >> "${log_var}" 2>&1
rm -rf /data/data/com.qinggan.bluetoothphone /data/user_de/0/com.qinggan.bluetoothphone >> "${log_var}" 2>&1
rm -rf /data/data/org.codeaurora.bluetooth /data/user_de/0/org.codeaurora.bluetooth >> "${log_var}" 2>&1
rm -rf /data/data/com.qinggan.app.setting /data/user_de/0/com.qinggan.app.setting >> "${log_var}" 2>&1
rm -rf /data/data/com.qinggan.providers.settings /data/user_de/0/com.qinggan.providers.settings >> "${log_var}" 2>&1

# 6. Delete global & secure Bluetooth settings
settings delete global bluetooth_on >> "${log_var}" 2>&1
settings delete secure bluetooth_address >> "${log_var}" 2>&1
settings delete secure bluetooth_name >> "${log_var}" 2>&1
settings delete global bluetooth_name >> "${log_var}" 2>&1
settings delete global bluetooth_disabled_profiles >> "${log_var}" 2>&1
settings delete secure bluetooth_phonebook_priority >> "${log_var}" 2>&1

# 7. Delete Qinggan Bluetooth records from content providers
content delete --uri content://com.qinggan.bluetoothphone/calllog >> "${log_var}" 2>&1
content delete --uri content://com.qinggan.bluetoothphone/contact >> "${log_var}" 2>&1
content delete --uri content://com.qinggan.bluetooth.contact.provider/black_list_info >> "${log_var}" 2>&1
content delete --uri content://com.qinggan.bluetooth.contact.provider/contact >> "${log_var}" 2>&1
content delete --uri content://com.qinggan.bluetooth.contact.provider/contact_info >> "${log_var}" 2>&1
content delete --uri content://com.qinggan.bluetooth.contact.provider/phone >> "${log_var}" 2>&1
content delete --uri content://qinggan.settings/global --where "name LIKE '%bluetooth%' OR name LIKE '%bt%'" >> "${log_var}" 2>&1
content delete --uri content://qinggan.settings/secure --where "name LIKE '%bluetooth%' OR name LIKE '%bt%'" >> "${log_var}" 2>&1
content delete --uri content://qinggan.settings/system --where "name LIKE '%bluetooth%' OR name LIKE '%bt%'" >> "${log_var}" 2>&1

# 8. Set factory reset and clean config persistence flags
setprop persist.bluetooth.factoryreset true
setprop persist.vendor.bt.clean.config true
setprop persist.bluetooth.btsnooplogmode disabled
"""


gen_bluetooth_factory_reset = gen_wipe_bluetooth_data


def gen_wipe_cache_partition(log_var: str = "LOG_FILE") -> str:
    """Purges /cache partition and ensures clean directory permissions."""
    return f"""echo "Purging /cache partition and clearing stale recovery commands..." >> "${log_var}"
rm -rf /cache/* >> "${log_var}" 2>&1
mkdir -p /cache >> "${log_var}" 2>&1
chmod 771 /cache >> "${log_var}" 2>&1
"""


def gen_clear_bootloader_control_block(log_var: str = "LOG_FILE") -> str:
    """Clears Bootloader Control Block (BCB) in misc partition to prevent recovery boot loops."""
    return f"""echo "Clearing BCB in misc partition to prevent recovery boot loops..." >> "${log_var}"
for dev in /dev/block/bootdevice/by-name/misc /dev/block/platform/*/by-name/misc /dev/block/by-name/misc; do
    if [ -b "$dev" ]; then
        echo "  Clearing BCB on block device: $dev" >> "${log_var}"
        dd if=/dev/zero of="$dev" bs=512 count=64 >> "${log_var}" 2>&1
        break
    fi
done
"""


def gen_wipe_data_partition(log_var: str = "LOG_FILE") -> str:
    """
    Performs complete deep root wipe of /data partition, initializes fresh directories,
    purges /cache, and clears Bootloader Control Block (BCB).
    """
    return f"""echo "Executing complete root wipe of /data partition..." >> "${log_var}"
# Kill daemons before wiping so they cannot write dirty in-memory buffers back to disk
pkill -9 -f "bluetooth" 2>/dev/null
pkill -9 -f "btservice" 2>/dev/null
rm -rf /data/app/* >> "${log_var}" 2>&1
rm -rf /data/data/* >> "${log_var}" 2>&1
rm -rf /data/user/* >> "${log_var}" 2>&1
rm -rf /data/user_de/* >> "${log_var}" 2>&1
rm -rf /data/system/* >> "${log_var}" 2>&1
rm -rf /data/system_de/* >> "${log_var}" 2>&1
rm -rf /data/property/* >> "${log_var}" 2>&1
rm -rf /data/media/* /data/media/0/* /sdcard/* >> "${log_var}" 2>&1
rm -rf /data/misc/* >> "${log_var}" 2>&1
rm -rf /data/vendor/* >> "${log_var}" 2>&1
rm -rf /data/dalvik-cache/* /cache/dalvik-cache/* >> "${log_var}" 2>&1
rm -rf /data/local/* >> "${log_var}" 2>&1
rm -rf /data/tombstones/* >> "${log_var}" 2>&1
rm -rf /data/anr/* >> "${log_var}" 2>&1
rm -rf /data/log/* /data/logs/* >> "${log_var}" 2>&1

# Initialize clean directory structures for fresh first boot
mkdir -p /data/system /data/media/0 /data/local/tmp /data/misc/bluedroid /data/misc/bluetooth >> "${log_var}" 2>&1
chmod 775 /data/system /data/media /data/local/tmp >> "${log_var}" 2>&1
chmod 770 /data/misc/bluedroid /data/misc/bluetooth >> "${log_var}" 2>&1
chown system:system /data/system >> "${log_var}" 2>&1
chown bluetooth:bluetooth /data/misc/bluedroid /data/misc/bluetooth >> "${log_var}" 2>&1
chown media_rw:media_rw /data/media /data/media/0 >> "${log_var}" 2>&1

{gen_wipe_cache_partition(log_var=log_var)}
{gen_clear_bootloader_control_block(log_var=log_var)}"""


# ============================================================================
# SECTION 5: WHITELIST PURGE & AUTO-HEALING (FACTORY RESET)
# ============================================================================

def gen_purge_non_whitelisted_apps(
    whitelist: list,
    target_system_dir: str = "/system/priv-app",
    log_var: str = "LOG_FILE"
) -> str:
    """
    Iterates over subdirectories of target_system_dir, checks against whitelist,
    and purges any non-factory directory.
    """
    wl_str = " ".join(whitelist)
    return f"""echo "Purging non-whitelisted packages in {target_system_dir}..." >> "${log_var}"
WHITELIST="{wl_str}"
for dir in {target_system_dir}/*; do
    if [ -d "$dir" ]; then
        name="${{dir##*/}}"
        is_allowed=false
        for fw in $WHITELIST; do
            if [ "$name" = "$fw" ]; then is_allowed=true; break; fi
        done
        if [ "$is_allowed" = "false" ]; then
            echo "  Purging non-factory component: $name" >> "${log_var}"
            rm -rf "$dir" >> "${log_var}" 2>&1
        fi
    fi
done
"""


def gen_auto_heal_factory_apps(
    source_backup_dir: str,
    target_system_dir: str,
    log_var: str = "LOG_FILE"
) -> str:
    """
    Restores missing factory applications from USB backup into target_system_dir
    only if the app folder does not exist on the device.
    """
    return f"""if [ -d "{source_backup_dir}" ]; then
    echo "Auto-healing missing factory apps from {source_backup_dir} to {target_system_dir}..." >> "${log_var}"
    for fdir in "{source_backup_dir}"/*; do
        if [ -d "$fdir" ]; then
            bname="${{fdir##*/}}"
            if [ ! -d "{target_system_dir}/$bname" ]; then
                echo "  Restoring missing factory app: $bname" >> "${log_var}"
                cp -r "$fdir" "{target_system_dir}/" >> "${log_var}" 2>&1
                chmod 755 "{target_system_dir}/$bname" >> "${log_var}" 2>&1
                chmod 644 "{target_system_dir}/$bname"/*.apk >> "${log_var}" 2>&1
            fi
        fi
    done
fi
"""


# ============================================================================
# SECTION 6: GMS & SYSTEM CUSTOMIZATION (SRP)
# ============================================================================

def gen_purge_stale_gms(log_var: str = "LOG_FILE") -> str:
    """Deeply purges stale Google Play Services, Framework, Store, accounts, and caches."""
    return gen_purge_apps(
        packages=GMS_FULL_PURGE_PACKAGES,
        wipe_privapp_patterns=GMS_FULL_PRIVAPP_PATTERNS,
        wipe_accounts=True,
        purge_system_apps=True,
        log_var=log_var
    )


def gen_inject_voice_recognizers(log_var: str = "LOG_FILE") -> str:
    """Injects android.software.voice_recognizers feature XML to enable Google Voice Assistant."""
    return f"""echo "Injecting Voice Recognizers feature..." >> "${log_var}"
cat << 'EOF' > /system/etc/permissions/voice_recognizers.xml
<?xml version="1.0" encoding="utf-8"?>
<permissions>
    <feature name="android.software.voice_recognizers" />
</permissions>
EOF
chmod 644 /system/etc/permissions/voice_recognizers.xml >> "${log_var}" 2>&1
"""


def gen_inject_gservices_features(log_var: str = "LOG_FILE") -> str:
    """Injects cn.google.services and services_updater feature declarations."""
    return f"""echo "Injecting Google Services compatibility features for head unit..." >> "${log_var}"
cat << 'EOF' > /system/etc/permissions/gservices.xml
<?xml version="1.0" encoding="utf-8"?>
<permissions>
    <feature name="cn.google.services" />
    <feature name="com.google.android.feature.services_updater" />
</permissions>
EOF
chmod 644 /system/etc/permissions/gservices.xml >> "${log_var}" 2>&1
"""


def gen_neutralize_automotive_flags(log_var: str = "LOG_FILE") -> str:
    """Removes android.hardware.type.automotive declarations to allow normal Play Store compatibility."""
    return f"""echo "Neutralizing automotive restrictions in permissions XMLs..." >> "${log_var}"
for xml_file in /system/etc/permissions/*.xml; do
    if grep -q "android.hardware.type.automotive" "$xml_file" 2>/dev/null; then
        echo "  Neutralizing automotive feature in $xml_file" >> "${log_var}"
        sed -i '/android.hardware.type.automotive/d' "$xml_file" >> "${log_var}" 2>&1
    fi
done
"""


def gen_force_provisioning_flags(log_var: str = "LOG_FILE") -> str:
    """Forces device_provisioned and user_setup_complete flags to prevent setup wizard locks."""
    return f"""echo "Forcing device provisioned flags..." >> "${log_var}"
settings put global device_provisioned 1 >> "${log_var}" 2>&1
settings put secure user_setup_complete 1 >> "${log_var}" 2>&1
"""


gen_device_provisioning = gen_force_provisioning_flags


def gen_force_arabic_locale(log_var: str = "LOG_FILE") -> str:
    """Forces Arabic system locale across Settings provider and system properties."""
    return f"""echo "Forcing Arabic system locale..." >> "${log_var}"
settings put system system_locales ar >> "${log_var}" 2>&1
settings put global system_locales ar >> "${log_var}" 2>&1
setprop persist.sys.locale ar >> "${log_var}" 2>&1
mkdir -p /data/property >> "${log_var}" 2>&1
echo -n "ar" > /data/property/persist.sys.locale
chmod 600 /data/property/persist.sys.locale >> "${log_var}" 2>&1
chown root:root /data/property/persist.sys.locale >> "${log_var}" 2>&1
"""


def gen_configure_gboard_ime(log_var: str = "LOG_FILE") -> str:
    """Enables Gboard, sets it as default input method, and disables stock Chinese IME."""
    return f"""if pm path com.google.android.inputmethod.latin >/dev/null 2>&1; then
    echo "Configuring Gboard as Default Input Method..." >> "${log_var}"
    pm enable com.google.android.inputmethod.latin >> "${log_var}" 2>&1
    ime enable com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME >> "${log_var}" 2>&1
    ime set com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME >> "${log_var}" 2>&1
    ime disable com.qinggan.app.qgime/.QingganIME >> "${log_var}" 2>&1
    settings put secure default_input_method "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME" >> "${log_var}" 2>&1
    settings put secure selected_input_method_subtype 1891618174 >> "${log_var}" 2>&1
    settings put secure enabled_input_methods "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME:com.google.android.googlequicksearchbox/com.google.android.voicesearch.ime.VoiceInputMethodService" >> "${log_var}" 2>&1
fi
"""


def gen_inject_gboard_preset(gboard_preset_var: str = "GBOARD_PRESET", log_var: str = "LOG_FILE") -> str:
    """Injects custom Gboard profile & theme, dynamically resolves UID, and sets SELinux context."""
    return f"""if [ -d "${gboard_preset_var}" ] && [ "$(ls -A "${gboard_preset_var}" 2>/dev/null)" ]; then
    echo "Injecting custom Gboard profile & theme from ${gboard_preset_var}..." >> "${log_var}"
    GBOARD_DATA="/data/data/com.google.android.inputmethod.latin"
    am force-stop com.google.android.inputmethod.latin >/dev/null 2>&1
    sleep 0.2

    # Dynamic UID resolution
    GB_UID=$(stat -c %u "$GBOARD_DATA" 2>/dev/null)
    if [ -z "$GB_UID" ] || [ "$GB_UID" -lt 10000 ]; then
        if [ -f "/data/system/packages.list" ]; then
            GB_UID=$(grep "^com.google.android.inputmethod.latin " /data/system/packages.list 2>/dev/null | cut -d ' ' -f 2 | tr -cd '0-9')
        fi
    fi
    if [ -z "$GB_UID" ] || [ "$GB_UID" -lt 10000 ]; then
        GB_UID=$(dumpsys package com.google.android.inputmethod.latin 2>/dev/null | grep -m1 "userId=" | tr -cd '0-9')
    fi
    if [ -z "$GB_UID" ] || [ "$GB_UID" -lt 10000 ]; then
        GB_UID=$(pm list packages -U 2>/dev/null | grep "package:com.google.android.inputmethod.latin " | head -n1 | sed 's/.*uid://' | tr -cd '0-9')
    fi
    echo "Resolved Gboard UID: $GB_UID" >> "${log_var}"

    rm -f "$GBOARD_DATA/databases/"*-wal "$GBOARD_DATA/databases/"*-shm 2>/dev/null
    mkdir -p "$GBOARD_DATA" >> "${log_var}" 2>&1

    for item in "${gboard_preset_var}"/*; do
        if [ -e "$item" ]; then
            iname=$(basename "$item")
            if [ "$iname" != "lib" ] && [ "$iname" != "cache" ] && [ "$iname" != "code_cache" ]; then
                cp -rf "$item" "$GBOARD_DATA/" >> "${log_var}" 2>&1
            fi
        fi
    done

    if [ -n "$GB_UID" ] && [ "$GB_UID" -ge 10000 ]; then
        chown -R "$GB_UID:$GB_UID" "$GBOARD_DATA" >> "${log_var}" 2>&1
    else
        chown -R 1000:1000 "$GBOARD_DATA" >> "${log_var}" 2>&1
    fi
    chmod 751 "$GBOARD_DATA" >> "${log_var}" 2>&1
    chmod -R 771 "$GBOARD_DATA/databases" "$GBOARD_DATA/shared_prefs" "$GBOARD_DATA/files" "$GBOARD_DATA/no_backup" 2>/dev/null
    chmod 660 "$GBOARD_DATA/databases"/* "$GBOARD_DATA/shared_prefs"/* "$GBOARD_DATA/no_backup"/* 2>/dev/null
    restorecon -R "$GBOARD_DATA" >> "${log_var}" 2>&1
fi
"""


def gen_direct_patch_settings_xml(log_var: str = "LOG_FILE") -> str:
    """Directly persists IME & Arabic locale in settings XMLs on disk."""
    return f"""echo "Directly persisting IME & Arabic locale in settings XMLs..." >> "${log_var}"
SECURE_XML="/data/system/users/0/settings_secure.xml"
if [ -f "$SECURE_XML" ]; then
    if grep -q 'name="default_input_method"' "$SECURE_XML"; then
        sed -i 's|name="default_input_method" value="[^"]*"|name="default_input_method" value="com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME"|g' "$SECURE_XML"
    else
        sed -i 's|</settings>|  <setting id="99991" name="default_input_method" value="com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME" package="android" />\\n</settings>|' "$SECURE_XML"
    fi
    if grep -q 'name="selected_input_method_subtype"' "$SECURE_XML"; then
        sed -i 's|name="selected_input_method_subtype" value="[^"]*"|name="selected_input_method_subtype" value="1891618174"|g' "$SECURE_XML"
    else
        sed -i 's|</settings>|  <setting id="99992" name="selected_input_method_subtype" value="1891618174" package="android" />\\n</settings>|' "$SECURE_XML"
    fi
    if grep -q 'name="enabled_input_methods"' "$SECURE_XML"; then
        sed -i 's|name="enabled_input_methods" value="[^"]*"|name="enabled_input_methods" value="com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME:com.google.android.googlequicksearchbox/com.google.android.voicesearch.ime.VoiceInputMethodService"|g' "$SECURE_XML"
    fi
    chmod 600 "$SECURE_XML" >> "${log_var}" 2>&1
    chown system:system "$SECURE_XML" >> "${log_var}" 2>&1
fi

SYSTEM_XML="/data/system/users/0/settings_system.xml"
if [ -f "$SYSTEM_XML" ]; then
    if grep -q 'name="system_locales"' "$SYSTEM_XML"; then
        sed -i 's|name="system_locales" value="[^"]*"|name="system_locales" value="ar"|g' "$SYSTEM_XML"
    else
        sed -i 's|</settings>|  <setting id="99993" name="system_locales" value="ar" package="android" />\\n</settings>|' "$SYSTEM_XML"
    fi
    chmod 600 "$SYSTEM_XML" >> "${log_var}" 2>&1
    chown system:system "$SYSTEM_XML" >> "${log_var}" 2>&1
fi
"""


gen_direct_settings_xml_patch = gen_direct_patch_settings_xml


def gen_gms_compatibility_and_arabic(log_var: str = "LOG_FILE") -> str:
    """Composite helper combining Google permissions, automotive bypass, provisioning, and locale."""
    return f"""rm -f /system/etc/permissions/privapp-permissions-google.xml /system/etc/permissions/privapp-permissions-documentsui.xml >> "${log_var}" 2>&1
{gen_inject_voice_recognizers(log_var=log_var)}
{gen_inject_gservices_features(log_var=log_var)}
{gen_neutralize_automotive_flags(log_var=log_var)}
{gen_force_provisioning_flags(log_var=log_var)}
{gen_force_arabic_locale(log_var=log_var)}"""


def gen_gboard_config(gboard_preset_var: str = "GBOARD_PRESET", log_var: str = "LOG_FILE") -> str:
    """Composite helper configuring Gboard IME and injecting preset profile data."""
    return f"""{gen_configure_gboard_ime(log_var=log_var)}
{gboard_preset_var}="$USB_PATH/update/gboard_data"
{gen_inject_gboard_preset(gboard_preset_var=gboard_preset_var, log_var=log_var)}"""


def gen_restore_oem_defaults(log_var: str = "LOG_FILE") -> str:
    """
    Restores OEM default settings:
    - Removes custom permissions XML files
    - Restores factory OEM keyboard IME
    - Clears custom TTS & Voice recognition engine overrides
    - Resets provisioning & user setup flags
    """
    return f"""echo "Removing custom Google permissions and restoring OEM settings..." >> "${log_var}"
rm -f /system/etc/permissions/privapp-permissions-google.xml /system/etc/permissions/privapp-permissions-documentsui.xml >> "${log_var}" 2>&1
rm -f /system/etc/permissions/voice_recognizers.xml >> "${log_var}" 2>&1
rm -f /system/etc/permissions/gservices.xml >> "${log_var}" 2>&1

# Check current default IME: only restore OEM keyboard if current IME is Gboard/Google, missing, or pointing to an uninstalled package
CURRENT_IME=$(settings get secure default_input_method 2>/dev/null | tr -d '\\r\\n ')
CURRENT_PKG=$(echo "$CURRENT_IME" | cut -d '/' -f 1)

NEED_RESTORE=0
if [ -z "$CURRENT_IME" ] || [ "$CURRENT_IME" = "null" ]; then
    NEED_RESTORE=1
elif echo "$CURRENT_IME" | grep -qi "google"; then
    NEED_RESTORE=1
elif [ -n "$CURRENT_PKG" ] && ! pm path "$CURRENT_PKG" > /dev/null 2>&1; then
    NEED_RESTORE=1
fi

if [ "$NEED_RESTORE" -eq 1 ]; then
    OEM_IME=$(ime list -a 2>/dev/null | grep -E "qinggan|qgime|sogou|baidu|pinyin" | head -n 1 | cut -d ':' -f 2 | tr -d ' ')
    if [ -n "$OEM_IME" ]; then
        echo "Default keyboard was Google or invalid ($CURRENT_IME). Restoring factory OEM keyboard ($OEM_IME)..." >> "${log_var}"
        ime enable "$OEM_IME" >> "${log_var}" 2>&1
        ime set "$OEM_IME" >> "${log_var}" 2>&1
        settings put secure default_input_method "$OEM_IME" >> "${log_var}" 2>&1
    else
        echo "Default keyboard was Google or invalid ($CURRENT_IME). Clearing default_input_method for system fallback..." >> "${log_var}"
        settings delete secure default_input_method >> "${log_var}" 2>&1
    fi
else
    echo "Current default keyboard is preserved ($CURRENT_IME)." >> "${log_var}"
fi

# Reset TTS & Voice engine
settings delete secure tts_default_synth >> "${log_var}" 2>&1
settings delete secure tts_enabled_plugins >> "${log_var}" 2>&1
settings delete secure voice_recognition_service >> "${log_var}" 2>&1

# Reset provisioning and setup flags back to stock OEM state
echo "Resetting provisioning and setup flags to factory defaults..." >> "${log_var}"
settings put global device_provisioned 1 >> "${log_var}" 2>&1
settings put secure user_setup_complete 1 >> "${log_var}" 2>&1
"""


# ============================================================================
# SECTION 7: DIAGNOSTICS & VEHICLE HARDWARE TWEAKS (CAN-BUS)
# ============================================================================

def gen_system_snapshot(log_var: str = "LOG_FILE") -> str:
    """Generates offline car data snapshot (installed priv-apps, apps, logcat) for diagnostics."""
    return f"""echo "=== TAKING NEW SYSTEM SNAPSHOT ===" >> "${log_var}"
CAR_ID=$(getprop ro.build.display.id | tr -d ' ')
if [ -z "$CAR_ID" ]; then CAR_ID=$(getprop ro.serialno | tr -d ' '); fi
if [ -z "$CAR_ID" ]; then CAR_ID="unknown_car"; fi

DATA_DIR="$USB_PATH/DongfengData/$CAR_ID"
mkdir -p "$DATA_DIR"

echo "Extracting installed apps list..." >> "${log_var}"
ls -1 /system/priv-app > "$DATA_DIR/installed_priv.txt"
ls -1 /system/app > "$DATA_DIR/installed_app.txt"

# Copy logs to car data directory for offline archival
cp "${log_var}" "$DATA_DIR/install_log.txt" >> "${log_var}" 2>&1
logcat -d > "$DATA_DIR/car_logcat.txt" 2>&1
"""


def gen_canbus_tweaks(selected_tweaks: list, log_var: str = "LOG_FILE") -> str:
    """Generates CAN-Bus IPC wait and command execution blocks."""
    if not selected_tweaks:
        return ""

    commands_block = []
    for item in selected_tweaks:
        if isinstance(item, str):
            from core.vehicle_tweaks_data import VEHICLE_TWEAKS
            found = next((tw for tw in VEHICLE_TWEAKS if tw["id"] == item), None)
            tweak = found or {"id": item, "name_en": item, "commands_enable": [], "commands_disable": []}
            action = "enable"
        elif isinstance(item, dict):
            tweak = item.get("tweak", {})
            action = item.get("action", "enable")
        else:
            continue

        tweak_name = tweak.get("name_en", tweak.get("id", "Unknown"))
        action_label = "ENABLE" if action == "enable" else "DISABLE"

        commands_block.append(f"# Feature: {tweak_name} [{action_label}]")
        cmd_list = tweak.get("commands_enable", []) if action == "enable" else tweak.get("commands_disable", [])
        for cmd in cmd_list:
            commands_block.append(f"echo \"Sending: {tweak_name} -> {action_label}...\" >> \"${log_var}\"")
            commands_block.append(cmd)
            commands_block.append("sleep 1")
        commands_block.append("")

    commands_text = "\n".join(commands_block)

    return f"""# Wait for qg.canbus service to be ready
RETRY_COUNT=0
while [ $RETRY_COUNT -lt 15 ]; do
    SERVICE_CHECK=$(service check qg.canbus)
    case "$SERVICE_CHECK" in
        *found*)
            echo "qg.canbus service verified active." >> "${log_var}"
            break
            ;;
        *)
            echo "Waiting for qg.canbus service..." >> "${log_var}"
            sleep 1
            RETRY_COUNT=$((RETRY_COUNT + 1))
            ;;
    esac
done

echo "Executing user-selected vehicle CAN-Bus configurations..." >> "${log_var}"
{commands_text}
"""


# ============================================================================
# SECTION 8: BACKUP & RESTORE ATOMIC BUILDING BLOCKS (SRP)
# ============================================================================

def gen_backup_system_settings(target_dir_var: str = "TARGET_DIR", b_type: str = "PERSONAL", log_var: str = "LOG_FILE") -> str:
    """Captures runtime permissions, package restrictions, appops, widgets, and explicit settings."""
    snippet = f"""echo "1. Backing up system settings and configurations..." >> "${log_var}"
mkdir -p "${target_dir_var}/settings" "${target_dir_var}/property" >> "${log_var}" 2>&1
cp -f /data/system/users/0/package-restrictions.xml "${target_dir_var}/settings/" >> "${log_var}" 2>&1
cp -f /data/system/users/0/runtime-permissions.xml "${target_dir_var}/settings/" >> "${log_var}" 2>&1
cp -f /data/system/appops.xml "${target_dir_var}/settings/" >> "${log_var}" 2>&1
cp -f /data/system/users/0/settings_*.xml "${target_dir_var}/settings/" >> "${log_var}" 2>&1
cp -f /data/system/users/0/appwidgets.xml "${target_dir_var}/settings/" >> "${log_var}" 2>&1
cp -f /data/system/appwidgets.xml "${target_dir_var}/settings/" >> "${log_var}" 2>&1
cp -f /system/etc/permissions/voice_recognizers.xml "${target_dir_var}/settings/" >> "${log_var}" 2>&1
cp -f /system/build.prop "${target_dir_var}/settings/" >> "${log_var}" 2>&1

EXPLICIT_SETTINGS="${target_dir_var}/settings/explicit_settings.sh"
echo "#!/system/bin/sh" > "$EXPLICIT_SETTINGS"

FONT=$(settings get system font_scale 2>/dev/null)
[ -n "$FONT" ] && [ "$FONT" != "null" ] && echo "settings put system font_scale '$FONT' >> \\\"\\${log_var}\\\" 2>&1" >> "$EXPLICIT_SETTINGS"

TIME_12_24=$(settings get system time_12_24 2>/dev/null)
[ -n "$TIME_12_24" ] && [ "$TIME_12_24" != "null" ] && echo "settings put system time_12_24 '$TIME_12_24' >> \\\"\\${log_var}\\\" 2>&1" >> "$EXPLICIT_SETTINGS"

TZ=$(getprop persist.sys.timezone 2>/dev/null)
[ -n "$TZ" ] && echo "setprop persist.sys.timezone '$TZ' >> \\\"\\${log_var}\\\" 2>&1" >> "$EXPLICIT_SETTINGS"

LOCALE=$(getprop persist.sys.locale 2>/dev/null)
[ -n "$LOCALE" ] && echo "setprop persist.sys.locale '$LOCALE' >> \\\"\\${log_var}\\\" 2>&1" >> "$EXPLICIT_SETTINGS"

IME=$(settings get secure default_input_method 2>/dev/null)
[ -n "$IME" ] && [ "$IME" != "null" ] && echo "settings put secure default_input_method '$IME' >> \\\"\\${log_var}\\\" 2>&1" >> "$EXPLICIT_SETTINGS"
[ -n "$IME" ] && [ "$IME" != "null" ] && echo "ime enable $IME >> \\\"\\${log_var}\\\" 2>&1" >> "$EXPLICIT_SETTINGS"
[ -n "$IME" ] && [ "$IME" != "null" ] && echo "ime set $IME >> \\\"\\${log_var}\\\" 2>&1" >> "$EXPLICIT_SETTINGS"
EN_IMES=$(settings get secure enabled_input_methods 2>/dev/null)
[ -n "$EN_IMES" ] && [ "$EN_IMES" != "null" ] && echo "settings put secure enabled_input_methods '$EN_IMES' >> \\\"\\${log_var}\\\" 2>&1" >> "$EXPLICIT_SETTINGS"
chmod 755 "$EXPLICIT_SETTINGS" >> "${log_var}" 2>&1

cmd package resolve-activity --brief -c android.intent.category.HOME -a android.intent.action.MAIN 2>/dev/null | tail -n 1 > "${target_dir_var}/settings/default_launcher.txt" 2>/dev/null
if pm list packages -d 2>/dev/null | grep -q "com.qinggan.app.launcher"; then
    echo "FROZEN" > "${target_dir_var}/settings/oem_launcher_state.txt"
fi

if [ -d "/data/property" ]; then
    cp -r /data/property/* "${target_dir_var}/property/" >> "${log_var}" 2>&1
fi
"""
    if b_type.upper() == "PERSONAL":
        snippet += f"""cp -f /data/system/locksettings.db* "${target_dir_var}/settings/" >> "${log_var}" 2>&1
"""
    return snippet


def gen_backup_custom_system_apps(
    target_dir_var: str = "TARGET_DIR",
    priv_whitelist: list = None,
    app_whitelist: list = None,
    log_var: str = "LOG_FILE"
) -> str:
    """Extracts non-whitelisted custom System Priv-Apps and Apps to USB."""
    priv_wl = " ".join(priv_whitelist or FACTORY_PRIV_APPS)
    app_wl = " ".join(app_whitelist or FACTORY_APPS)
    return f"""echo "2. Backing up custom system applications..." >> "${log_var}"
mkdir -p "${target_dir_var}/system_apps/priv-app" "${target_dir_var}/system_apps/app" >> "${log_var}" 2>&1
PRIV_WL="{priv_wl}"
APP_WL="{app_wl}"

for dir in /system/priv-app/*; do
    if [ -d "$dir" ]; then
        name=$(basename "$dir")
        is_factory=false
        for fw in $PRIV_WL; do
            if [ "$name" = "$fw" ]; then is_factory=true; break; fi
        done
        if [ "$is_factory" = "false" ]; then
            cp -r "$dir" "${target_dir_var}/system_apps/priv-app/" >> "${log_var}" 2>&1
        fi
    fi
done

for dir in /system/app/*; do
    if [ -d "$dir" ]; then
        name=$(basename "$dir")
        is_factory=false
        for fw in $APP_WL; do
            if [ "$name" = "$fw" ]; then is_factory=true; break; fi
        done
        if [ "$is_factory" = "false" ]; then
            cp -r "$dir" "${target_dir_var}/system_apps/app/" >> "${log_var}" 2>&1
        fi
    fi
done
"""


def gen_backup_user_apks(target_dir_var: str = "TARGET_DIR", log_var: str = "LOG_FILE") -> str:
    """Backs up third-party User APKs from /data/app."""
    return f"""echo "3. Backing up User Applications (/data/app)..." >> "${log_var}"
mkdir -p "${target_dir_var}/data_apps" >> "${log_var}" 2>&1
if [ -d "/data/app" ]; then
    for uapp in /data/app/*; do
        if [ -e "$uapp" ]; then
            cp -r "$uapp" "${target_dir_var}/data_apps/" >> "${log_var}" 2>&1
        fi
    done
fi
"""


def gen_backup_app_data(target_dir_var: str = "TARGET_DIR", b_type: str = "PERSONAL", log_var: str = "LOG_FILE") -> str:
    """Backs up app data (/data/data, /data/user_de) and handles Community vs Personal filtering."""
    snippet = f"""echo "4. Backing up application data & preferences..." >> "${log_var}"
mkdir -p "${target_dir_var}/data_data" >> "${log_var}" 2>&1

if [ -f "/data/system/packages.list" ]; then
    cp -f /data/system/packages.list "${target_dir_var}/packages.list" >> "${log_var}" 2>&1
fi

for qg_dir in /data/data/com.android.settings /data/data/com.android.providers.settings /data/data/com.android.providers.userdictionary /data/data/com.qinggan.* /data/data/com.pateo.CarPlay.*; do
    if [ -d "$qg_dir" ]; then
        cp -r "$qg_dir" "${target_dir_var}/data_data/" >> "${log_var}" 2>&1
    fi
done

if [ -d "/data/user_de/0" ]; then
    mkdir -p "${target_dir_var}/user_de" >> "${log_var}" 2>&1
    for de_dir in /data/user_de/0/com.qinggan.* /data/user_de/0/com.android.providers.settings /data/user_de/0/com.android.providers.userdictionary /data/user_de/0/com.android.settings; do
        if [ -d "$de_dir" ]; then
            cp -r "$de_dir" "${target_dir_var}/user_de/" >> "${log_var}" 2>&1
        fi
    done
fi

# Backup data for User Apps
if [ -d "/data/app" ]; then
    for uapp in /data/app/*; do
        if [ -e "$uapp" ]; then
            u_bname=$(basename "$uapp")
            clean_pkg=$(echo "$u_bname" | cut -d'-' -f1)
            if [ -d "/data/data/$clean_pkg" ] && [ ! -d "${target_dir_var}/data_data/$clean_pkg" ]; then
                cp -r "/data/data/$clean_pkg" "${target_dir_var}/data_data/" >> "${log_var}" 2>&1
            fi
        fi
    done
fi

# Backup data for custom launchers and modded tools
for c_pkg in altergames.carlauncher org.smarttube.stable com.vialsoft.radarbot_free com.nst.iptvsmarterstvbox com.Hydraprimeonline nu.nav.bar com.farmerbb.taskbar; do
    if [ -d "/data/data/$c_pkg" ] && [ ! -d "${target_dir_var}/data_data/$c_pkg" ]; then
        cp -r "/data/data/$c_pkg" "${target_dir_var}/data_data/" >> "${log_var}" 2>&1
    fi
done
"""
    if b_type.upper() == "PERSONAL":
        snippet += f"""mkdir -p "${target_dir_var}/accounts" "${target_dir_var}/keystore" >> "${log_var}" 2>&1
cp -f /data/system/users/0/accounts.db* "${target_dir_var}/accounts/" >> "${log_var}" 2>&1
cp -f /data/system_de/0/accounts_de.db* "${target_dir_var}/accounts/" >> "${log_var}" 2>&1
if [ -d "/data/misc/keystore" ]; then cp -r /data/misc/keystore/* "${target_dir_var}/keystore/" >> "${log_var}" 2>&1; fi
if [ -d "/data/system/sync" ]; then
    mkdir -p "${target_dir_var}/accounts/sync" >> "${log_var}" 2>&1
    cp -r /data/system/sync/* "${target_dir_var}/accounts/sync/" >> "${log_var}" 2>&1
fi
for gms_dir in /data/data/com.google.* /data/data/com.android.vending; do
    if [ -d "$gms_dir" ]; then cp -r "$gms_dir" "${target_dir_var}/data_data/" >> "${log_var}" 2>&1; fi
done
if [ -d "/data/data/com.android.bluetooth" ]; then cp -r /data/data/com.android.bluetooth "${target_dir_var}/data_data/" >> "${log_var}" 2>&1; fi
"""
    else:
        snippet += f"""echo "Community Mode: Scrubbing private accounts and authentication tokens..." >> "${log_var}"
rm -rf "${target_dir_var}/data_data/com.google."* "${target_dir_var}/data_data/com.android.vending" 2>/dev/null
"""
    return snippet


def gen_backup_connectivity(target_dir_var: str = "TARGET_DIR", b_type: str = "PERSONAL", log_var: str = "LOG_FILE") -> str:
    """Backs up Wi-Fi and Bluetooth configuration in Personal mode; skips in Community mode."""
    if b_type.upper() != "PERSONAL":
        return f"""echo "Community Mode: Wi-Fi networks and Bluetooth pairings skipped." >> "${log_var}"
"""
    return f"""echo "5. Backing up Wi-Fi networks & Bluetooth pairings..." >> "${log_var}"
mkdir -p "${target_dir_var}/wifi_bt/wifi" "${target_dir_var}/wifi_bt/bluedroid" "${target_dir_var}/wifi_bt/bluetooth" "${target_dir_var}/wifi_bt/vendor_bt" "${target_dir_var}/wifi_bt/adb" >> "${log_var}" 2>&1
if [ -d "/data/misc/wifi" ]; then cp -r /data/misc/wifi/* "${target_dir_var}/wifi_bt/wifi/" >> "${log_var}" 2>&1; fi
if [ -d "/data/misc/dhcp" ]; then cp -r /data/misc/dhcp/* "${target_dir_var}/wifi_bt/wifi/" >> "${log_var}" 2>&1; fi
if [ -d "/data/misc/bluedroid" ]; then cp -r /data/misc/bluedroid/* "${target_dir_var}/wifi_bt/bluedroid/" >> "${log_var}" 2>&1; fi
if [ -d "/data/misc/bluetooth" ]; then cp -r /data/misc/bluetooth/* "${target_dir_var}/wifi_bt/bluetooth/" >> "${log_var}" 2>&1; fi
if [ -d "/data/vendor/bluetooth" ]; then cp -r /data/vendor/bluetooth/* "${target_dir_var}/wifi_bt/vendor_bt/" >> "${log_var}" 2>&1; fi
if [ -d "/data/misc/adb" ]; then cp -r /data/misc/adb/* "${target_dir_var}/wifi_bt/adb/" >> "${log_var}" 2>&1; fi
"""


def gen_backup_user_media(target_dir_var: str = "TARGET_DIR", inc_media: bool = False, log_var: str = "LOG_FILE") -> str:
    """Backs up user media (/sdcard) if enabled."""
    if not inc_media:
        return f"""echo "User Media disabled: Skipping /sdcard backup." >> "${log_var}"
"""
    return f"""echo "6. Backing up user media files (/sdcard)..." >> "${log_var}"
mkdir -p "${target_dir_var}/sdcard" >> "${log_var}" 2>&1
SD_SRC="/data/media/0"
if [ ! -d "$SD_SRC" ] || [ -z "$(ls -A "$SD_SRC" 2>/dev/null)" ]; then
    if [ -d "/sdcard" ]; then SD_SRC="/sdcard"; fi
fi

for item in "$SD_SRC"/*; do
    if [ -e "$item" ]; then
        bname=$(basename "$item")
        if [ "$bname" = "Android" ]; then
            mkdir -p "${target_dir_var}/sdcard/Android" >> "${log_var}" 2>&1
            for a_item in "$item"/*; do
                if [ "$(basename "$a_item")" != "data" ] && [ -e "$a_item" ]; then
                    cp -r "$a_item" "${target_dir_var}/sdcard/Android/" >> "${log_var}" 2>&1
                fi
            done
        else
            cp -r "$item" "${target_dir_var}/sdcard/" >> "${log_var}" 2>&1
        fi
    fi
done
"""


def gen_backup_init(target_dir_var: str = "TARGET_DIR", b_type: str = "PERSONAL", inc_media: bool = False, log_var: str = "LOG_FILE") -> str:
    """Initializes backup variables, creates target folder, and resets completion flag."""
    inc_m_str = "1" if inc_media else "0"
    return f"""CAR_MODEL=$(getprop ro.product.model)
BUILD_ID=$(getprop ro.build.display.id)
echo "Model: $CAR_MODEL" >> "${log_var}"
echo "Build: $BUILD_ID" >> "${log_var}"
echo "Backup Type: {b_type.upper()}" >> "${log_var}"
echo "Include Media: {inc_m_str}" >> "${log_var}"

{target_dir_var}="$USB_PATH/Backup"
rm -rf "${target_dir_var}" >> "${log_var}" 2>&1
mkdir -p "${target_dir_var}" >> "${log_var}" 2>&1
rm -f "$USB_PATH/backup_complete.flag" >> "${log_var}" 2>&1

BACKUP_FAILED=0
"""


def gen_backup_manifest_and_flags(
    target_dir_var: str = "TARGET_DIR",
    b_type: str = "PERSONAL",
    preset_name: str = "",
    author: str = "",
    inc_media: bool = False,
    log_var: str = "LOG_FILE",
    is_composite: bool = False
) -> str:
    """Saves full package names, generates Backup_Manifest.txt, and writes backup_complete.flag."""
    p_name_sh = (preset_name or "").replace('"', '\\"').replace("'", "")
    author_sh = (author or "").replace('"', '\\"').replace("'", "")
    inc_m_str = "1" if inc_media else "0"
    b_type_sh = b_type.upper()

    final_touch = 'touch "$STATE_DIR/stage_backup.done"' if is_composite else '''mkdir -p "$USB_PATH/completed_cars/${CAR_SERIAL}" 2>/dev/null
touch "$USB_PATH/completed_cars/${CAR_SERIAL}/completed.done"
touch "$USB_PATH/completed_cars/${CAR_SERIAL}.done"
echo "[$(date \'+%Y-%m-%d %H:%M:%S\')] MODEL: $CAR_MODEL | SERIAL: $CAR_SERIAL | STATUS: BACKUP_COMPLETE" >> "$USB_PATH/completed_cars/registry.txt"
sync'''

    return f"""# Save full package list with paths for accurate pkg_name resolution during restore
echo "Saving full package list for restore pkg_name resolution..." >> "${log_var}"
pm list packages -f > "${target_dir_var}/packages_full.txt" 2>/dev/null
pm list packages > "${target_dir_var}/packages_names.txt" 2>/dev/null

# Generate Comprehensive Backup Manifest & Restoration Strategy Checklist
MANIFEST_FILE="${target_dir_var}/Backup_Manifest.txt"
echo "==========================================================" > "$MANIFEST_FILE"
echo "📋 AERO SUITE v2.0 — BACKUP MANIFEST & STRATEGY CHECKLIST" >> "$MANIFEST_FILE"
echo "==========================================================" >> "$MANIFEST_FILE"
echo "Backup Date:    $(date)" >> "$MANIFEST_FILE"
echo "Vehicle Model:  $CAR_MODEL" >> "$MANIFEST_FILE"
echo "ROM Build ID:   $BUILD_ID" >> "$MANIFEST_FILE"
echo "Backup Type:    {b_type_sh}" >> "$MANIFEST_FILE"
echo "Preset Name:    {p_name_sh}" >> "$MANIFEST_FILE"
echo "Author:         {author_sh}" >> "$MANIFEST_FILE"
echo "Include Media:  {inc_m_str}" >> "$MANIFEST_FILE"
echo "" >> "$MANIFEST_FILE"
echo "── 1. Captured User Applications (/data/app) ──" >> "$MANIFEST_FILE"
if [ -d "${target_dir_var}/data_apps" ]; then
    for u in "${target_dir_var}/data_apps/"*; do
        if [ -e "$u" ]; then echo "  [App] $(basename "$u")" >> "$MANIFEST_FILE"; fi
    done
fi
echo "" >> "$MANIFEST_FILE"
echo "── 2. Captured Custom System Apps (/system/priv-app & app) ──" >> "$MANIFEST_FILE"
if [ -d "${target_dir_var}/system_apps/priv-app" ]; then
    for s in "${target_dir_var}/system_apps/priv-app/"*; do
        if [ -d "$s" ]; then echo "  [Priv-App] $(basename "$s")" >> "$MANIFEST_FILE"; fi
    done
fi
if [ -d "${target_dir_var}/system_apps/app" ]; then
    for s in "${target_dir_var}/system_apps/app/"*; do
        if [ -d "$s" ]; then echo "  [System-App] $(basename "$s")" >> "$MANIFEST_FILE"; fi
    done
fi
echo "" >> "$MANIFEST_FILE"
echo "── 3. Launcher & UI Configuration ──" >> "$MANIFEST_FILE"
if [ -f "${target_dir_var}/settings/default_launcher.txt" ]; then
    echo "  Default Launcher: $(cat "${target_dir_var}/settings/default_launcher.txt")" >> "$MANIFEST_FILE"
fi
if [ -f "${target_dir_var}/settings/oem_launcher_state.txt" ]; then
    echo "  Stock OEM Launcher: FROZEN (Will be re-frozen on restore)" >> "$MANIFEST_FILE"
else
    echo "  Stock OEM Launcher: ACTIVE" >> "$MANIFEST_FILE"
fi
echo "" >> "$MANIFEST_FILE"
echo "── 4. Google Services & Keystore ──" >> "$MANIFEST_FILE"
if [ -d "${target_dir_var}/keystore" ] && [ -n "$(ls -A "${target_dir_var}/keystore" 2>/dev/null)" ]; then
    echo "  Keystore: Master keys archived (1:1 Auth Token Preservation)" >> "$MANIFEST_FILE"
else
    echo "  Keystore: Not present" >> "$MANIFEST_FILE"
fi
if [ -f "${target_dir_var}/accounts/accounts.db" ]; then
    echo "  Accounts DB: Google & System account database archived" >> "$MANIFEST_FILE"
fi
echo "==========================================================" >> "$MANIFEST_FILE"

sync
if [ "$BACKUP_FAILED" -eq 0 ]; then
    echo "BACKUP_DATE=$(date)" > "$USB_PATH/backup_complete.flag"
    echo "DEVICE_MODEL=$CAR_MODEL" >> "$USB_PATH/backup_complete.flag"
    echo "BUILD_ID=$BUILD_ID" >> "$USB_PATH/backup_complete.flag"
    echo "BACKUP_TYPE={b_type_sh}" >> "$USB_PATH/backup_complete.flag"
    echo "PRESET_NAME={p_name_sh}" >> "$USB_PATH/backup_complete.flag"
    echo "AUTHOR={author_sh}" >> "$USB_PATH/backup_complete.flag"
    echo "INCLUDE_MEDIA={inc_m_str}" >> "$USB_PATH/backup_complete.flag"
    echo "STATUS=SUCCESS" >> "$USB_PATH/backup_complete.flag"
    echo "=== AERO BACKUP STAGE STATUS: SUCCESS ===" >> "${log_var}"
    date >> "${log_var}"
    {final_touch}
    sync
else
    echo "=== AERO BACKUP STAGE STATUS: FAILED ===" >> "${log_var}"
    date >> "${log_var}"
    {final_touch}
    sync
fi
sync
"""


# ============================================================================
# SECTION 9: RESTORATION ATOMIC GENERATORS (SRP)
# ============================================================================

def gen_restore_header_check(log_var: str = "LOG_FILE") -> str:
    """Verifies restore_ready.flag and locates Backup directory on USB."""
    return f"""# Sanity Check: Verify restore_ready.flag
if [ ! -f "$USB_PATH/restore_ready.flag" ]; then
    echo "ABORT: restore_ready.flag not found! This USB was not prepared correctly." >> "${log_var}"
    exit 1
fi

TARGET_DIR="$USB_PATH/Backup"
if [ ! -d "$TARGET_DIR" ]; then
    TARGET_DIR="$USB_PATH/PersonalBackup"
fi

if [ ! -d "$TARGET_DIR" ]; then
    echo "ABORT: No valid Backup folder found on USB!" >> "${log_var}"
    exit 1
fi

echo "Restore package verified. Starting 12-step restoration..." >> "${log_var}"
"""


def gen_restore_pkg_resolver(target_dir_var: str = "TARGET_DIR") -> str:
    """Generates shell resolve_pkg_name function for dynamic package name resolution."""
    return f"""# Helper: resolve package name from data_apps folder name with multi-strategy fallback
resolve_pkg_name() {{
    local fn="$1"
    local pkg=""
    if pm path "$fn" > /dev/null 2>&1; then echo "$fn"; return; fi
    if [ -f "${target_dir_var}/packages_full.txt" ]; then
        pkg=$(grep "=$fn" "${target_dir_var}/packages_full.txt" 2>/dev/null | head -n1 | sed 's|.*package:||;s|=.*||')
        if [ -n "$pkg" ] && pm path "$pkg" > /dev/null 2>&1; then echo "$pkg"; return; fi
    fi
    pkg=$(echo "$fn" | sed 's/-[A-Za-z0-9_=+/]*$//')
    if [ -n "$pkg" ] && pm path "$pkg" > /dev/null 2>&1; then echo "$pkg"; return; fi
    pkg=$(echo "$fn" | sed 's/-[0-9].*//')
    echo "$pkg"
}}
"""


def gen_restore_custom_system_apps(target_dir_var: str = "TARGET_DIR", log_var: str = "LOG_FILE") -> str:
    """Restores custom Priv-Apps and System Apps with proper permissions and native libraries."""
    return f"""echo "2/12 Restoring Custom System Apps..." >> "${log_var}"
if [ -d "${target_dir_var}/system_apps/priv-app" ]; then
    for dir in "${target_dir_var}/system_apps/priv-app/"*; do
        if [ -d "$dir" ]; then
            bname=$(basename "$dir")
            echo "Restoring Priv-App: $bname..." >> "${log_var}"
            mkdir -p "/system/priv-app/$bname" >> "${log_var}" 2>&1
            cp -r "$dir/." "/system/priv-app/$bname/" >> "${log_var}" 2>&1
            chmod 755 "/system/priv-app/$bname" >> "${log_var}" 2>&1
            chmod 644 "/system/priv-app/$bname"/*.apk >> "${log_var}" 2>&1
            if [ -d "/system/priv-app/$bname/lib" ]; then
                chmod -R 755 "/system/priv-app/$bname/lib" >> "${log_var}" 2>&1
                chmod 644 "/system/priv-app/$bname/lib/arm"/*.so >> "${log_var}" 2>&1
            fi
        fi
    done
fi
if [ -d "${target_dir_var}/system_apps/app" ]; then
    for dir in "${target_dir_var}/system_apps/app/"*; do
        if [ -d "$dir" ]; then
            bname=$(basename "$dir")
            echo "Restoring System App: $bname..." >> "${log_var}"
            mkdir -p "/system/app/$bname" >> "${log_var}" 2>&1
            cp -r "$dir/." "/system/app/$bname/" >> "${log_var}" 2>&1
            chmod 755 "/system/app/$bname" >> "${log_var}" 2>&1
            chmod 644 "/system/app/$bname"/*.apk >> "${log_var}" 2>&1
            if [ -d "/system/app/$bname/lib" ]; then
                chmod -R 755 "/system/app/$bname/lib" >> "${log_var}" 2>&1
                chmod 644 "/system/app/$bname/lib/arm"/*.so >> "${log_var}" 2>&1
            fi
        fi
    done
fi
"""


def gen_restore_voice_and_keystore(target_dir_var: str = "TARGET_DIR", log_var: str = "LOG_FILE") -> str:
    """Restores voice recognizers feature XML and Keystore master keys."""
    return f"""echo "3/12 Restoring Voice Recognizers & Keystore..." >> "${log_var}"
if [ -f "${target_dir_var}/settings/voice_recognizers.xml" ]; then
    cp -f "${target_dir_var}/settings/voice_recognizers.xml" /system/etc/permissions/ >> "${log_var}" 2>&1
    chmod 644 /system/etc/permissions/voice_recognizers.xml >> "${log_var}" 2>&1
fi
if [ -d "${target_dir_var}/keystore" ] && pm path com.google.android.gms > /dev/null 2>&1; then
    echo "GMS detected — Restoring Android Keystore Master Keys..." >> "${log_var}"
    mkdir -p /data/misc/keystore >> "${log_var}" 2>&1
    cp -r "${target_dir_var}/keystore/"* /data/misc/keystore/ >> "${log_var}" 2>&1
    chown -R keystore:keystore /data/misc/keystore >> "${log_var}" 2>&1
    chmod 700 /data/misc/keystore >> "${log_var}" 2>&1
else
    echo "Keystore restore skipped (no GMS or no keystore in backup)." >> "${log_var}"
fi
"""


def gen_restore_accounts(target_dir_var: str = "TARGET_DIR", log_var: str = "LOG_FILE") -> str:
    """Restores Google accounts database or cleans target tokens in Community mode."""
    return f"""echo "4/12 Restoring Accounts..." >> "${log_var}"
if [ -f "${target_dir_var}/accounts/accounts.db" ]; then
    mkdir -p /data/system/users/0 /data/system_de/0 >> "${log_var}" 2>&1
    cp -f "${target_dir_var}/accounts/accounts.db"* /data/system/users/0/ >> "${log_var}" 2>&1
    cp -f "${target_dir_var}/accounts/accounts_de.db"* /data/system_de/0/ >> "${log_var}" 2>&1
    if [ -d "${target_dir_var}/accounts/sync" ]; then
        mkdir -p /data/system/sync >> "${log_var}" 2>&1
        cp -r "${target_dir_var}/accounts/sync/"* /data/system/sync/ >> "${log_var}" 2>&1
    fi
    chmod 600 /data/system/users/0/accounts.db* /data/system_de/0/accounts_de.db* >> "${log_var}" 2>&1
    chown system:system /data/system/users/0/accounts.db* /data/system_de/0/accounts_de.db* >> "${log_var}" 2>&1
else
    echo "Community / No Accounts in backup: Preserving target vehicle accounts." >> "${log_var}"
    if [ -d "${target_dir_var}/system_apps/priv-app/GoogleServicesFramework" ] || [ -d "${target_dir_var}/system_apps/priv-app/GMS" ]; then
        echo "Community GMS detected — resetting target screen GMS caches to guarantee zero-conflict login..." >> "${log_var}"
        pm clear com.google.android.gms > /dev/null 2>&1
        pm clear com.android.vending > /dev/null 2>&1
        pm clear com.google.android.gsf > /dev/null 2>&1
    fi
fi
"""


def gen_restore_properties_and_flags(target_dir_var: str = "TARGET_DIR", log_var: str = "LOG_FILE") -> str:
    """Restores provisioning flags and persistent system properties."""
    return f"""echo "5/12 Restoring Properties & Setup Flags..." >> "${log_var}"
settings put global device_provisioned 1 >> "${log_var}" 2>&1
settings put secure user_setup_complete 1 >> "${log_var}" 2>&1
if [ -d "${target_dir_var}/property" ]; then
    mkdir -p /data/property >> "${log_var}" 2>&1
    cp -r "${target_dir_var}/property/"* /data/property/ >> "${log_var}" 2>&1
    chmod 600 /data/property/* >> "${log_var}" 2>&1
    chown root:root /data/property/* >> "${log_var}" 2>&1
    for propfile in "${target_dir_var}/property/"*; do
        if [ -f "$propfile" ]; then
            p_name=$(basename "$propfile")
            p_val=$(cat "$propfile" 2>/dev/null)
            [ -n "$p_val" ] && setprop "$p_name" "$p_val" >> "${log_var}" 2>&1
        fi
    done
fi
"""


def gen_restore_settings_xml(target_dir_var: str = "TARGET_DIR", log_var: str = "LOG_FILE") -> str:
    """Restores settings XMLs, runtime permissions, appops, and appwidgets."""
    return f"""echo "6/12 Restoring Settings XMLs & Runtime Permissions..." >> "${log_var}"
cp -f "${target_dir_var}/settings/settings_"*.xml /data/system/users/0/ >> "${log_var}" 2>&1
cp -f "${target_dir_var}/settings/runtime-permissions.xml" /data/system/users/0/ >> "${log_var}" 2>&1
cp -f "${target_dir_var}/settings/appops.xml" /data/system/ >> "${log_var}" 2>&1
if [ -f "${target_dir_var}/settings/appwidgets.xml" ]; then
    cp -f "${target_dir_var}/settings/appwidgets.xml" /data/system/users/0/ >> "${log_var}" 2>&1
    cp -f "${target_dir_var}/settings/appwidgets.xml" /data/system/ >> "${log_var}" 2>&1
fi
chmod 600 /data/system/users/0/settings_*.xml \\
          /data/system/users/0/runtime-permissions.xml \\
          /data/system/appops.xml \\
          /data/system/users/0/appwidgets.xml \\
          /data/system/appwidgets.xml 2>/dev/null >> "${log_var}" 2>&1
chown system:system /data/system/users/0/settings_*.xml \\
                    /data/system/users/0/runtime-permissions.xml \\
                    /data/system/appops.xml \\
                    /data/system/users/0/appwidgets.xml \\
                    /data/system/appwidgets.xml 2>/dev/null >> "${log_var}" 2>&1
"""


def gen_restore_package_restrictions(target_dir_var: str = "TARGET_DIR", log_var: str = "LOG_FILE") -> str:
    """Restores package restrictions before user app installation to preserve freeze states."""
    return f"""echo "7/12 Restoring Package Restrictions (Launcher State)..." >> "${log_var}"
if [ -f "${target_dir_var}/settings/package-restrictions.xml" ]; then
    cp -f "${target_dir_var}/settings/package-restrictions.xml" /data/system/users/0/ >> "${log_var}" 2>&1
    chmod 600 /data/system/users/0/package-restrictions.xml >> "${log_var}" 2>&1
    chown system:system /data/system/users/0/package-restrictions.xml >> "${log_var}" 2>&1
fi
"""


def gen_restore_user_apps(target_dir_var: str = "TARGET_DIR", log_var: str = "LOG_FILE") -> str:
    """Installs User Apps (/data/app) using session/flat PM installs with OEM bypass."""
    return f"""echo "8/12 Installing User Apps to /data/app..." >> "${log_var}"
echo "Unlocking OEM sideload policies..." >> "${log_var}"
setprop persist.ais_server.3app.perm 1 >> "${log_var}" 2>&1
settings put global install_non_market_apps 1 >> "${log_var}" 2>&1
settings put secure install_non_market_apps 1 >> "${log_var}" 2>&1
settings put system install_non_market_apps 1 >> "${log_var}" 2>&1
settings put global package_verifier_enable 0 >> "${log_var}" 2>&1
settings put global package_verifier_user_consent -1 >> "${log_var}" 2>&1
settings put global verifier_verify_adb_installs 0 >> "${log_var}" 2>&1

echo "Cleaning stale user apps from /system/app..." >> "${log_var}"
for u_check in "${target_dir_var}/data_apps/"*; do
    if [ -d "$u_check" ]; then
        u_bname=$(basename "$u_check")
        rm -rf "/system/app/$u_bname" >> "${log_var}" 2>&1
    elif [ -f "$u_check" ] && [ "${{u_check##*.}}" = "apk" ]; then
        u_fname=$(basename "$u_check")
        u_bname="${{u_fname%.*}}"
        rm -rf "/system/app/$u_bname" "/system/app/$u_fname" >> "${log_var}" 2>&1
    fi
done

if [ -d "${target_dir_var}/data_apps" ]; then
    STAGE_DIR="/data/local/tmp/user_restore_stage"
    for appdir in "${target_dir_var}/data_apps/"*; do
        if [ -d "$appdir" ]; then
            app_bname=$(basename "$appdir")
            pkg_name=$(resolve_pkg_name "$app_bname")

            if [ -n "$pkg_name" ] && pm path "$pkg_name" > /dev/null 2>&1; then
                echo "already installed $pkg_name, skipping install..." >> "${log_var}"
                pm enable "$pkg_name" >> "${log_var}" 2>&1
                continue
            fi

            echo "Installing: $app_bname (pkg=$pkg_name)..." >> "${log_var}"
            rm -rf "$STAGE_DIR" && mkdir -p "$STAGE_DIR"
            cp "$appdir"/*.apk "$STAGE_DIR/" >> "${log_var}" 2>&1
            chmod 644 "$STAGE_DIR"/*.apk >> "${log_var}" 2>&1

            total_bytes=0
            for a in "$STAGE_DIR"/*.apk; do
                sz=$(stat -c%s "$a" 2>/dev/null || wc -c < "$a")
                total_bytes=$((total_bytes + sz))
            done

            installed=false
            sess_id=$(pm install-create -i com.android.packageinstaller -r -g -S $total_bytes 2>&1 | tr -cd '0-9')
            [ -z "$sess_id" ] && sess_id=$(pm install-create -i com.android.vending -r -g -S $total_bytes 2>&1 | tr -cd '0-9')
            [ -z "$sess_id" ] && sess_id=$(pm install-create -r -g -S $total_bytes 2>&1 | tr -cd '0-9')

            if [ -n "$sess_id" ]; then
                for a in "$STAGE_DIR"/*.apk; do
                    b_name=$(basename "$a" .apk)
                    sz=$(stat -c%s "$a" 2>/dev/null || wc -c < "$a")
                    pm install-write -S $sz $sess_id "$b_name" "$a" >> "${log_var}" 2>&1
                done
                commit_res=$(pm install-commit $sess_id 2>&1)
                echo "commit: $commit_res" >> "${log_var}"
                if echo "$commit_res" | grep -qi "Success"; then
                    installed=true
                else
                    pm install-abandon $sess_id > /dev/null 2>&1
                fi
            fi

            if [ "$installed" = false ]; then
                target_apk=$(ls -1 "$STAGE_DIR"/*.apk 2>/dev/null | head -n 1)
                [ -f "$STAGE_DIR/base.apk" ] && target_apk="$STAGE_DIR/base.apk"
                if [ -f "$target_apk" ]; then
                    for installer in com.android.packageinstaller com.android.vending ""; do
                        if [ -n "$installer" ]; then
                            inst_res=$(pm install -i "$installer" -r "$target_apk" 2>&1)
                        else
                            inst_res=$(pm install -r "$target_apk" 2>&1)
                        fi
                        echo "$inst_res" >> "${log_var}"
                        if echo "$inst_res" | grep -qi "Success"; then installed=true; break; fi
                    done
                fi
            fi

            if [ "$installed" = false ]; then
                target_apk=$(ls -1 "$STAGE_DIR"/*.apk 2>/dev/null | head -n 1)
                [ -f "$STAGE_DIR/base.apk" ] && target_apk="$STAGE_DIR/base.apk"
                if [ -f "$target_apk" ]; then
                    cmd_res=$(cmd package install -i com.android.packageinstaller -r "$target_apk" 2>&1)
                    echo "cmd: $cmd_res" >> "${log_var}"
                    echo "$cmd_res" | grep -qi "Success" && installed=true
                fi
            fi

            if [ "$installed" = true ]; then
                echo "OK: $app_bname installed." >> "${log_var}"
                pm enable "$pkg_name" >> "${log_var}" 2>&1
            else
                echo "WARN: $app_bname install rejected by PM." >> "${log_var}"
            fi
            rm -rf "$STAGE_DIR" >> "${log_var}" 2>&1

        elif [ -f "$appdir" ] && [ "${{appdir##*.}}" = "apk" ]; then
            fname=$(basename "$appdir")
            echo "Installing flat APK: $fname..." >> "${log_var}"
            rm -rf "$STAGE_DIR" && mkdir -p "$STAGE_DIR"
            cp "$appdir" "$STAGE_DIR/$fname" >> "${log_var}" 2>&1
            chmod 644 "$STAGE_DIR/$fname" >> "${log_var}" 2>&1
            installed=false
            sz=$(stat -c%s "$STAGE_DIR/$fname" 2>/dev/null || wc -c < "$STAGE_DIR/$fname")
            sess_id=$(pm install-create -i com.android.packageinstaller -r -g -S $sz 2>&1 | tr -cd '0-9')
            if [ -n "$sess_id" ]; then
                pm install-write -S $sz $sess_id base "$STAGE_DIR/$fname" >> "${log_var}" 2>&1
                commit_res=$(pm install-commit $sess_id 2>&1)
                if echo "$commit_res" | grep -qi "Success"; then installed=true; else pm install-abandon $sess_id > /dev/null 2>&1; fi
            fi
            if [ "$installed" = false ]; then
                inst_res=$(pm install -i com.android.packageinstaller -r "$STAGE_DIR/$fname" 2>&1)
                echo "$inst_res" >> "${log_var}"
                if echo "$inst_res" | grep -qi "Success"; then installed=true; fi
                if [ "$installed" = false ]; then
                    inst_res=$(pm install -r "$STAGE_DIR/$fname" 2>&1)
                    echo "$inst_res" >> "${log_var}"
                    echo "$inst_res" | grep -qi "Success" && installed=true
                fi
            fi
            if [ "$installed" = true ]; then
                echo "OK: $fname installed." >> "${log_var}"
                pm enable "${{fname%.apk}}" >> "${log_var}" 2>&1
            fi
            rm -rf "$STAGE_DIR" >> "${log_var}" 2>&1
        fi
    done
fi

echo "Breaking APP_STOPPED flag for all restored packages..." >> "${log_var}"
for pdir in "${target_dir_var}/data_data/"*; do
    [ -d "$pdir" ] && pm enable "$(basename "$pdir")" > /dev/null 2>&1
done
"""


def gen_restore_app_data_with_uid_mapping(target_dir_var: str = "TARGET_DIR", log_var: str = "LOG_FILE") -> str:
    """Restores application internal data with dynamic UID mapping, WAL cleanup, and SELinux relabeling."""
    return f"""echo "9/12 Restoring App Internal Data with Dynamic UID resolution..." >> "${log_var}"
if [ -d "${target_dir_var}/data_data" ]; then
    for pdir in "${target_dir_var}/data_data/"*; do
        if [ -d "$pdir" ]; then
            pname=$(basename "$pdir")
            dest_dir="/data/data/$pname"
            am force-stop "$pname" > /dev/null 2>&1
            sleep 0.1
            rm -f "$dest_dir/databases/"*-wal "$dest_dir/databases/"*-shm 2>/dev/null
            mkdir -p "$dest_dir" >> "${log_var}" 2>&1
            for item in "$pdir/"*; do
                if [ -e "$item" ]; then
                    iname=$(basename "$item")
                    if [ "$iname" != "lib" ] && [ "$iname" != "cache" ] && [ "$iname" != "code_cache" ]; then
                        cp -r "$item" "$dest_dir/" >> "${log_var}" 2>&1
                    fi
                fi
            done
            APP_UID=""
            if [ -f "/data/system/packages.list" ]; then
                APP_UID=$(awk -v p="$pname" '$1==p {{print $2}}' /data/system/packages.list)
            fi
            if [ -z "$APP_UID" ]; then
                APP_UID=$(dumpsys package "$pname" 2>/dev/null | grep -m1 "userId=" | tr -cd '0-9')
            fi
            if [ -z "$APP_UID" ]; then
                APP_UID=$(pm list packages -U 2>/dev/null | grep "package:$pname " | head -n1 | sed 's/.*uid://' | tr -cd '0-9')
            fi
            if [ -z "$APP_UID" ] || [ "$APP_UID" -lt 10000 ]; then
                STAT_UID=$(stat -c %u "$dest_dir" 2>/dev/null)
                if [ -n "$STAT_UID" ] && [ "$STAT_UID" -ge 10000 ]; then
                    APP_UID="$STAT_UID"
                fi
            fi

            if [ -n "$APP_UID" ] && [ "$APP_UID" -ge 10000 ]; then
                chown -R "$APP_UID:$APP_UID" "$dest_dir" >> "${log_var}" 2>&1
            else
                chown -R 1000:1000 "$dest_dir" >> "${log_var}" 2>&1
            fi
            chmod 751 "$dest_dir" >> "${log_var}" 2>&1
            chmod -R 771 "$dest_dir/databases" "$dest_dir/shared_prefs" "$dest_dir/files" 2>/dev/null
            chmod 660 "$dest_dir/databases"/* "$dest_dir/shared_prefs"/* 2>/dev/null
            restorecon -R "$dest_dir" >> "${log_var}" 2>&1
        fi
    done
    restorecon -R /data/data >> "${log_var}" 2>&1
    restorecon -R /data/system >> "${log_var}" 2>&1
fi

if [ -d "${target_dir_var}/user_de" ]; then
    echo "Restoring Device-Encrypted storage (user_de)..." >> "${log_var}"
    mkdir -p /data/user_de/0 >> "${log_var}" 2>&1
    cp -r "${target_dir_var}/user_de/"* /data/user_de/0/ >> "${log_var}" 2>&1
    if [ -f "/data/system/packages.list" ]; then
        for udedir in /data/user_de/0/*; do
            if [ -d "$udedir" ]; then
                udename=$(basename "$udedir")
                udeuid=$(awk -v p="$udename" '$1==p {{print $2}}' /data/system/packages.list)
                if [ -n "$udeuid" ]; then
                    chown -R "$udeuid:$udeuid" "$udedir" >> "${log_var}" 2>&1
                    chmod 751 "$udedir" >> "${log_var}" 2>&1
                fi
            fi
        done
    fi
    restorecon -R /data/user_de >> "${log_var}" 2>&1
fi
"""


def gen_restore_connectivity(target_dir_var: str = "TARGET_DIR", log_var: str = "LOG_FILE") -> str:
    """Restores Wi-Fi, Bluetooth pairings, ADB keys, and developer mode settings."""
    return f"""echo "10/12 Restoring Wi-Fi, Bluetooth & ADB Keys..." >> "${log_var}"
if [ -d "${target_dir_var}/wifi_bt/wifi" ]; then
    mkdir -p /data/misc/wifi >> "${log_var}" 2>&1
    cp -r "${target_dir_var}/wifi_bt/wifi/"* /data/misc/wifi/ >> "${log_var}" 2>&1
    chown -R wifi:wifi /data/misc/wifi >> "${log_var}" 2>&1
    chmod -R 770 /data/misc/wifi >> "${log_var}" 2>&1
else
    echo "Community / No Wi-Fi in backup: Preserving target Wi-Fi." >> "${log_var}"
fi
if [ -d "${target_dir_var}/wifi_bt/bluedroid" ]; then
    mkdir -p /data/misc/bluedroid >> "${log_var}" 2>&1
    cp -r "${target_dir_var}/wifi_bt/bluedroid/"* /data/misc/bluedroid/ >> "${log_var}" 2>&1
    chown -R bluetooth:bluetooth /data/misc/bluedroid >> "${log_var}" 2>&1
    chmod -R 770 /data/misc/bluedroid >> "${log_var}" 2>&1
fi
if [ -d "${target_dir_var}/wifi_bt/bluetooth" ]; then
    mkdir -p /data/misc/bluetooth >> "${log_var}" 2>&1
    cp -r "${target_dir_var}/wifi_bt/bluetooth/"* /data/misc/bluetooth/ >> "${log_var}" 2>&1
    chown -R bluetooth:bluetooth /data/misc/bluetooth >> "${log_var}" 2>&1
    chmod -R 770 /data/misc/bluetooth >> "${log_var}" 2>&1
fi
if [ -d "${target_dir_var}/wifi_bt/vendor_bt" ]; then
    mkdir -p /data/vendor/bluetooth >> "${log_var}" 2>&1
    cp -r "${target_dir_var}/wifi_bt/vendor_bt/"* /data/vendor/bluetooth/ >> "${log_var}" 2>&1
    chown -R bluetooth:bluetooth /data/vendor/bluetooth >> "${log_var}" 2>&1
    chmod -R 770 /data/vendor/bluetooth >> "${log_var}" 2>&1
fi
if [ -d "${target_dir_var}/wifi_bt/adb" ]; then
    mkdir -p /data/misc/adb >> "${log_var}" 2>&1
    cp -r "${target_dir_var}/wifi_bt/adb/"* /data/misc/adb/ >> "${log_var}" 2>&1
    chmod 640 /data/misc/adb/* >> "${log_var}" 2>&1
    chown -R system:shell /data/misc/adb >> "${log_var}" 2>&1
fi
if grep -q 'name="development_settings_enabled" value="1"' "${target_dir_var}/settings/settings_global.xml" 2>/dev/null; then
    echo "Reinforcing Developer Mode & ADB..." >> "${log_var}"
    settings put global development_settings_enabled 1 >> "${log_var}" 2>&1
    settings put global adb_enabled 1 >> "${log_var}" 2>&1
    setprop persist.sys.usb.config diag,serial_smd,rmnet_ipa,adb >> "${log_var}" 2>&1
    setprop persist.adb.tcp.port 5555 >> "${log_var}" 2>&1
    for s_dir in /data/user_de/0/com.android.settings /data/data/com.android.settings; do
        if [ -d "$s_dir" ]; then
            mkdir -p "$s_dir/shared_prefs" >> "${log_var}" 2>&1
            echo '<?xml version="1.0" encoding="utf-8" standalone="yes" ?><map><boolean name="show" value="true" /></map>' > "$s_dir/shared_prefs/development.xml" 2>> "${log_var}"
            chmod 660 "$s_dir/shared_prefs/development.xml" >> "${log_var}" 2>&1
            chown 1000:1000 "$s_dir/shared_prefs/development.xml" >> "${log_var}" 2>&1
        fi
    done
fi
"""


def gen_restore_user_media(target_dir_var: str = "TARGET_DIR", log_var: str = "LOG_FILE") -> str:
    """Restores user media (/data/media/0 or /sdcard) with correct ownership."""
    return f"""echo "11/12 Restoring Internal Storage..." >> "${log_var}"
if [ -d "${target_dir_var}/sdcard" ] && [ -n "$(ls -A "${target_dir_var}/sdcard" 2>/dev/null)" ]; then
    SD_DEST="/data/media/0"
    [ ! -d "$SD_DEST" ] && SD_DEST="/sdcard"
    cp -r "${target_dir_var}/sdcard/." "$SD_DEST/" >> "${log_var}" 2>&1
    chown -R media_rw:media_rw "$SD_DEST" >> "${log_var}" 2>&1
    chmod -R 775 "$SD_DEST" >> "${log_var}" 2>&1
else
    echo "No media backup: Preserving existing internal storage." >> "${log_var}"
fi
"""


def gen_restore_final_hardening(target_dir_var: str = "TARGET_DIR", log_var: str = "LOG_FILE") -> str:
    """Locks /system RO, re-injects settings XMLs right before hard reboot, sets launcher state, and reboots."""
    return f"""echo "12/12 Applying visual UI settings & final security configs..." >> "${log_var}"
mount -o remount,ro /system >> "${log_var}" 2>&1

if [ -f "${target_dir_var}/settings/explicit_settings.sh" ]; then
    echo "Applying visual UI settings (font scale, 12/24h clock, timezone)..." >> "${log_var}"
    sh "${target_dir_var}/settings/explicit_settings.sh" >> "${log_var}" 2>&1
fi

echo "Re-injecting appwidgets and settings XMLs directly before hard reboot..." >> "${log_var}"
if [ -f "${target_dir_var}/settings/appwidgets.xml" ]; then
    cp -f "${target_dir_var}/settings/appwidgets.xml" /data/system/users/0/ >> "${log_var}" 2>&1
    cp -f "${target_dir_var}/settings/appwidgets.xml" /data/system/ >> "${log_var}" 2>&1
    chmod 600 /data/system/users/0/appwidgets.xml /data/system/appwidgets.xml 2>/dev/null
    chown system:system /data/system/users/0/appwidgets.xml /data/system/appwidgets.xml 2>/dev/null
fi
cp -f "${target_dir_var}/settings/settings_"*.xml /data/system/users/0/ >> "${log_var}" 2>&1
chmod 600 /data/system/users/0/settings_*.xml >> "${log_var}" 2>&1
chown system:system /data/system/users/0/settings_*.xml >> "${log_var}" 2>&1

DEF_LAUNCHER_FILE="${target_dir_var}/settings/default_launcher.txt"
if [ -f "$DEF_LAUNCHER_FILE" ]; then
    DEF_COMPONENT=$(cat "$DEF_LAUNCHER_FILE" | tr -d '\\r\\n ')
    if echo "$DEF_COMPONENT" | grep -q "/"; then
        echo "Setting default home launcher: $DEF_COMPONENT" >> "${log_var}"
        cmd package set-home-activity "$DEF_COMPONENT" >> "${log_var}" 2>&1
    fi
fi

if [ -f "${target_dir_var}/settings/oem_launcher_state.txt" ]; then
    echo "Re-freezing stock OEM launcher as captured in backup..." >> "${log_var}"
    pm disable com.qinggan.app.launcher >> "${log_var}" 2>&1
    pm disable-user --user 0 com.qinggan.app.launcher >> "${log_var}" 2>&1
elif grep -q 'name="com.qinggan.app.launcher".*enabled="2"' "${target_dir_var}/settings/package-restrictions.xml" 2>/dev/null; then
    echo "Restoring stock launcher freeze state from XML..." >> "${log_var}"
    pm disable com.qinggan.app.launcher >> "${log_var}" 2>&1
    pm disable-user --user 0 com.qinggan.app.launcher >> "${log_var}" 2>&1
fi

echo "===========================================" >> "${log_var}"
echo "RESTORE COMPLETED 100%! REBOOTING..." >> "${log_var}"
echo "===========================================" >> "${log_var}"
echo "=== AERO PROCESS STATUS: SUCCESS ===" >> "${log_var}"
date >> "${log_var}"
mkdir -p "$USB_PATH/completed_cars/${{CAR_SERIAL}}" 2>/dev/null
touch "$USB_PATH/completed_cars/${{CAR_SERIAL}}/completed.done"
touch "$USB_PATH/completed_cars/${{CAR_SERIAL}}.done"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] MODEL: $CAR_MODEL | SERIAL: $CAR_SERIAL | STATUS: RESTORE_COMPLETE" >> "$USB_PATH/completed_cars/registry.txt"
sync
sleep 2
sync
setprop sys.powerctl reboot || reboot -f || busybox reboot -f || reboot
"""


def gen_fetch_logs_block(logs_dir_name: str = "Logs", log_var: str = "LOG_FILE") -> str:
    """
    Generates shell commands to extract complete system diagnostics (logcat, dmesg,
    getprop, dumpsys package, dumpsys meminfo, storage df, tombstones, anr, recovery)
    into $USB_PATH/{logs_dir_name}.
    """
    return f"""echo "Extracting system diagnostic telemetry to $USB_PATH/{logs_dir_name}..." >> "${log_var}"
LOGS_DIR="$USB_PATH/{logs_dir_name}"
mkdir -p "$LOGS_DIR"

logcat -d -v time > "$LOGS_DIR/logcat.txt" 2>&1
dmesg > "$LOGS_DIR/dmesg.txt" 2>&1
getprop > "$LOGS_DIR/getprop.txt" 2>&1
dumpsys package > "$LOGS_DIR/dumpsys_package.txt" 2>&1
dumpsys meminfo > "$LOGS_DIR/dumpsys_meminfo.txt" 2>&1
df -h > "$LOGS_DIR/storage_df.txt" 2>&1

if [ -d "/data/tombstones" ]; then
    mkdir -p "$LOGS_DIR/tombstones"
    cp -r /data/tombstones/* "$LOGS_DIR/tombstones/" 2>/dev/null
fi
if [ -d "/data/anr" ]; then
    mkdir -p "$LOGS_DIR/anr"
    cp -r /data/anr/* "$LOGS_DIR/anr/" 2>/dev/null
fi
if [ -d "/cache/recovery" ]; then
    mkdir -p "$LOGS_DIR/recovery"
    cp -r /cache/recovery/* "$LOGS_DIR/recovery/" 2>/dev/null
fi
echo "  ✓ Diagnostic logs successfully extracted to $USB_PATH/{logs_dir_name}." >> "${log_var}"
"""


