# Aero Automotive Suite v2.0 🚗⚡

> **Industrial-Grade In-Vehicle Infotainment (IVI) Management & Engineering Studio for Dongfeng Shine / Aeolus D53 (Qualcomm MSM8953 Snapdragon 450/625, Android 8.1.0 Oreo API 27).**

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PySide6 / Qt6](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://www.qt.io/)
[![Platform](https://img.shields.io/badge/Platform-Dongfeng%20Shine%20AAOS%208.1-00D2FF?style=for-the-badge&logo=android&logoColor=white)](https://developer.android.com/)
[![Architecture](https://img.shields.io/badge/Architecture-Clean%20Architecture%20%26%20SOLID-FF9F43?style=for-the-badge)](https://en.wikipedia.org/wiki/Clean_architecture)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)](https://github.com/)

---

## 1. System Overview

**Aero Automotive Suite v2.0** is an all-in-one desktop workstation designed to provision, customize, backup, and modernize Android Automotive OS headunits (Dongfeng Shine / Aeolus D53). It enables technicians and vehicle owners to execute complex kernel-level modifications, install privileged navigation systems, inject the Google Ecosystem, and toggle CAN-Bus comfort features—completely offline via automated USB payload delivery.

Built using **Python 3.12** and **PySide6 (Qt6)** under strict **Clean Architecture** and **SOLID principles**, it decouples UI presentation, transactional service orchestration, hardware USB device management, and idempotent shell payload generation.

---

## 2. Key Capabilities

### 1. Multi-Action Execution Basket & Pipeline (`BasketManager`)
- **Heterogeneous Batching:** Stage multiple independent operations into an execution queue (e.g., Install User Apps + Toggle CAN-Bus Tweaks + Inject Google Services + Deploy Aero Bar).
- **Idempotent Shell Synthesis:** The unified **`BashBuilder`** engine compiles all staged pipeline items into a single, cohesive, atomic shell script (`update/custom_rep.sh`) with strict execution order safety:
  1. System remounts & pre-flight integrity check
  2. CAN-Bus vehicle parameters configuration
  3. Custom system privileged applications (`/system/priv-app/`)
  4. Standard user applications installation (`pm install`)
  5. Launcher and system UI state transitions
  6. Permissions granting and settings injection
  7. Automated post-boot application launches (`Auto-Launch`)
  8. Cache sync and safe atomic kernel reboot

### 2. Full 10-Component Google Ecosystem Deployment
Seamlessly injects the complete Google Android stack tailored specifically to Qualcomm MSM8953 Android 8.1 without bootloops or missing shared libraries:
- **Core Framework:** Google Services Framework (GSF), Google Account Manager, Google Play Services (GMS), and Google Play Store.
- **Productivity & Input:** Files by Google (Storage Manager with full storage permissions), Gboard (bilingual Arabic/English layout with automated preference configuration), and Google Speech Services (TTS & Voice Recognition XML).
- **Navigation & Web:** Google Maps Navigation and Google Chrome Stable.
- **First-Boot Automation:** Automatically configures `device_provisioned` and `user_setup_complete` flags, immediately launching Play Store upon startup for account sign-in.

### 3. Direct CAN-Bus Vehicle Tweaks (No OBD-II Dongle Required)
Direct integration with Dongfeng's `ICanBusService` (`qg.canbus` Binder IPC) to configure factory body control parameters:
- **Welcome Light:** Exterior courtesy lighting upon approaching the vehicle with the smart key.
- **Seat Welcome / Easy Entry:** Slides driver electric power seat rearward upon opening the door, restoring driving position upon ignition.
- **Speed-Sensing Auto Door Lock:** Automatically locks all doors upon exceeding 15 km/h.
- **Auto Park & Unlock on Engine Off:** Automatically engages Electric Parking Brake (EPB) and unlocks doors when turning off the engine.
- **Electric Liftgate Safety Lock:** Prevents accidental rear trunk activation during vehicle motion.

### 4. Aero Bar & Navigation Dock Deployment
- Automates deployment of the single-row (88px) modern navigation dock into `/system/priv-app/AeroBar/`.
- Pre-grants overlay and accessibility permissions, configures keep-alive policies, and hides the legacy OEM dual-row navigation bar.

### 5. 1:1 Bit-Exact System Clone, Backup & Restore
- Preserves full POSIX file permissions, extended attributes, symlinks, and original SELinux contexts.
- Comprehensive backup and restore of system partitions, user applications (`/data/app/`), application databases, and vehicle calibrations.

### 6. High-Performance Dark GUI (PySide6 / Qt6)
- GPU-accelerated responsive interface matching automotive cockpit design tokens (`#070A0E`, Cyan `#00D2FF`).
- **7 Supported Languages:** English, Arabic (full bidirectional RTL layout), Russian, Chinese, Spanish, Portuguese, and Vietnamese.
- Built-in automated FAT32 filesystem formatter, live USB drive detection, and real-time execution terminal.

---

## 3. Architecture & Directory Structure

```
Aero_Suite/
├── main.py                     # Application entry point & Qt lifecycle manager
├── build_release.ps1           # Standalone executable packaging script (PyInstaller)
├── src/
│   ├── core/                   # State store, central paths, i18n engine, constants
│   │   ├── paths.py            # Centralized path resolution across dev and frozen environments
│   │   ├── state.py            # Reactive state management
│   │   └── i18n.py             # Multi-language internationalization loader
│   ├── controllers/            # Hardware USB controller & payload orchestrators
│   ├── payloads/               # Atomic shell generators (GMS, AeroBar, CAN-Bus, Backup)
│   │   ├── bash_builder.py     # Reusable shell snippet synthesis engine
│   │   ├── install_gms.py      # Google ecosystem deployment payload
│   │   ├── install_hvac_bar.py # Aero Bar deployment payload
│   │   └── vehicle_tweaks.py   # CAN-Bus vehicle parameters payload
│   ├── services/               # Execution basket & multi-action transaction engine
│   ├── ui/                     # PySide6 components, dark theme, and views
│   │   ├── components/         # Reusable cards, navigation bar, terminal console
│   │   ├── views/              # Feature screens (Apps, Tweaks, GMS, Bar, Backup, Tools)
│   │   └── assets/             # Vector icons, payment logos, and illustrations
│   └── locales/                # External JSON string catalogs (en, ar, ru, zh, es, pt, vi)
└── docs/                       # Technical references, guides, and changelog
```

---

## 4. Requirements & Installation

### Prerequisites
- Python 3.11 or 3.12 (64-bit)
- Windows 10/11 (or Linux with Qt6 support)

### Installation
```bash
# Clone the repository
git clone https://github.com/abdofx55/Aero-Suite.git
cd Aero-Suite

# Create a virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install required dependencies
pip install PySide6 psutil
```

### Running the Suite
```bash
python main.py
```

### Packaging Standalone Executable (.exe)
```powershell
powershell -ExecutionPolicy Bypass -File .\build_release.ps1
```
The compiled, standalone executable will be generated in `dist/AeroSuite.exe`.

---

## 5. Author & Support

- **Lead Engineer:** Abdelrhman Hamdy
- **Contact:** abdellrhman.hamdi@gmail.com | +201095449725
- **Vehicle Community:** Dongfeng Shine / Aeolus D53 Global Owners Club

---

## 6. License & Terms

Proprietary Software — Developed specifically for the Aero Automotive ecosystem. All rights reserved.
