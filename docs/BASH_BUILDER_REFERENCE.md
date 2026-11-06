# Aero Suite — Bash Builder & Payload Engineering Reference Manual

> **Document Version:** 2.0  
> **Target Audience:** Future AI Agents, System Engineers, and Core Contributors  
> **Architecture Pattern:** SOLID Principles, Single Responsibility Principle (SRP), Atomic Shell Code Generators  
> **Module Path:** `src/payloads/bash_builder.py`

---

## 1. Architecture Philosophy & Design Principles

The infotainment head unit running in Dongfeng Aeolus vehicles is an embedded Android system (API 27 / Android 8.1 Oreo) running on a Qualcomm Snapdragon SoC. Writing brittle, gigantic strings of raw Bash inside each payload file causes maintenance nightmares, hard-to-detect syntax bugs, and prevents code reuse.

`bash_builder.py` serves as the **Single Source of Truth** for all on-device shell execution logic. It follows strict software engineering principles:

1. **Single Responsibility Principle (SRP):** Each generator function produces code for **exactly one atomic operation** (e.g., wiping Bluetooth pairing data, mounting partition RW, resolving an app UID, relabeling SELinux context). Even operations used by only one payload must be isolated into their own dedicated generator.
2. **Open / Closed Principle (OCP):** New system features or payloads can be assembled simply by composing existing atomic blocks, without modifying proven core routines.
3. **Defense in Depth & Automotive Resilience:**
   - Always redirect outputs to `${LOG_FILE}` (`>> "$LOG_FILE" 2>&1`) to prevent silent failure.
   - Avoid assumptions about storage mount points: verify directories before copying or deleting.
   - Prevent database corruption by wiping SQLite write-ahead logs (`*-wal`, `*-shm`) before touching internal app databases.
   - Use hard kernel reboot (`reboot -f || setprop sys.powerctl reboot`) when writing direct XML settings on disk so Android's `system_server` does not overwrite the disk files with in-memory state during graceful shutdown.

---

## 2. Table of Contents & Function Directory

| Category | Functions |
|---|---|
| **1. Header, Mount & Lifecycle** | `gen_bash_header`, `gen_mount_rw`, `gen_mount_ro`, `gen_reboot`, `gen_bash_footer` |
| **2. App Lifecycle & Launch Engine** | `gen_install_system_apps`, `gen_install_user_apps`, `gen_disable_app`, `gen_enable_app`, `gen_grant_permissions`, `gen_launch_app` |
| **3. Uninstallation & Debloating** | `gen_uninstall_user_app`, `gen_uninstall_system_app`, `gen_uninstall_app`, `gen_purge_apps`, `gen_system_purge_reboot_check` |
| **4. Granular Data Wiping** | `gen_wipe_app_data`, `gen_wipe_account_databases`, `gen_wipe_bluetooth_data`, `gen_wipe_cache_partition`, `gen_clear_bootloader_control_block`, `gen_wipe_data_partition` |
| **5. Factory Purge & Auto-Healing** | `gen_purge_non_whitelisted_apps`, `gen_auto_heal_factory_apps` |
| **6. GMS & System Customization** | `gen_purge_stale_gms`, `gen_inject_voice_recognizers`, `gen_inject_gservices_features`, `gen_neutralize_automotive_flags`, `gen_force_provisioning_flags`, `gen_force_arabic_locale`, `gen_configure_gboard_ime`, `gen_inject_gboard_preset`, `gen_direct_patch_settings_xml`, `gen_gms_compatibility_and_arabic`, `gen_gboard_config`, `gen_restore_oem_defaults` |
| **7. Diagnostics & CAN-Bus** | `gen_system_snapshot`, `gen_canbus_tweaks` |
| **8. Backup Extraction Engine** | `gen_backup_init`, `gen_backup_system_settings`, `gen_backup_custom_system_apps`, `gen_backup_user_apks`, `gen_backup_app_data`, `gen_backup_connectivity`, `gen_backup_user_media`, `gen_backup_manifest_and_flags` |
| **9. Restoration Engine (12 Steps)** | `gen_restore_header_check`, `gen_restore_pkg_resolver`, `gen_restore_custom_system_apps`, `gen_restore_voice_and_keystore`, `gen_restore_accounts`, `gen_restore_properties_and_flags`, `gen_restore_settings_xml`, `gen_restore_package_restrictions`, `gen_restore_user_apps`, `gen_restore_app_data_with_uid_mapping`, `gen_restore_connectivity`, `gen_restore_user_media`, `gen_restore_final_hardening` |

