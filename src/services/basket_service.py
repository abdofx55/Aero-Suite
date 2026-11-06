"""
basket_service.py — Composite Multi-Command Queue Engine (The Basket) for Aero Suite.
Adheres strictly to SOLID/SRP principles and docs/BASH_BUILDER_REFERENCE.md.
Coordinates multi-payload staging, conflict detection, script assembly, and composite USB preparation.
"""
import os
import re
import time
import tempfile
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Callable

from PySide6.QtCore import QObject, Signal

from core.constants import SIGNATURE_BANNER, FACTORY_PRIV_APPS, FACTORY_APPS
from core.exceptions import log_exception
from core.i18n import t, get_i18n
from payloads.base import (
    clean_usb_drive,
    count_usb_clean_ops,
    write_script_file,
    extract_so_libs,
    copy_file_with_chunk_progress,
    patch_apk
)
from payloads.bash_builder import (
    gen_bash_header,
    gen_state_init,
    gen_wait_for_boot_completed,
    gen_stage_reboot,
    gen_mount_rw,
    gen_mount_ro,
    gen_install_system_apps,
    gen_install_user_apps,
    gen_replace_systemui,
    gen_disable_app,
    gen_enable_app,
    gen_purge_apps,
    gen_purge_stale_gms,
    gen_gms_compatibility_and_arabic,
    gen_canbus_tweaks,
    gen_launch_app,
    gen_bash_footer,
    gen_backup_init,
    gen_backup_system_settings,
    gen_backup_custom_system_apps,
    gen_backup_user_apks,
    gen_backup_app_data,
    gen_backup_connectivity,
    gen_backup_user_media,
    gen_backup_manifest_and_flags,
    gen_wipe_data_partition,
    gen_bluetooth_factory_reset,
    gen_gboard_config,
    gen_direct_settings_xml_patch,
    gen_fetch_logs_block
)
from core.constants import ACTION_EXECUTION_ORDER
from payloads.manual_generator import write_composite_manual


@dataclass
class BasketItem:
    """Represents a single queued operation inside the Basket."""
    action_type: str                   # e.g., 'install_apps', 'install_gms', 'disable_launcher', 'reboot_screen'
    title: str                         # Display title
    summary: str                       # Short human-readable summary
    config: Dict[str, Any] = field(default_factory=dict)
    requires_reboot: bool = False      # Whether this action mandates a reboot
    launch_target_pkg: Optional[str] = None   # Package name to launch if this action requests auto-launch
    launch_target_name: Optional[str] = None  # Human-readable name of launch app


