# Aero Automotive Suite — Comprehensive v2.0 Technical Documentation & Changelog

**Target Hardware:** Dongfeng Shine / Aeolus D53 (Qinggan IVI Platform, Qualcomm MSM8953 Snapdragon 450/625, Android 8.1.0 Oreo API 27).  
**Lead Developer:** Abdelrhman Hamdy — Senior Software Engineer  
**Contact:** abdellrhman.hamdi@gmail.com | +201095449725  
**Version:** 2.0-Production (Evolution from v1.0-Beta)  

---

## 1. Executive Summary & Architectural Overview

Aero Automotive Suite v2.0 represents a comprehensive rewrite and enhancement of the original v1.0 desktop suite. What began as a single-action script deployer has evolved into an industrial-grade, GPU-accelerated automotive management studio with multi-action batch pipelines, expanded 10-component Google Ecosystem support, direct CAN-Bus vehicle telematics, full internationalization (4 languages with bidirectional RTL/LTR support), built-in filesystem tools, and deep system resilience against Android 8.1 / IVI edge cases.

---

## 2. Major Features & Subsystems Implemented

### 2.1. Multi-Action Execution Basket & Batch Pipeline (سلة الأوامر المجمعة)
* **Problem in v1.0:** The user had to prepare, format, and insert separate USB flash drives sequentially for each individual operation (e.g., install apps, freeze OEM launcher, toggle vehicle settings, and open native settings required 4 separate drive trips).
* **v2.0 Solution:**
  - Introduced the **Execution Basket (`BasketManager`)** in the central application architecture.
  - Users can stage multiple heterogeneous actions (e.g., install user apps + disable stock launcher + configure CAN-Bus tweaks + inject Google Services) into an execution queue.
  - The unified **`BashBuilder` engine** merges all staged payload steps into a single, cohesive, idempotent shell script (`update/custom_rep.sh`) with strict execution order safety:
    1. System remounts & pre-clean
    2. CAN-Bus vehicle tweaks
    3. Custom system priv-apps & apps
    4. Package manager installations
    5. UI & launcher state toggles
    6. System settings & permissions injection
    7. Automated app launches (Auto-Launch)
    8. Cache sync & safe atomic reboot

### 2.2. The Expanded 10-Component Google Ecosystem (منظومة جوجل المتكاملة)
The original 4-component GMS deployment was expanded into a complete 10-service suite tailored specifically to Qualcomm MSM8953 Android 8.1:

| # | Package Name / Component | Service Description | Integration Layer |
|---|--------------------------|---------------------|-------------------|
| 1 | `com.google.android.gsf` | Google Services Framework | `/system/priv-app/01_GSF` |
| 2 | `com.google.android.gsf.login` | Google Account Manager | `/system/priv-app/02_GSFLogin` |
| 3 | `com.google.android.gms` | Google Play Services (Core Engine) | `/system/priv-app/03_GMS` |
| 4 | `com.android.vending` | Google Play Store | `/system/priv-app/04_PlayStore` |
| 5 | `com.google.android.apps.nbu.files` | Files by Google (Storage Manager) | `/system/priv-app/05_GoogleFiles` |
| 6 | `com.google.android.tts` | Google Speech Services & Text-to-Speech | `/system/priv-app/06_GoogleSpeech` |
| 7 | `voice_recognizers.xml` | Android System Voice Recognizer Permissions | `/system/etc/permissions/` |
| 8 | `com.google.android.inputmethod.latin` | Gboard (Google Keyboard) | `/data/app/` + Preference Injection |
| 9 | `com.google.android.apps.maps` | Google Maps Navigation | `/data/app/` |
| 10 | `com.android.chrome` | Google Chrome Stable Browser | `/data/app/` |

**Post-Setup Automation Added:**
- **Auto-Launch Play Store:** Launches Google Play Store directly upon first boot for instant Google account sign-in.
- **Auto-Launch Files by Google:** Launches Files with full granted `MANAGE_EXTERNAL_STORAGE` and `PACKAGE_USAGE_STATS` permissions.

### 2.3. CAN-Bus Vehicle Features & Telematics (خصائص وتعديلات السيارة)
Implemented direct vehicle body control configuration via the `ICanBusService` (`qg.canbus` Binder interface) without requiring expensive third-party OBD2 dongles:
- **Welcome Light (إضاءة الترحيب عند الاقتراب):** Automatic courtesy exterior illumination when approaching with smart key.
- **Seat Welcome / Easy Entry (ترحيب المقعد وتسهيل الركوب):** Slides driver power seat rearward upon door opening, returning to driving profile upon ignition.
- **Speed-Sensing Auto Door Lock (قفل الأبواب التلقائي مع السرعة):** Automatically locks all central doors above 15 km/h.
- **Auto Park & Unlock on Engine Off (تفعيل الهاند بريك وفتح الأقفال عند إطفاء المحرك):** Automatically engages electric parking brake (EPB) and unlocks doors when stopping the engine.
- **Electric Trunk Safety Lock (إيقاف فتح الشنطة الكهربائية أثناء القيادة):** Prevents accidental rear liftgate trigger during transit.
- **Mirror Puddle Lights (إضاءة المرايات الجانبية):** Activates ground approach lights under mirrors.
- **Lock Confirmation Chirp (صوت التنبيه الهادئ عند غلق السيارة):** Audio feedback beep upon locking.