---

## 3. Detailed Specification by Module

### 3.1 Header, Mount & Lifecycle

#### `gen_bash_header(title: str, log_filename: str = "install_log.txt") -> str`
- **Purpose:** Emits the standard POSIX shebang, resolves dynamically discovered USB mount path (`/udisk`, `/storage/udisk*`, `/mnt/media_rw/*`), initializes the log file, and prints the branded banner.
- **Parameters:**
  - `title`: Human-readable title of the operation written to log.
  - `log_filename`: Log filename created on the USB drive root (default: `"install_log.txt"`).
- **Automotive Resilience:** Discovers USB path using 5 distinct fallback strategies.

#### `gen_mount_rw(log_var: str = "LOG_FILE") -> str`
- **Purpose:** Remounts `/system` as Read-Write (`RW`) using native `mount`, fallback `mount -o rw,remount`, and `busybox`.
- **When to use:** Any time `/system/priv-app`, `/system/app`, or `/system/etc` needs modification.

#### `gen_mount_ro(log_var: str = "LOG_FILE") -> str`
- **Purpose:** Remounts `/system` back to Read-Only (`RO`) to maintain filesystem integrity and OEM tamper protections.

#### `gen_reboot(delay: int = 2, message: str = "", log_var: str = "LOG_FILE") -> str`
- **Purpose:** Performs a synchronized, delay-buffered reboot.

#### `gen_bash_footer(success_status: str = "SUCCESS", with_reboot: bool = False, reboot_delay: int = 2, reboot_msg: str = "", log_var: str = "LOG_FILE") -> str`
- **Purpose:** Standard script conclusion: touches `$USB_PATH/process_complete`, flushes disk buffers (`sync`), writes final timestamp, and optionally triggers a reboot.

---

### 3.2 Application Lifecycle & Launch Engine

#### `gen_install_system_apps(soft_dir_var: str = "SOFT_DIR", log_var: str = "LOG_FILE") -> str`
- **Purpose:** Deploys privileged/system APKs into `/system/priv-app/`. Sets directory permissions to `755`, APK permissions to `644`, and configures architecture-specific shared objects under `lib/arm/` to `644`.

#### `gen_install_user_apps(user_apps_dir_var: str = "USER_APPS_DIR", log_var: str = "LOG_FILE") -> str`
- **Purpose:** Unlocks OEM sideload restrictions via `persist.ais_server.3app.perm 1`, bypasses Android package verifier, and performs `pm install -r -g` on every APK in the directory.

#### `gen_disable_app(package_name: str, log_var: str = "LOG_FILE") -> str`
- **Purpose:** Freezes an app using dual-tier disabling (`pm disable` + `pm disable-user --user 0`) and terminates running instances (`am force-stop`).

#### `gen_enable_app(package_name: str, log_var: str = "LOG_FILE") -> str`
- **Purpose:** Unfreezes a disabled application across all users (`pm enable`, `pm default-state`).

#### `gen_grant_permissions(package_name: str, permissions: list, log_var: str = "LOG_FILE") -> str`
- **Purpose:** Grants explicit runtime dangerous permissions (e.g., `READ_EXTERNAL_STORAGE`, `ACCESS_FINE_LOCATION`) via `pm grant`.

#### `gen_launch_app(package_name: str, app_title: str = "", log_var: str = "LOG_FILE") -> str`
- **Purpose:** **4-Tier Automotive Launch Engine:**
  1. Primary: Resolves launcher activity via `cmd package resolve-activity`.
  2. Fallback 1: Discovers launchable activities via `pm dump`.
  3. Fallback 2: Uses `monkey -p <pkg> -c android.intent.category.LAUNCHER 1`.
  4. Fallback 3: Explicit main component launch.

---

### 3.3 Uninstallation & Debloating Engine (SRP)

> [!IMPORTANT]
> **SRP Separation Rule:**
> - User apps residing in `/data/app` must **never** touch `/system/priv-app`.
> - System apps residing in `/system/priv-app` or `/system/app` require dynamic directory discovery via `pm path` before deleting, plus framework cache wipe.

#### `gen_uninstall_user_app(package_name: str, log_var: str = "LOG_FILE") -> str`
- **Purpose:** Clears app state (`pm clear`), uninstalls via package manager (`pm uninstall`), purges APK folders from `/data/app/`, and wipes internal caches.