class BasketService(QObject):
    """
    Central Coordinator for queued multi-command USB generation.
    Enforces business rules:
    1. Launcher freeze is deferred to the end (Step N-1).
    2. Reboot is always consolidated and executed at the very end.
    3. Launch conflicts are trapped immediately.
    4. If Reboot is present, launch actions are superseded and removed.
    """
    basket_changed = Signal(int)       # Emits current count of items
    item_added = Signal(str)           # Emits action_type
    item_removed = Signal(str)         # Emits action_type

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[BasketItem] = []

    # ---------------------------------------------------------
    # Item Management & Sorting by Execution Sequence
    # ---------------------------------------------------------
    ACTION_EXECUTION_ORDER = {
        "backup": 5,               # Stage 0: Safe data extraction first before any wipe or mods
        "factory_reset": 10,        # Stage 1: Wipe & restore OEM stock ROM (reboots)
        "quick_setup": 12,          # Stage 1.5: Master Fast Provisioning
        "uninstall_gms": 15,
        "uninstall_apps": 20,
        "vehicle_tweaks": 30,
        "install_hvac_bar": 35,
        "restore_hvac_bar": 35,
        "install_gms": 40,
        "install_apps": 50,
        "enable_launcher": 60,
        "disable_launcher": 70,     # Executed post-boot
        "open_settings": 80,
        "open_app": 80,
        "reboot_screen": 90         # Very end
    }

    def get_items(self) -> List[BasketItem]:
        """Returns shallow copy of queued items."""
        return list(self._items)

    def get_ordered_items(self) -> List[BasketItem]:
        """Returns queued items sorted strictly by actual vehicle execution sequence."""
        return sorted(self._items, key=lambda it: self.ACTION_EXECUTION_ORDER.get(it.action_type, 50))

    def count(self) -> int:
        return len(self._items)

    def is_empty(self) -> bool:
        return len(self._items) == 0

    def get_item(self, action_type: str) -> Optional[BasketItem]:
        for it in self._items:
            if it.action_type == action_type:
                return it
        return None

    def has_item(self, action_type: str) -> bool:
        return any(it.action_type == action_type for it in self._items)

    def add_item(self, item: BasketItem) -> None:
        """
        Adds or updates an item in the queue.
        Resolves mutual exclusions:
        - disable_launcher vs enable_launcher
        - install_gms vs uninstall_gms
        - install_hvac_bar vs restore_hvac_bar
        - open_settings vs open_app (single foreground activity)
        """
        # Mutual exclusion 1: Launcher freeze vs unfreeze
        if item.action_type == "disable_launcher":
            self.remove_item("enable_launcher")
        elif item.action_type == "enable_launcher":
            self.remove_item("disable_launcher")

        # Mutual exclusion 2: GMS install vs uninstall
        if item.action_type == "install_gms":
            self.remove_item("uninstall_gms")
        elif item.action_type == "uninstall_gms":
            self.remove_item("install_gms")

        # Mutual exclusion 3: Standalone app openers (only one foreground window)
        if item.action_type == "open_settings":
            self.remove_item("open_app")
        elif item.action_type == "open_app":
            self.remove_item("open_settings")

        # Mutual exclusion 4: HVAC bar install vs restore
        if item.action_type == "install_hvac_bar":
            self.remove_item("restore_hvac_bar")
        elif item.action_type == "restore_hvac_bar":
            self.remove_item("install_hvac_bar")

        # Mutual exclusion 5: Quick setup vs GMS / HVAC
        if item.action_type == "quick_setup":
            self.remove_item("install_hvac_bar")
            self.remove_item("restore_hvac_bar")
            self.remove_item("install_gms")
            self.remove_item("uninstall_gms")
        elif item.action_type in ("install_hvac_bar", "restore_hvac_bar", "install_gms", "uninstall_gms"):
            self.remove_item("quick_setup")

        # If this item sets a launch target, enforce single launch target across all items
        if item.launch_target_pkg:
            self.set_launch_target(item.action_type, item.launch_target_pkg, item.launch_target_name or item.launch_target_pkg)

        # Check existing item of same action_type
        existing_idx = next((i for i, it in enumerate(self._items) if it.action_type == item.action_type), -1)
        if existing_idx >= 0:
            self._items[existing_idx] = item
        else:
            self._items.append(item)

        self.item_added.emit(item.action_type)
        self.basket_changed.emit(len(self._items))

    def remove_item(self, action_type: str) -> bool:
        idx = next((i for i, it in enumerate(self._items) if it.action_type == action_type), -1)
        if idx >= 0:
            self._items.pop(idx)
            self.item_removed.emit(action_type)
            self.basket_changed.emit(len(self._items))
            return True
        return False

    def clear(self) -> None:
        if self._items:
            self._items.clear()
            self.basket_changed.emit(0)

    # ---------------------------------------------------------
    # Launch Target & Conflict Resolution
    # ---------------------------------------------------------
    def get_current_launch_target(self) -> Optional[Tuple[str, str, str]]:
        """
        Returns (action_type, pkg, app_name) of the active launch target in the basket, or None.
        """
        for it in self._items:
            if it.launch_target_pkg:
                return (it.action_type, it.launch_target_pkg, it.launch_target_name or it.launch_target_pkg)
        return None

    def check_launch_conflict(self, new_action: str, new_pkg: str, new_name: str) -> Optional[Tuple[str, str, str]]:
        """
        Checks if a DIFFERENT launch target is already registered in the basket.
        Returns existing (action_type, pkg, name) if conflict exists, else None.
        """
        current = self.get_current_launch_target()
        if not current:
            return None
        cur_action, cur_pkg, cur_name = current
        if cur_pkg != new_pkg:
            return (cur_action, cur_pkg, cur_name)
        return None

    def set_launch_target(self, target_action: str, target_pkg: str, target_name: str) -> None:
        """Sets launch target on target_action and clears it from all other actions."""
        for it in self._items:
            if it.action_type == target_action:
                it.launch_target_pkg = target_pkg
                it.launch_target_name = target_name
            else:
                it.launch_target_pkg = None
                it.launch_target_name = None

    def clear_all_launch_targets(self) -> None:
        """Clears launch targets across all items."""
        for it in self._items:
            it.launch_target_pkg = None
            it.launch_target_name = None

    # ---------------------------------------------------------
    # Reboot & Environmental Checks
    # ---------------------------------------------------------
    def has_reboot(self) -> bool:
        """
        Returns True if any item mandates a reboot (explicit reboot_screen, factory_reset, GMS, HVAC, system apps, etc.).
        """
        if self.has_item("reboot_screen") or self.has_item("factory_reset"):
            return True
        for it in self._items:
            if it.requires_reboot:
                return True
            # Check install_apps system targets
            if it.action_type == "install_apps":
                selected = it.config.get("selected_apks", [])
                if any(a.get("install_target") == "system" for a in selected):
                    return True
        return False

    def get_reboot_count(self) -> int:
        """
        Calculates exact number of physical screen reboots:
        - 2 reboots: Factory reset (Stage 1) + System modifications/GMS/HVAC/System Apps (Stage 2).
        - 1 reboot: Either Stage 1 or Stage 2 reboot, or explicit reboot_screen.
        - 0 reboots: User apps only, tweaks only, launcher toggles, logs extraction, etc.
        """
        has_reset = self.has_item("factory_reset")
        item_inst = self.get_item("install_apps")
        has_sys_apps = False
        if item_inst:
            selected = item_inst.config.get("selected_apks", [])
            has_sys_apps = any(isinstance(a, dict) and a.get("install_target") == "system" for a in selected)

        has_stage2_reboot = (
            self.has_item("install_gms") or
            self.has_item("install_hvac_bar") or
            self.has_item("restore_hvac_bar") or
            self.has_item("uninstall_gms") or
            has_sys_apps
        )
        if has_reset and has_stage2_reboot:
            return 2
        elif has_reset or has_stage2_reboot or self.has_item("reboot_screen"):
            return 1
        return 0

    # ---------------------------------------------------------
    # Script Assembly Engine (Multi-Stage State Machine Pipeline)
    # ---------------------------------------------------------
    def assemble_composite_script(self) -> Tuple[str, bool, Optional[str]]:
        """
        Builds the unified multi-stage custom_rep.sh script string for the entire basket.
        Enforces Multi-Stage State Machine Architecture:
        - Stage 0: System Backup (if queued, pre-flight, no reboot)
        - Stage 1: Factory Reset (if queued, wipes /data, reboots)
        - Stage 2: Modifications, GMS, HVAC Bar & App Installs (reboots if system components modified)
        - Stage 3: Post-Boot configuration (Gboard IME setup, stock launcher freeze, auto-launch)
        Returns (script_content, has_reboot, active_launch_pkg_or_none).
        """
        reboot_needed = self.has_reboot()
        launch_info = self.get_current_launch_target()
        final_launch_pkg = launch_info[1] if launch_info else None

        header = gen_bash_header("AERO SUITE COMPOSITE MULTI-STAGE BATCH", "composite_batch.log")
        stages = [gen_state_init()]

        # Common directory definitions
        stages.append("""SOFT_DIR="$USB_PATH/update/soft"
USER_SOFT_DIR="$USB_PATH/update/user_soft"
USER_APPS_STAGE="$USB_PATH/update/user_apps"
GBOARD_PRESET="$USB_PATH/update/gboard_data"
""")

        # -------------------------------------------------------------
        # STAGE 0: COMPLETE SYSTEM & DATA BACKUP (Pre-Flight, No Reboot)
        # -------------------------------------------------------------
        item_backup = self.get_item("backup")
        if item_backup:
            b_type = (item_backup.config.get("backup_type") or "personal").upper()
            inc_media = bool(item_backup.config.get("include_media", False))
            p_name = item_backup.config.get("preset_name", "")
            author = item_backup.config.get("author", "")
            stages.append(f"""# =============================================================
# STAGE 0: SYSTEM & DATA EXTRACTION (PRE-FLIGHT BACKUP)
# =============================================================
if [ ! -f "$STATE_DIR/stage_backup.done" ]; then
    echo "=== STAGE 0: EXTRACTING COMPLETE VEHICLE BACKUP TO USB ===" >> "$LOG_FILE"
{gen_backup_init(target_dir_var="TARGET_DIR", b_type=b_type, inc_media=inc_media, log_var="LOG_FILE")}
{gen_backup_system_settings(target_dir_var="TARGET_DIR", b_type=b_type, log_var="LOG_FILE")}
{gen_backup_custom_system_apps(target_dir_var="TARGET_DIR", priv_whitelist=FACTORY_PRIV_APPS, app_whitelist=FACTORY_APPS, log_var="LOG_FILE")}
{gen_backup_user_apks(target_dir_var="TARGET_DIR", log_var="LOG_FILE")}
{gen_backup_app_data(target_dir_var="TARGET_DIR", b_type=b_type, log_var="LOG_FILE")}
{gen_backup_connectivity(target_dir_var="TARGET_DIR", b_type=b_type, log_var="LOG_FILE")}
{gen_backup_user_media(target_dir_var="TARGET_DIR", inc_media=inc_media, log_var="LOG_FILE")}
{gen_backup_manifest_and_flags(target_dir_var="TARGET_DIR", b_type=b_type, preset_name=p_name, author=author, inc_media=inc_media, log_var="LOG_FILE", is_composite=True)}
fi
""")

        # -------------------------------------------------------------
        # STAGE 1: FACTORY RESET & ZERO-TRACE PURGE (Reboots Vehicle)
        # -------------------------------------------------------------
        item_reset = self.get_item("factory_reset")
        if item_reset:
            priv_str = ' '.join(FACTORY_PRIV_APPS)
            app_str = ' '.join(FACTORY_APPS)
            stages.append(f"""# =============================================================
# STAGE 1: ZERO-TRACE DEALERSHIP PURGE & FACTORY RESET
# =============================================================
if [ ! -f "$STATE_DIR/stage_factory_reset.done" ]; then
    echo "=== STAGE 1: INITIATING COMPLETE FACTORY PURGE ===" >> "$LOG_FILE"
{gen_mount_rw(log_var="LOG_FILE")}
{gen_enable_app("com.qinggan.app.launcher", log_var="LOG_FILE")}
PRIV_WHITELIST="{priv_str}"
APP_WHITELIST="{app_str}"

# Purge non-factory priv-apps
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

# Purge non-factory apps
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

# Smart auto-heal from FactoryRestore if staged on USB
if [ -d "$USB_PATH/update/FactoryRestore/priv-app" ]; then
    for fdir in "$USB_PATH/update/FactoryRestore/priv-app/"*; do
        if [ -d "$fdir" ]; then
            bname="${{fdir##*/}}"
            if [ ! -d "/system/priv-app/$bname" ]; then
                echo "Restoring missing OEM factory priv-app: $bname" >> "$LOG_FILE"
                cp -r "$fdir" /system/priv-app/ >> "$LOG_FILE" 2>&1
                chmod 755 "/system/priv-app/$bname" >> "$LOG_FILE" 2>&1
                chmod 644 "/system/priv-app/$bname"/*.apk >> "$LOG_FILE" 2>&1
            fi
        fi
    done
fi
if [ -d "$USB_PATH/update/FactoryRestore/app" ]; then
    for fdir in "$USB_PATH/update/FactoryRestore/app/"*; do
        if [ -d "$fdir" ]; then
            bname="${{fdir##*/}}"
            if [ ! -d "/system/app/$bname" ]; then
                echo "Restoring missing OEM factory app: $bname" >> "$LOG_FILE"
                cp -r "$fdir" /system/app/ >> "$LOG_FILE" 2>&1
                chmod 755 "/system/app/$bname" >> "$LOG_FILE" 2>&1
                chmod 644 "/system/app/$bname"/*.apk >> "$LOG_FILE" 2>&1
            fi
        fi
    done
fi

rm -f /system/etc/permissions/voice_recognizers.xml >> "$LOG_FILE" 2>&1
{gen_bluetooth_factory_reset(log_var="LOG_FILE")}
{gen_mount_ro(log_var="LOG_FILE")}
{gen_wipe_data_partition(log_var="LOG_FILE")}
{gen_stage_reboot("stage_factory_reset", reboot_delay=3, reboot_msg="FACTORY RESET COMPLETE — REBOOTING VEHICLE TO INITIALIZE CLEAN ROM...", log_var="LOG_FILE")}
fi
""")

        # -------------------------------------------------------------
        # STAGE 2: SYSTEM MODIFICATIONS & APPLICATIONS DEPLOYMENT
        # -------------------------------------------------------------
        install_items = [
            it for it in self._items
            if it.action_type in (
                "uninstall_apps", "uninstall_gms", "vehicle_tweaks",
                "install_hvac_bar", "restore_hvac_bar", "install_gms",
                "install_apps", "enable_launcher"
            )
        ]

        if install_items:
            stage2_parts = []
            needs_rw = False
            for it in install_items:
                if it.action_type in ("install_gms", "uninstall_gms", "vehicle_tweaks", "install_hvac_bar", "restore_hvac_bar"):
                    needs_rw = True
                elif it.action_type == "install_apps":
                    selected = it.config.get("selected_apks", [])
                    if any(a.get("install_target") == "system" for a in selected):
                        needs_rw = True

            if needs_rw:
                stage2_parts.append(gen_mount_rw())

            item_uninst = self.get_item("uninstall_apps")
            if item_uninst:
                pkgs = item_uninst.config.get("packages", [])
                if pkgs:
                    stage2_parts.append(f"""echo "=== STEP: UNINSTALLING SPECIFIED APPLICATIONS ===" >> "$LOG_FILE"
{gen_purge_apps(pkgs, log_var="LOG_FILE")}""")

            item_uninst_gms = self.get_item("uninstall_gms")
            if item_uninst_gms:
                stage2_parts.append(f"""echo "=== STEP: PURGING GOOGLE PLAY SERVICES ===" >> "$LOG_FILE"
{gen_purge_stale_gms(log_var="LOG_FILE")}""")

            item_tweaks = self.get_item("vehicle_tweaks")
            if item_tweaks:
                selected_tweaks = item_tweaks.config.get("selected_tweaks", [])
                if selected_tweaks:
                    stage2_parts.append(f"""echo "=== STEP: APPLYING VEHICLE CUSTOMIZATION TWEAKS ===" >> "$LOG_FILE"
{gen_canbus_tweaks(selected_tweaks, log_var="LOG_FILE")}""")

            item_inst_hvac = self.get_item("install_hvac_bar")
            if item_inst_hvac:
                stage2_parts.append("""echo "=== STEP: DEPLOYING ENHANCED NAVIGATION & CLIMATE BAR (AERO BAR) ===" >> "$LOG_FILE"
AEROBAR_STAGE="$USB_PATH/update/soft/AeroBar/AeroBar.apk"
if [ -f "$AEROBAR_STAGE" ]; then
    echo "Installing Aero Bar to /system/priv-app/AeroBar..." >> "$LOG_FILE"
    mkdir -p /system/priv-app/AeroBar >> "$LOG_FILE" 2>&1
    cp "$AEROBAR_STAGE" /system/priv-app/AeroBar/AeroBar.apk >> "$LOG_FILE" 2>&1
    chmod 755 /system/priv-app/AeroBar >> "$LOG_FILE" 2>&1
    chmod 644 /system/priv-app/AeroBar/AeroBar.apk >> "$LOG_FILE" 2>&1
    chown -R system:system /system/priv-app/AeroBar >> "$LOG_FILE" 2>&1
    pm install -r -g "$AEROBAR_STAGE" >> "$LOG_FILE" 2>&1
    appops set com.aero.bar.dongfeng_shine SYSTEM_ALERT_WINDOW allow >> "$LOG_FILE" 2>&1
    appops set com.aero.bar.dongfeng_shine.debug SYSTEM_ALERT_WINDOW allow >> "$LOG_FILE" 2>&1
    appops set com.aero.bar SYSTEM_ALERT_WINDOW allow >> "$LOG_FILE" 2>&1
    settings put secure enabled_accessibility_services com.aero.bar.dongfeng_shine/com.aero.bar.service.AeroAccessibilityService:com.aero.bar.dongfeng_shine.debug/com.aero.bar.service.AeroAccessibilityService >> "$LOG_FILE" 2>&1
    settings put secure accessibility_enabled 1 >> "$LOG_FILE" 2>&1
    settings put global policy_control immersive.navigation=* >> "$LOG_FILE" 2>&1
    if [ -f /system/build.prop ]; then
        grep -q "qemu.hw.mainkeys" /system/build.prop && sed -i "s/qemu.hw.mainkeys=.*/qemu.hw.mainkeys=1/" /system/build.prop || echo "qemu.hw.mainkeys=1" >> /system/build.prop
    fi
    setprop qemu.hw.mainkeys 1 >> "$LOG_FILE" 2>&1
fi""")

            item_rest_hvac = self.get_item("restore_hvac_bar")
            if item_rest_hvac:
                stage2_parts.append(f"""echo "=== STEP: RESTORING FACTORY STOCK OEM CLIMATE BAR ===" >> "$LOG_FILE"
HVAC_STAGE_APK="$USB_PATH/update/soft/SystemUI-release-signed/SystemUI-release-signed.apk"
{gen_replace_systemui(apk_source_var="HVAC_STAGE_APK", log_var="LOG_FILE")}""")

            item_gms = self.get_item("install_gms")
            if item_gms:
                stage2_parts.append(f"""echo "=== STEP: PURGING PREVIOUS GOOGLE PLAY SERVICES (CLEAN REINSTALL) ===" >> "$LOG_FILE"
{gen_purge_stale_gms(log_var="LOG_FILE")}
echo "=== STEP: INJECTING GOOGLE PLAY SERVICES ===" >> "$LOG_FILE"
{gen_install_system_apps(soft_dir_var="SOFT_DIR", log_var="LOG_FILE")}
{gen_gms_compatibility_and_arabic(log_var="LOG_FILE")}""")

            item_inst = self.get_item("install_apps")
            if item_inst:
                selected = item_inst.config.get("selected_apks", [])
                has_sys = any(a.get("install_target") == "system" for a in selected)
                if has_sys:
                    stage2_parts.append(f"""echo "=== STEP: DEPLOYING SYSTEM PRIVILEGED APPLICATIONS ===" >> "$LOG_FILE"
{gen_install_system_apps(soft_dir_var="SOFT_DIR", log_var="LOG_FILE")}""")

            if item_gms:
                stage2_parts.append(f"""echo "=== STEP: INSTALLING GOOGLE USER APPLICATIONS ===" >> "$LOG_FILE"
{gen_install_user_apps(user_soft_dir_var="USER_APPS_STAGE", log_var="LOG_FILE")}""")

            if item_inst:
                selected = item_inst.config.get("selected_apks", [])
                has_usr = any(a.get("install_target") != "system" for a in selected)
                if has_usr:
                    stage2_parts.append(f"""echo "=== STEP: INSTALLING THIRD-PARTY USER APPLICATIONS ===" >> "$LOG_FILE"
{gen_install_user_apps(user_soft_dir_var="USER_SOFT_DIR", log_var="LOG_FILE")}""")

            if self.has_item("enable_launcher"):
                stage2_parts.append(f"""echo "=== STEP: RESTORING OEM STOCK LAUNCHER ===" >> "$LOG_FILE"
{gen_enable_app("com.qinggan.app.launcher", log_var="LOG_FILE")}""")

            if needs_rw:
                stage2_parts.append(gen_mount_ro())

            stage2_requires_reboot = (
                item_gms is not None or
                item_inst_hvac is not None or
                item_rest_hvac is not None or
                item_uninst_gms is not None or
                (item_inst is not None and any(a.get("install_target") == "system" for a in item_inst.config.get("selected_apks", [])))
            )

            if stage2_requires_reboot:
                stage2_parts.append(gen_stage_reboot(
                    "stage_install",
                    reboot_delay=3,
                    reboot_msg="INSTALLATIONS COMPLETE — REBOOTING TO INITIALIZE SYSTEM PACKAGES...",
                    log_var="LOG_FILE"
                ))
            else:
                stage2_parts.append("""touch "$STATE_DIR/stage_install.done"
sync
""")

            stages.append(f"""# =============================================================
# STAGE 2: SYSTEM MODIFICATIONS & APPLICATIONS
# =============================================================
if [ ! -f "$STATE_DIR/stage_install.done" ]; then
    echo "=== STAGE 2: DEPLOYING SYSTEM MODIFICATIONS & APPLICATIONS ===" >> "$LOG_FILE"
{"".join(stage2_parts)}
fi
""")

        # -------------------------------------------------------------
        # STAGE 3: POST-BOOT FINALIZATION & AUTO-LAUNCH (Always Runs at End)
        # -------------------------------------------------------------
        stage3_parts = [
            'echo "=== STAGE 3: POST-BOOT CONFIGURATION & FINALIZATION ===" >> "$LOG_FILE"',
            gen_wait_for_boot_completed(settle_seconds=5, log_var="LOG_FILE"),
            'echo "Enforcing system provisioning completion flags..." >> "$LOG_FILE"',
            'settings put global device_provisioned 1 >> "$LOG_FILE" 2>&1',
            'settings put secure user_setup_complete 1 >> "$LOG_FILE" 2>&1'
        ]

        if self.has_item("install_gms"):
            stage3_parts.append(f"""echo "=== STEP: INJECTING GBOARD PRESET & ENABLING KEYBOARD ===" >> "$LOG_FILE"
{gen_gboard_config("GBOARD_PRESET", log_var="LOG_FILE")}
{gen_direct_settings_xml_patch(log_var="LOG_FILE")}""")

        if self.has_item("disable_launcher"):
            stage3_parts.append(f"""echo "=== STEP: FREEZING OEM STOCK LAUNCHER (FINALIZING UI) ===" >> "$LOG_FILE"
{gen_disable_app("com.qinggan.app.launcher", log_var="LOG_FILE")}""")

        if self.has_item("fetch_logs"):
            stage3_parts.append(f"""echo "=== STEP: EXTRACTING SYSTEM DIAGNOSTIC LOGS ===" >> "$LOG_FILE"
{gen_fetch_logs_block(logs_dir_name="Logs", log_var="LOG_FILE")}""")

        if final_launch_pkg:
            stage3_parts.append(f"""echo "=== STEP: AUTO-LAUNCHING APPLICATION ===" >> "$LOG_FILE"
{gen_launch_app(final_launch_pkg, log_var="LOG_FILE")}""")
        elif self.has_item("open_settings"):
            stage3_parts.append("""echo "=== STEP: LAUNCHING ANDROID SETTINGS ===" >> "$LOG_FILE"
am start -n com.android.settings/.Settings >> "$LOG_FILE" 2>&1
am start -a android.settings.SETTINGS >> "$LOG_FILE" 2>&1
""")

        footer_reboot = self.has_item("reboot_screen") and not (install_items and stage2_requires_reboot) and not (item_reset is not None)
        footer = gen_bash_footer(
            success_status="SUCCESS",
            with_reboot=footer_reboot,
            log_var="LOG_FILE"
        )
        stage3_parts.append(footer)

        stages.append("\n".join(stage3_parts))

        full_script = header + "\n" + "\n".join(stages)
        return full_script, reboot_needed, final_launch_pkg

    # ---------------------------------------------------------
    # High-Level Composite USB Preparation Worker
    # ---------------------------------------------------------
    def prepare_composite_usb(
        self,
        usb_drive: str,
        log_func: Optional[Callable[[str], None]] = None,
        progress_func: Optional[Callable] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> bool:
        """
        Executes complete multi-operation preparation:
        - Cleans USB drive with dynamic progress.
        - Stages all necessary files (APKs, GMS components, Tweaks).
        - Generates unified custom_rep.sh.
        - Generates multilingual composite manual (_Info.html).
        - Flushes disk buffers.
        """
        def _log(msg):
            if log_func:
                log_func(msg)

        if not os.path.exists(usb_drive):
            _log(t("logs.usb_not_found", f"  ✗ USB Drive not found: {usb_drive}", drive=usb_drive))
            return False

        if self.is_empty():
            _log("  ⚠ Basket is empty. Nothing to prepare.")
            return False

        if cancel_check and cancel_check():
            _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
            return False

        try:
            _log(f"\n── Preparing Composite Customization USB ({len(self._items)} Operations): {usb_drive} ──")

            # 1. Clean USB Drive
            clean_ops = count_usb_clean_ops(usb_drive)
            clean_work_units = (clean_ops / 350.0) * 15.0 if clean_ops > 0 else 0.0
            clean_end_pct = max(0.02, min(0.30, clean_work_units / 100.0)) if clean_work_units > 0 else 0.05

            clean_usb_drive(usb_drive, log_func, progress_func, cancel_check, start_pct=0.0, end_pct=clean_end_pct)
            if cancel_check and cancel_check():
                _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
                return False

            update_dir = os.path.join(usb_drive, "update")
            soft_dir = os.path.join(update_dir, "soft")
            user_soft_dir = os.path.join(update_dir, "user_soft")
            os.makedirs(update_dir, exist_ok=True)

            # 2. Stage Components Across Items
            # 2. Stage Components Across Items
            item_inst = self.get_item("install_apps")
            item_gms = self.get_item("install_gms")

            # Calculate total payload bytes across all APKs for smooth live progress tracking
            total_bytes = 0
            gms_sys_files = []
            gms_usr_files = []

            if item_gms:
                gms_dir = item_gms.config.get("gms_dir", "")
                inc_gboard = item_gms.config.get("include_gboard", True)
                inc_chrome = item_gms.config.get("include_chrome", False)
                inc_maps = item_gms.config.get("include_maps", False)
                if os.path.exists(gms_dir):
                    from payloads.install_gms import _is_system_priv_app, _get_gms_order_prefix
                    all_gms = [f for f in os.listdir(gms_dir) if f.lower().endswith(".apk")]
                    gms_sys_files = sorted([f for f in all_gms if _is_system_priv_app(f)], key=_get_gms_order_prefix)
                    for f in all_gms:
                        fl = f.lower()
                        if "gboard" in fl and inc_gboard:
                            gms_usr_files.append(f)
                        elif "chrome" in fl and inc_chrome:
                            gms_usr_files.append(f)
                        elif "maps" in fl and inc_maps:
                            gms_usr_files.append(f)

                    for f in gms_sys_files + gms_usr_files:
                        p = os.path.join(gms_dir, f)
                        if os.path.isfile(p):
                            total_bytes += os.path.getsize(p)

            inst_selected = item_inst.config.get("selected_apks", []) if item_inst else []
            for apk_info in inst_selected:
                p = apk_info.get("path", "")
                if os.path.isfile(p):
                    total_bytes += os.path.getsize(p)

            item_hvac_inst = self.get_item("install_hvac_bar")
            item_hvac_rest = self.get_item("restore_hvac_bar")
            hvac_src_apk = None
            if item_hvac_inst:
                from core.paths import HVAC_MOD_APK
                hvac_src_apk = HVAC_MOD_APK
            elif item_hvac_rest:
                from core.paths import HVAC_STOCK_APK, FACTORY_BACKUP_DIR
                hvac_src_apk = HVAC_STOCK_APK if os.path.isfile(HVAC_STOCK_APK) else os.path.join(FACTORY_BACKUP_DIR, "priv-app", "SystemUI-release-signed", "SystemUI-release-signed.apk")

            if hvac_src_apk and os.path.isfile(hvac_src_apk):
                total_bytes += os.path.getsize(hvac_src_apk)

            range_start = clean_end_pct
            range_span = 0.88 - range_start
            copied_bytes_cumulative = 0
            transfer_start_time = time.time()

            def _make_chunk_cb(display_name):
                def _on_chunk(chunk_len, file_copied, file_total):
                    nonlocal copied_bytes_cumulative
                    copied_bytes_cumulative += chunk_len
                    elapsed = max(0.05, time.time() - transfer_start_time)
                    speed_mb_s = (copied_bytes_cumulative / (1024 * 1024)) / elapsed
                    ratio = min(1.0, copied_bytes_cumulative / max(1, total_bytes))
                    current_pct = range_start + (ratio * range_span)
                    c_mb = copied_bytes_cumulative / (1024 * 1024)
                    t_mb = total_bytes / (1024 * 1024)
                    if progress_func:
                        progress_func(current_pct, display_name, speed_mb_s, c_mb, t_mb)
                return _on_chunk

            if total_bytes == 0:
                if progress_func:
                    progress_func(0.40, "Configuring operations & commands...")
                    time.sleep(0.06)

            # 2.1 Stage GMS if present
            if item_gms and (gms_sys_files or gms_usr_files):
                os.makedirs(soft_dir, exist_ok=True)
                user_apps_dir = os.path.join(update_dir, "user_apps")
                gms_dir = item_gms.config.get("gms_dir", "")
                from payloads.install_gms import _get_gms_order_prefix

                _log(f"  Staging Google Services ({len(gms_sys_files)} system, {len(gms_usr_files)} user)...")
                for f in gms_sys_files:
                    if cancel_check and cancel_check():
                        _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
                        return False
                    src_f = os.path.join(gms_dir, f)
                    base = os.path.splitext(f)[0]
                    clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '', base)
                    order_prefix = _get_gms_order_prefix(f)
                    folder_name = f"{order_prefix}{clean_name}" if not clean_name.startswith(order_prefix) else clean_name
                    dest_d = os.path.join(soft_dir, folder_name)
                    os.makedirs(dest_d, exist_ok=True)
                    dest_f = os.path.join(dest_d, f"{folder_name}.apk")
                    copy_file_with_chunk_progress(src_f, dest_f, chunk_callback=_make_chunk_cb(f), cancel_check=cancel_check)
                    extract_so_libs(src_f, dest_d, log_func)

                if gms_usr_files:
                    os.makedirs(user_apps_dir, exist_ok=True)
                    for f in gms_usr_files:
                        if cancel_check and cancel_check():
                            _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
                            return False
                        src_f = os.path.join(gms_dir, f)
                        base = os.path.splitext(f)[0]
                        dest_f = os.path.join(user_apps_dir, f"{base}.apk")
                        copy_file_with_chunk_progress(src_f, dest_f, chunk_callback=_make_chunk_cb(f), cancel_check=cancel_check)

            # 2.2 Stage Install Apps if present
            if item_inst and inst_selected:
                os.makedirs(soft_dir, exist_ok=True)
                os.makedirs(user_soft_dir, exist_ok=True)
                _log(f"  Staging {len(inst_selected)} application(s)...")

                for apk_info in inst_selected:
                    if cancel_check and cancel_check():
                        _log(t("logs.cancelled_by_user", "  ⚠ Operation cancelled by user."))
                        return False
                    src_apk = apk_info["path"]
                    fname = os.path.basename(src_apk)
                    clean_name = re.sub(r'[^a-zA-Z0-9_\-]', '', os.path.splitext(fname)[0])
                    target_type = apk_info.get("install_target", "user")
                    force_portrait = apk_info.get("force_portrait", False)
                    block_boot = apk_info.get("block_boot", True)

                    target_ori = "portrait" if force_portrait else "default"
                    needs_patch = (target_ori == "portrait" or block_boot)

                    if target_type == "system":
                        app_dest_dir = os.path.join(soft_dir, clean_name)
                        os.makedirs(app_dest_dir, exist_ok=True)
                        dest_apk = os.path.join(app_dest_dir, f"{clean_name}.apk")
                        extract_so_libs(src_apk, app_dest_dir, log_func)
                    else:
                        dest_apk = os.path.join(user_soft_dir, f"{clean_name}.apk")

                    source_to_copy = src_apk
                    temp_patched = None
                    if needs_patch:
                        temp_patched = os.path.join(tempfile.gettempdir(), f"aero_{clean_name}_{int(time.time()*1000)}.apk")
                        ok_p = patch_apk(src_apk, temp_patched, log_func=log_func, target_orientation=target_ori, disable_boot_launch=block_boot)
                        if ok_p and os.path.isfile(temp_patched):
                            source_to_copy = temp_patched

                    copy_file_with_chunk_progress(source_to_copy, dest_apk, chunk_callback=_make_chunk_cb(fname), cancel_check=cancel_check)
                    if temp_patched and os.path.exists(temp_patched):
                        try:
                            os.remove(temp_patched)
                        except Exception:
                            pass

            # 2.3 Stage HVAC Bar if present
            if hvac_src_apk and os.path.isfile(hvac_src_apk):
                os.makedirs(soft_dir, exist_ok=True)
                if item_hvac_inst:
                    hvac_dir = os.path.join(soft_dir, "AeroBar")
                    os.makedirs(hvac_dir, exist_ok=True)
                    dest_f = os.path.join(hvac_dir, "AeroBar.apk")
                    _log("  Staging Aero Bar System APK for Navigation Bar deployment...")
                    copy_file_with_chunk_progress(hvac_src_apk, dest_f, chunk_callback=_make_chunk_cb("AeroBar.apk"), cancel_check=cancel_check)
                else:
                    hvac_dir = os.path.join(soft_dir, "SystemUI-release-signed")
                    os.makedirs(hvac_dir, exist_ok=True)
                    dest_f = os.path.join(hvac_dir, "SystemUI-release-signed.apk")
                    _log("  Staging Stock SystemUI APK for Navigation Bar restoration...")
                    copy_file_with_chunk_progress(hvac_src_apk, dest_f, chunk_callback=_make_chunk_cb("SystemUI-release-signed.apk"), cancel_check=cancel_check)

            # 2.4 Stage Gboard Custom Preset Data if present
            if item_gms and item_gms.config.get("include_gboard", True):
                gms_dir = item_gms.config.get("gms_dir", "")
                if os.path.exists(gms_dir):
                    gboard_src_dir = os.path.join(gms_dir, "gboard_data")
                    if os.path.isdir(gboard_src_dir):
                        import shutil
                        dest_gb_data = os.path.join(update_dir, "gboard_data")
                        if os.path.exists(dest_gb_data):
                            shutil.rmtree(dest_gb_data, ignore_errors=True)
                        shutil.copytree(gboard_src_dir, dest_gb_data)
                        _log("  Staging custom Gboard profile preset...")

            # 2.5 Stage FactoryRestore if factory_reset is queued
            item_reset = self.get_item("factory_reset")
            if item_reset:
                from core.constants import FACTORY_BACKUP_DIR
                from payloads.base import copy_tree_with_progress
                if os.path.isdir(FACTORY_BACKUP_DIR):
                    _log("  Staging FactoryRestore archive for stock ROM auto-healing...")
                    dest_factory = os.path.join(update_dir, "FactoryRestore")
                    copy_tree_with_progress(FACTORY_BACKUP_DIR, dest_factory, progress_callback=None, log_func=log_func, cancel_check=cancel_check)

            # 3. Assemble and Write Script
            if progress_func:
                progress_func(0.90, "Assembling unified custom_rep.sh batch script...")

            script_str, will_reboot, auto_pkg = self.assemble_composite_script()
            script_path = os.path.join(update_dir, "custom_rep.sh")
            write_script_file(script_path, script_str)
            _log("  ✓ Generated unified custom_rep.sh batch script.")

            # 4. Generate Composite Manual (HTML)
            if progress_func:
                progress_func(0.95, "Generating composite user manual (HTML)...")

            actions_payload = [{"id": it.action_type, "kwargs": it.config} for it in self.get_ordered_items()]
            write_composite_manual(usb_drive, actions_payload, lang=get_i18n().current_lang)
            _log("  ✓ Generated composite user manual (User_Guide.html).")

            # 5. Flush USB Buffers
            if progress_func:
                progress_func(0.98, "Flushing filesystem buffers to USB drive...")
                time.sleep(0.04)
                progress_func(1.0, "Composite Customization USB ready!")

            _log("✓ Composite Customization USB prepared successfully.")
            return True

        except Exception as e:
            log_exception(e, "prepare_composite_usb")
            _log(f"  ✗ Failed to prepare composite USB: {str(e)}")
            return False


# Shared Singleton Instance
_basket_service_instance: Optional[BasketService] = None


def get_basket_service() -> BasketService:
    global _basket_service_instance
    if _basket_service_instance is None:
        _basket_service_instance = BasketService()
    return _basket_service_instance
