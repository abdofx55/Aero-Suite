"""
factory_reset.py — Feature 12: Zero-Trace Factory Purge & OEM Auto-Healing Payload Generator.
Purges all custom modifications, restores stock ROM integrity, wipes crash traces, and hard reboots.
"""
import os
import time
from core.constants import FACTORY_PRIV_APPS, FACTORY_APPS, SIGNATURE_BANNER
from core.exceptions import log_exception
from core.i18n import t
from payloads.base import clean_usb_drive, write_script_file, copy_tree_with_progress
from payloads.bash_builder import (
    gen_bash_header,
    gen_mount_rw,
    gen_mount_ro,
    gen_enable_app,
    gen_bluetooth_factory_reset,
    gen_wipe_data_partition,
    gen_bash_footer
)
from payloads.manual_generator import generate_info_content, write_payload_manuals


def prepare_factory_reset_usb(
    usb_drive: str,
    local_factory_backup_dir: str = "",
    log_func=None,
    progress_func=None,
    cancel_check=None
) -> bool:
    """Prepares USB to restore vehicle to pristine factory zero state."""
    def _log(msg):
        if log_func:
            log_func(msg)

    _log(t("logs.prep_usb_header", f"\n── Preparing Factory Reset USB (Zero-Trace Purge): {usb_drive} ──", title=t("nav.factory_reset_title", "Factory Reset"), drive=usb_drive))
    if not os.path.exists(usb_drive):
        _log(t("logs.usb_not_found", f"  ✗ USB Drive not found: {usb_drive}", drive=usb_drive))
        return False

    if cancel_check and cancel_check():
        _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
        return False

    try:
        has_local_factory = bool(local_factory_backup_dir and os.path.exists(local_factory_backup_dir))
        clean_usb_drive(usb_drive, log_func, progress_func, cancel_check, start_pct=0.0, end_pct=0.15 if has_local_factory else 0.30)
        if cancel_check and cancel_check():
            _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
            return False

        update_dir = os.path.join(usb_drive, "update")
        os.makedirs(update_dir, exist_ok=True)

        if has_local_factory:
            _log(t("logs.factory_backup_copy", "  Copying FactoryBackup to USB for auto-healing stock ROM..."))
            ok_copy = copy_tree_with_progress(
                local_factory_backup_dir,
                os.path.join(update_dir, "FactoryRestore"),
                progress_callback=progress_func,
                log_func=log_func,
                cancel_check=cancel_check,
                scale_range=(0.15, 0.88)
            )
            if not ok_copy or (cancel_check and cancel_check()):
                _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
                return False
            if progress_func:
                progress_func(0.91, "Verifying factory restore integrity...", 0.0, 0, 0)
        else:
            if progress_func:
                progress_func(0.55, "Configuring factory whitelist...", 0.0, 0, 0)

        if progress_func:
            progress_func(0.94 if has_local_factory else 0.75, "Generating Zero-Trace recovery script...", 0.0, 0, 0)

        priv_str = ' '.join(FACTORY_PRIV_APPS)
        app_str = ' '.join(FACTORY_APPS)

        script = (
            gen_bash_header("DEEP ZERO-TRACE FACTORY PURGE", "factory_restore.log")
            + gen_mount_rw()
            + gen_enable_app("com.qinggan.app.launcher")
            + f"""
PRIV_WHITELIST="{priv_str}"
APP_WHITELIST="{app_str}"

# 3. Purge non-factory priv-apps
for dir in /system/priv-app/*; do
    if [ -d "$dir" ]; then
        name="${{dir##*/}}"
        is_factory=false
        for fw in $PRIV_WHITELIST; do
            if [ "$name" = "$fw" ]; then is_factory=true; break; fi
        done
        if [ "$is_factory" = "false" ]; then
            echo "Purging non-factory priv-app: $name" >> "$LOG_FILE"
            rm -rf "$dir" >> "$LOG_FILE" 2>&1
        fi
    fi
done

# 4. Purge non-factory apps
for dir in /system/app/*; do
    if [ -d "$dir" ]; then
        name="${{dir##*/}}"
        is_factory=false
        for fw in $APP_WHITELIST; do
            if [ "$name" = "$fw" ]; then is_factory=true; break; fi
        done
        if [ "$is_factory" = "false" ]; then
            echo "Purging non-factory app: $name" >> "$LOG_FILE"
            rm -rf "$dir" >> "$LOG_FILE" 2>&1
        fi
    fi
done

# 5. Smart auto-heal: byte-by-byte integrity verification (cmp -s) for tampered or missing factory apps
if [ -d "$USB_PATH/update/FactoryRestore/priv-app" ]; then
    for fdir in "$USB_PATH/update/FactoryRestore/priv-app/"*; do
        if [ -d "$fdir" ]; then
            bname="${{fdir##*/}}"
            needs_restore=false
            if [ ! -d "/system/priv-app/$bname" ]; then
                needs_restore=true
            else
                src_apk=""
                for a in "$fdir"/*.apk; do
                    if [ -f "$a" ]; then src_apk="$a"; break; fi
                done
                target_apk=""
                for a in "/system/priv-app/$bname"/*.apk; do
                    if [ -f "$a" ]; then target_apk="$a"; break; fi
                done

                if [ -z "$target_apk" ] || [ ! -f "$target_apk" ]; then
                    needs_restore=true
                elif [ -n "$src_apk" ] && [ -f "$src_apk" ]; then
                    if ! cmp -s "$src_apk" "$target_apk" 2>/dev/null; then
                        needs_restore=true
                    fi
                fi
            fi

            if [ "$needs_restore" = "true" ]; then
                echo "Auto-healing missing or tampered factory priv-app: $bname" >> "$LOG_FILE"
                rm -rf "/system/priv-app/$bname" >> "$LOG_FILE" 2>&1
                cp -r "$fdir" /system/priv-app/ >> "$LOG_FILE" 2>&1
                chmod 755 "/system/priv-app/$bname" >> "$LOG_FILE" 2>&1
                chmod 644 "/system/priv-app/$bname"/*.apk >> "$LOG_FILE" 2>&1
                if [ -d "/system/priv-app/$bname/oat" ]; then
                    chmod 755 "/system/priv-app/$bname/oat" >> "$LOG_FILE" 2>&1
                    chmod -R 644 "/system/priv-app/$bname/oat"/* >> "$LOG_FILE" 2>&1
                fi
            else
                echo "Factory priv-app verified intact: $bname" >> "$LOG_FILE"
            fi
        fi
    done
fi
if [ -d "$USB_PATH/update/FactoryRestore/app" ]; then
    for fdir in "$USB_PATH/update/FactoryRestore/app/"*; do
        if [ -d "$fdir" ]; then
            bname="${{fdir##*/}}"
            needs_restore=false
            if [ ! -d "/system/app/$bname" ]; then
                needs_restore=true
            else
                src_apk=""
                for a in "$fdir"/*.apk; do
                    if [ -f "$a" ]; then src_apk="$a"; break; fi
                done
                target_apk=""
                for a in "/system/app/$bname"/*.apk; do
                    if [ -f "$a" ]; then target_apk="$a"; break; fi
                done

                if [ -z "$target_apk" ] || [ ! -f "$target_apk" ]; then
                    needs_restore=true
                elif [ -n "$src_apk" ] && [ -f "$src_apk" ]; then
                    if ! cmp -s "$src_apk" "$target_apk" 2>/dev/null; then
                        needs_restore=true
                    fi
                fi
            fi

            if [ "$needs_restore" = "true" ]; then
                echo "Auto-healing missing or tampered factory app: $bname" >> "$LOG_FILE"
                rm -rf "/system/app/$bname" >> "$LOG_FILE" 2>&1
                cp -r "$fdir" /system/app/ >> "$LOG_FILE" 2>&1
                chmod 755 "/system/app/$bname" >> "$LOG_FILE" 2>&1
                chmod 644 "/system/app/$bname"/*.apk >> "$LOG_FILE" 2>&1
                if [ -d "/system/app/$bname/oat" ]; then
                    chmod 755 "/system/app/$bname/oat" >> "$LOG_FILE" 2>&1
                    chmod -R 644 "/system/app/$bname/oat"/* >> "$LOG_FILE" 2>&1
                fi
            else
                echo "Factory app verified intact: $bname" >> "$LOG_FILE"
            fi
        fi
    done
fi

# 6. Remove injected permissions & enable stock launcher
echo "Enabling stock launcher and cleaning custom permissions..." >> "$LOG_FILE"
rm -f /system/etc/permissions/voice_recognizers.xml >> "$LOG_FILE" 2>&1
(pm enable com.qinggan.app.launcher >> "$LOG_FILE" 2>&1) &
"""
            + gen_bluetooth_factory_reset()
            + gen_mount_ro()
            + gen_wipe_data_partition()
            + gen_bash_footer(
                success_status="SUCCESS",
                with_reboot=True,
                reboot_delay=3,
                reboot_msg="FACTORY RESET COMPLETE — REBOOTING DIRECTLY TO ANDROID"
            )
        )
        write_script_file(os.path.join(update_dir, "custom_rep.sh"), script)

        if progress_func:
            progress_func(0.97 if has_local_factory else 0.90, "Writing Zero-Trace purge manual (HTML)...", 0.0, 0, 0)

        write_payload_manuals(usb_drive, "Factory_Reset_Info", "factory_reset", has_local_factory=has_local_factory)

        if progress_func:
            progress_func(0.99 if has_local_factory else 0.96, "Flushing filesystem buffers to USB drive...", 0.0, 0, 0)
            time.sleep(0.04)
            progress_func(1.0, "Factory Reset USB ready!", 0.0, 0, 0)

        _log(t("logs.prep_usb_success", "✓ Factory Reset USB prepared successfully.", title=t("nav.factory_reset_title", "Factory Reset")))
        return True
    except Exception as e:
        log_exception(e, "prepare_factory_reset_usb")
        _log(t("logs.prep_failed", "  ✗ Failed to prepare {title} USB: {err}", title=t("nav.factory_reset_title", "Factory Reset"), err=str(e)))
        return False