#### `gen_uninstall_system_app(package_name: str, purge_data: bool = True, log_var: str = "LOG_FILE") -> str`
- **Purpose:** Queries `pm path <pkg>` to find the exact mount directory under `/system`, wipes that directory, clears package manager registrations, and purges system residue.

#### `gen_uninstall_app(package_name: str, log_var: str = "LOG_FILE") -> str`
- **Purpose:** High-level Dual-Sweep uninstaller that cleanly purges the package regardless of whether it is located in `/data/app` or `/system/priv-app`.

#### `gen_purge_apps(packages: list, wipe_privapp_patterns: list = None, wipe_accounts: bool = False, purge_system_apps: bool = False, log_var: str = "LOG_FILE") -> str`
- **Purpose:** Batch deep uninstallation iterating over a package list with optional wildcard pattern cleanups and account database purges.

---

### 3.4 Granular Data Wiping (SRP)

#### `gen_wipe_app_data(package_name: str, log_var: str = "LOG_FILE") -> str`
- **Purpose:** Completely wipes `/data/data/<pkg>`, `/data/user/0/<pkg>`, `/data/user_de/0/<pkg>`, external storage app data `/data/media/0/Android/data/<pkg>`, and Dalvik bytecode cache.

#### `gen_wipe_account_databases(log_var: str = "LOG_FILE") -> str`
- **Purpose:** Deletes `accounts.db` (credential vault), `accounts_de.db` (device encrypted accounts), and sync state databases.

#### `gen_wipe_bluetooth_data(log_var: str = "LOG_FILE") -> str` *(Alias: `gen_bluetooth_factory_reset`)*
- **Purpose:** Disables Bluetooth service, terminates Bluetooth stacks, clears Bluetooth databases, deletes global paired device settings, and sets `persist.bluetooth.factoryreset true`.

#### `gen_wipe_cache_partition(log_var: str = "LOG_FILE") -> str`
- **Purpose:** Wipes `/cache/*`, cleans stale recovery commands, and restores directory permissions (`771`).

#### `gen_clear_bootloader_control_block(log_var: str = "LOG_FILE") -> str`
- **Purpose:** Writes zeroes to the Bootloader Control Block (`misc` partition via `dd if=/dev/zero ... count=64`) to prevent bootloader recovery loops.

#### `gen_wipe_data_partition(log_var: str = "LOG_FILE") -> str`
- **Purpose:** Complete deep factory purge of `/data` partition while keeping system folders intact for clean first-boot recreation.

---

### 3.5 Factory Purge Whitelist & Auto-Healing

#### `gen_purge_non_whitelisted_apps(whitelist: list, target_system_dir: str = "/system/priv-app", log_var: str = "LOG_FILE") -> str`
- **Purpose:** Loops through `/system/priv-app` (or `/system/app`), compares each folder name against the official factory whitelist, and wipes any non-OEM folder.

#### `gen_auto_heal_factory_apps(source_backup_dir: str, target_system_dir: str, log_var: str = "LOG_FILE") -> str`
- **Purpose:** Checks if essential factory system apps are missing from the head unit. If missing, restores them from the USB backup with permissions `755` (dirs) and `644` (apks).

---

### 3.6 GMS & System Customization

#### `gen_purge_stale_gms(log_var: str = "LOG_FILE") -> str`
- **Purpose:** Wipes old, broken, or Chinese-ROM conflicting Google Play Services, Google Services Framework, Play Store, and files before clean reinstallation.

#### `gen_inject_voice_recognizers(log_var: str = "LOG_FILE") -> str`
- **Purpose:** Injects `/system/etc/permissions/voice_recognizers.xml` with `android.software.voice_recognizers` so Google Voice Assistant can bind to the microphone.

#### `gen_inject_gservices_features(log_var: str = "LOG_FILE") -> str`
- **Purpose:** Injects `/system/etc/permissions/gservices.xml` declaring `cn.google.services` and `services_updater`.

#### `gen_neutralize_automotive_flags(log_var: str = "LOG_FILE") -> str`
- **Purpose:** Strips `android.hardware.type.automotive` from permissions XMLs so Google Play Store treats the head unit as a regular tablet/phone, unlocking full app library downloads.

#### `gen_force_provisioning_flags(log_var: str = "LOG_FILE") -> str` *(Alias: `gen_device_provisioning`)*
- **Purpose:** Bypasses Google SetupWizard locks by setting `device_provisioned 1` and `user_setup_complete 1`.