### 2.4. Full Multilingual Architecture & Dynamic RTL (دعم 4 لغات عالمية بالكامل)
- Completely decoupled hardcoded Arabic strings into structured JSON catalogs located in `src/locales/`:
  - 🇪🇬 **العربية (ar.json):** Egyptian colloquial tone, natural automotive terminology, full Right-to-Left (RTL) mirroring.
  - 🇬🇧 **English (en.json):** Professional technical automotive English, Left-to-Right (LTR).
  - 🇷🇺 **Русский (ru.json):** Tailored for Russian Dongfeng / Aeolus communities.
  - 🇨🇳 **中文 (zh.json):** Tailored for Dongfeng Aeolus domestic platform standards.
- **Instant Hot-Switching:** Languages switch live via the top-bar dropdown without restarting the process.
- **Onboarding Experience:** Immersive first-run wizard allowing user language selection before reaching the studio.
- **Dedicated Dedication Banner:** Standardized across all 4 locales: `🎁 إهداء خاص لملاك سيارة دونج فينج شاين في مصر ❤️` / `🎁 A Special Gift for Dongfeng Shine Owners in Egypt ❤️`.

### 2.5. PySide6 / Qt6 High-Performance GPU-Accelerated UI
- Replaced legacy CustomTkinter GUI with a modern PySide6 (Qt6) interface.
- Hardware-accelerated rendering eliminating screen tearing and UI redraw lag.
- Interactive **App Cards & Tweak Cards** with instant sub-millisecond full-text filtering and card-wide hitboxes.
- Real-time **Cyber Terminal Console** with color-coded syntax logs (Cyan, Mint, Amber, Crimson).
- Real-time transfer statistics measuring exact chunk byte throughput and USB transfer speed (`MB/s`).

### 2.6. Integrated USB Drive Tools & In-App FAT32 Formatter
- Direct pre-flight inspection of connected USB drive filesystems.
- Built-in formatting routine allowing users to format drives (including large 64GB/128GB/256GB USB sticks) to **FAT32** directly inside Aero Suite without external utilities like Rufus or MiniTool Partition Wizard.
- Instant USB hotplug detection (`UsbWatcher`) responding dynamically when flash drives are inserted or ejected.
- "Open in Explorer" tool button integrated directly into the header.

### 2.7. Automated Interactive HTML USB Manuals (Offline On-Drive Documentation)
- Every generated payload USB now includes a self-contained, responsive, multi-page HTML manual (`*.html`).
- Completely offline, styled with Aero Cyber Obsidian themes.
- Explains safety parameters, step-by-step instructions, and assurances regarding OEM vehicle systems (HVAC, steering controls, reverse camera).

---

## 3. Deep-Dive: Bug Fixes & Platform Stabilization

### 3.1. Resolved Android 8.1 Native Library Alignment (`res=-2 / INSTALL_FAILED_INVALID_APK`)
* **Bug:** Android 8.1 Oreo on Qualcomm Snapdragon 450/625 refused to extract or run certain third-party APKs containing native `.so` binaries, throwing `INSTALL_FAILED_INVALID_APK` with return code `-2`.
* **Root Cause:** APK files built with newer Android SDKs had 16KB or unaligned native libraries inside `lib/armeabi-v7a/`, whereas Android 8.1's PackageManager requires strict 4096-byte page alignment for mmap.
* **Fix (`apk_engine.py`):**
  - Implemented automatic 4KB page-alignment verification and correction (`zipalign -p 4`).
  - Added automated decompression of native `.so` libraries into target system lib paths (`/system/priv-app/<Pkg>/lib/arm/`).

### 3.2. Eliminated PKCS#9 SMIMECapability Verification Crash (`sign_apk`)
* **Bug:** Apps signed by the suite failed package verification on the car with signature parsing errors.
* **Root Cause:** Modern Python cryptography tools appended PKCS#9 `SMIMECapability` authenticated attributes to signed CMS signatures. Android 8.1's `StrictJarVerifier` rejects unrecognized PKCS#9 attributes.
* **Fix (`apk_engine.py`):**
  - Enforced `NoAttributes` during CMS signature generation, generating RFC-compliant V1 JAR signatures seamlessly verified by Oreo.

### 3.3. Fixed Google Play Store "Download Pending" Infinite Loop
* **Bug:** After injecting GMS, Play Store opened but got permanently stuck on "Download pending... 0%".
* **Root Cause:** Android SetupWizard flags were missing; the system considered the device unprovisioned and held background download jobs.
* **Fix (`install_gms.py`):**
  - Added explicit configuration flags during installation:
    `settings put global device_provisioned 1`
    `settings put secure user_setup_complete 1`