#### `gen_force_arabic_locale(log_var: str = "LOG_FILE") -> str`
- **Purpose:** Enforces Arabic language system-wide across `settings put system system_locales ar`, `setprop persist.sys.locale ar`, and direct file write to `/data/property/persist.sys.locale`.

#### `gen_configure_gboard_ime(log_var: str = "LOG_FILE") -> str`
- **Purpose:** Activates Gboard, sets it as the default input method, configures Arabic/English sub-types, and disables factory Chinese keyboard (`QingganIME`).

#### `gen_inject_gboard_preset(gboard_preset_var: str = "GBOARD_PRESET", log_var: str = "LOG_FILE") -> str`
- **Purpose:** Injects pre-configured themes and dictionaries into `/data/data/com.google.android.inputmethod.latin/`, dynamically maps UID, and relabels SELinux context.

#### `gen_direct_patch_settings_xml(log_var: str = "LOG_FILE") -> str` *(Alias: `gen_direct_settings_xml_patch`)*
- **Purpose:** Patches `settings_secure.xml` and `settings_system.xml` directly on disk so that default IME and Arabic locales survive immediate cold boot.

#### `gen_restore_oem_defaults(log_var: str = "LOG_FILE") -> str`
- **Purpose:** Clears Google permission files, re-enables factory keyboard IME, clears TTS overrides, and resets setup flags back to stock.

---

### 3.7 Diagnostics & Hardware CAN-Bus Tweaks

#### `gen_system_snapshot(log_var: str = "LOG_FILE") -> str`
- **Purpose:** Extracts car model, build ID, list of all installed system apps and user apps, and dumps `logcat` directly to the USB drive under `DongfengData/<CAR_ID>/`.

#### `gen_canbus_tweaks(selected_tweaks: list, log_var: str = "LOG_FILE") -> str`
- **Purpose:** Waits for vehicle IPC and CAN-Bus daemons (`qg.canbus`, `ais_server`), and dispatches selected vehicle modifications (speed lock bypass, day/night theme sync, steering wheel controls).

---

### 3.8 Backup Extraction Engine

#### `gen_backup_init(target_dir_var: str = "TARGET_DIR", b_type: str = "PERSONAL", inc_media: bool = False, log_var: str = "LOG_FILE") -> str`
- **Purpose:** Reads vehicle model and build ID, logs backup configuration, initializes `$USB_PATH/Backup`, and clears stale completion flags.

#### `gen_backup_system_settings(target_dir_var: str = "TARGET_DIR", b_type: str = "PERSONAL", log_var: str = "LOG_FILE") -> str`
- **Purpose:** Extracts XML settings (`package-restrictions.xml`, `runtime-permissions.xml`, `appops.xml`, `settings_*.xml`, `appwidgets.xml`, `build.prop`), saves active launcher state, and records dynamic UI settings (font scale, 12/24h clock, timezone, default IME).

#### `gen_backup_custom_system_apps(target_dir_var: str = "TARGET_DIR", priv_whitelist: list = None, app_whitelist: list = None, log_var: str = "LOG_FILE") -> str`
- **Purpose:** Sweeps `/system/priv-app` and `/system/app`, filters out factory whitelist packages, and backs up only custom system additions.

#### `gen_backup_user_apks(target_dir_var: str = "TARGET_DIR", log_var: str = "LOG_FILE") -> str`
- **Purpose:** Backs up all user-installed APKs from `/data/app/`.

#### `gen_backup_app_data(target_dir_var: str = "TARGET_DIR", b_type: str = "PERSONAL", log_var: str = "LOG_FILE") -> str`
- **Purpose:** Extracts application internal databases (`/data/data`, `/data/user_de/0`). In `COMMUNITY` mode, scrubs private Google accounts, Play Store tokens, and Bluetooth pairings to ensure 100% zero-leakage safe sharing.

#### `gen_backup_connectivity(target_dir_var: str = "TARGET_DIR", b_type: str = "PERSONAL", log_var: str = "LOG_FILE") -> str`
- **Purpose:** Backs up saved Wi-Fi networks and Bluetooth pairings in `PERSONAL` mode; cleanly skips in `COMMUNITY` mode.

#### `gen_backup_user_media(target_dir_var: str = "TARGET_DIR", inc_media: bool = False, log_var: str = "LOG_FILE") -> str`
- **Purpose:** Backs up user media files from `/data/media/0` or `/sdcard` (skipping cache and APK data) if enabled.