### 3.4. Overhauled Backup & Restore Engine (Aero Restore v2.0)
* **Bug:** Restoring an archive previously led to package crashing and permission denials.
* **Root Causes & Solutions (`restore.py` & `backup.py`):**
  1. **Dynamic UID Remapping:** Restored app data directories in `/data/data/<pkg>` previously had stale Linux UIDs from the source car. v2.0 dynamically queries `packages.list` and `dumpsys package` to chown files to the target vehicle's exact UID.
  2. **SQLite WAL/SHM Corruption Protection:** Automatically removes stale `-wal` and `-shm` write-ahead logs prior to database restore.
  3. **Late Settings XML Injection:** Re-injects `appwidgets.xml` and `settings_*.xml` immediately before hardware reboot to prevent `system_server` from overwriting them with in-memory state on shutdown.
  4. **Direct Boot (`user_de`) Coverage:** Fully archives and restores `/data/user_de/0/` to ensure Direct Boot aware services (such as Gboard and SettingsProvider) retain state before initial unlock.
  5. **Kernel Hard Reboot:** Executes kernel hard reboot (`setprop sys.powerctl reboot`) to bypass system shutdown memory flushes.

### 3.5. Gboard Customizations & Privacy Sanitization
* **Enhancement:** Gboard preferences (Dark Theme, Arabic-first language layout, Number Row toggle, and Full-Width / Non-Split mode) are automatically captured and injected.
* **Privacy Guarantee:** Stripped all user typing history (`UserHistory.*.dict`), custom dictionary logs, and contacts databases to guarantee 100% privacy with zero credential or personal word leakage.

### 3.6. Prevented Multi-Execution / Reboot Loops (`process_complete` Flag)
* **Bug:** Leaving the USB in the car caused the update script to run repetitively on every ignition cycle.
* **Fix:** Introduced an atomic marker file (`process_complete`) created at the end of execution. All payloads check for this file on startup and exit cleanly if the operation already finished.

### 3.7. Multi-Stage State Machine Architecture (`.state/` Checkpoint Engine)
* **Problem:** Operations requiring hardware reboot (such as GMS framework injection and Zero-Trace Factory Reset) historically interrupted composite batch jobs, preventing downstream steps like post-boot auto-launch, Gboard preference setup, and launcher freezing from executing. Technicians were forced to use 2 to 3 separate USB drives sequentially.
* **Architectural Breakthrough:**
  - Introduced the **Multi-Stage State Machine Architecture** running sequentially from a **single USB drive**.
  - Engineered the **State Checkpoint Engine** residing in `$USB_PATH/update/.state/`.
  - Checkpoint markers (`stage_backup.done`, `stage_reset.done`, `stage_installs.done`, etc.) persist seamlessly across system reboots.
  - Scripts dynamically inspect checkpoint flags on every boot:
    - **Stage 0 (Pre-Flight Backup):** Performs non-destructive 1:1 or community snapshot directly to `$USB_PATH/Backup/` without reboot.
    - **Stage 1 (Factory Reset):** Performs factory wipe of `/data` partitions and auto-healing of `/system/`, then triggers an immediate atomic hardware reboot without marking `process_complete`.
    - **Stage 2 (Installs & Mods):** Deploys GMS system apps, user apps, HVAC enhanced bar, and CAN-Bus modifications, then reboots to register package changes.
    - **Stage 3 (Post-Boot Execution):** Actively polls `getprop sys.boot_completed` until it equals `1` with a 60-second watchdog timeout, pauses for a 5-second stabilization window, then executes post-boot actions before setting the terminal `process_complete` flag.

### 3.8. Post-Boot Real UID Gboard Ingestion & Persistent Stock Launcher Freeze
* **Gboard UID Resolution:** Gboard data injection (`/data/data/com.google.android.inputmethod.latin`) previously failed if executed before reboot because `PackageManagerService` had not yet created an entry in `/data/system/packages.list`. Deferring to Stage 3 guarantees a legitimate, live UID exists, preventing permission denials and package crashes.
* **Persistent OEM Launcher Freeze:** Disabling the stock launcher (`com.qinggan.app.launcher`) prior to reboot caused the OEM boot watchdog to force-enable it upon startup. Executing `pm disable` in Stage 3 after `sys.boot_completed=1` permanently freezes the OEM launcher without watchdog interference.

---

## 4. Summary of Codebase Metrics

- **Total Test Cases:** 33 automated test suites across payloads, APK engine, i18n, and UI bridges.
- **Languages Supported:** 4 (AR, EN, RU, ZH).
- **Core Engine Modules:** 13 specialized payload generators (`src/payloads/`).
- **Vehicle Whitelist:** 69 factory priv-apps and 33 factory apps protected against accidental removal.
- **Safety Standard:** Zero-tamper lock protecting factory HVAC, audio matrix, reverse camera, and steering wheel CAN-Bus controls.