#### `gen_backup_manifest_and_flags(target_dir_var: str = "TARGET_DIR", b_type: str = "PERSONAL", preset_name: str = "", author: str = "", inc_media: bool = False, log_var: str = "LOG_FILE") -> str`
- **Purpose:** Saves package lists (`packages_full.txt`), writes `Backup_Manifest.txt`, and generates `backup_complete.flag`.

---

### 3.9 Restoration Engine (12 Steps)

Restoration follows a strict 12-step sequence to guarantee system stability and prevent authentication conflicts:

| Step | Function | Description |
|---|---|---|
| Check | `gen_restore_header_check` | Validates `restore_ready.flag` and locates backup folder |
| Helper| `gen_restore_pkg_resolver` | Generates shell function `resolve_pkg_name` for accurate package resolution |
| 1/12  | `gen_mount_rw` + Unfreeze | Mounts `/system` RW and unfreezes stock OEM launcher |
| 2/12  | `gen_restore_custom_system_apps` | Restores priv-apps & system apps with `755`/`644` permissions |
| 3/12  | `gen_restore_voice_and_keystore` | Restores voice recognizers XML and Keystore master keys |
| 4/12  | `gen_restore_accounts` | Restores Google accounts DB or cleans stale target tokens in Community mode |
| 5/12  | `gen_restore_properties_and_flags` | Sets provisioning flags and restores system properties |
| 6/12  | `gen_restore_settings_xml` | Restores runtime permissions, appops, appwidgets XMLs |
| 7/12  | `gen_restore_package_restrictions` | Restores package restrictions *before* installing user apps to preserve freeze state |
| 8/12  | `gen_restore_user_apps` | Unlocks OEM sideload policies and installs user apps via PackageManager session |
| 9/12  | `gen_restore_app_data_with_uid_mapping` | Restores app data with SQLite WAL purge, 4-tier UID resolution, and `restorecon -R` |
| 10/12 | `gen_restore_connectivity` | Restores Wi-Fi networks, Bluetooth pairings, and reinforces ADB |
| 11/12 | `gen_restore_user_media` | Restores internal storage media files with `media_rw` ownership |
| 12/12 | `gen_restore_final_hardening` | Locks `/system` RO, re-injects settings XMLs right before hard reboot, sets launcher state |

---

## 4. Usage Guide for AI Agents: How to Assemble Payloads

When an AI agent or developer is asked to create a new payload or feature, **never write raw bash strings directly**. Instead, compose functions from `bash_builder`:

```python
from payloads.bash_builder import (
    gen_bash_header,
    gen_mount_rw,
    gen_mount_ro,
    gen_install_system_apps,
    gen_grant_permissions,
    gen_launch_app,
    gen_bash_footer
)

def prepare_my_custom_payload(usb_drive: str, package_name: str) -> bool:
    # 1. Compose script using atomic building blocks
    script = (
        gen_bash_header("CUSTOM USER PAYLOAD", "install_log.txt")
        + gen_mount_rw()
        + gen_install_system_apps("SOFT_DIR")
        + gen_grant_permissions(package_name, ["android.permission.RECORD_AUDIO"])
        + gen_mount_ro()
        + gen_launch_app(package_name, app_title="Custom App")
        + gen_bash_footer(success_status="SUCCESS", with_reboot=True, reboot_delay=3)
    )
    
    # 2. Write custom_rep.sh and manuals
    ...
```

---

## 5. Architectural Roadmap & Unified Manual Engine

Now that all operations are encapsulated into atomic functions and the manual generator is unified:
1. **Unified Manual Engine (`src/payloads/manual_generator.py`):**
   - Implements `generate_unified_manual(actions: list, lang: str)` supporting both single payloads and multi-action queues (The Basket).
   - Generates unified, non-redundant instructions across all 4 languages: **Arabic (`ar`)**, **English (`en`)**, **Russian (`ru`)**, and **Chinese (`zh`)**.
   - Provides `write_composite_manual(usb_drive, actions, lang)` for composite flash drives.
2. **Multi-Action Queue Integration (The Basket):**
   - Single initial `gen_mount_rw()`.
   - Sequential execution of atomic payload blocks.
   - Single final `gen_mount_ro()`.
   - Single consolidated reboot at the very end.
   - Single consolidated `دليل_الاستخدام.html` / `User_Guide.html` generated via `write_composite_manual`.
