# Aero Automotive Suite v2.0 🚗⚡

> **Industrial-Grade In-Vehicle Infotainment (IVI) Management & Engineering Studio for Dongfeng Shine / Aeolus D53 (Qualcomm MSM8953 Snapdragon 450/625, Android 8.1.0 Oreo API 27).**

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PySide6 / Qt6](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://www.qt.io/)
[![Platform](https://img.shields.io/badge/Platform-Dongfeng%20Shine%20AAOS%208.1-00D2FF?style=for-the-badge&logo=android&logoColor=white)](https://developer.android.com/)
[![Architecture](https://img.shields.io/badge/Architecture-Clean%20Architecture%20%26%20SOLID-FF9F43?style=for-the-badge)](https://en.wikipedia.org/wiki/Clean_architecture)

---

## 🌟 English Overview

**Aero Automotive Suite v2.0** is an all-in-one desktop workstation designed to provision, customize, backup, and modernize Android Automotive OS headunits (Dongfeng Shine / Aeolus D53). It enables technicians and vehicle owners to execute complex kernel-level modifications, install privileged navigation systems, inject the Google Ecosystem, and toggle CAN-Bus comfort features—completely offline via automated USB payload delivery.

### 🚀 Key Capabilities

1. **Multi-Action Execution Basket & Pipeline (`BasketManager`):**
   - Stage multiple operations simultaneously (e.g., install apps + toggle CAN-Bus tweaks + inject Google Services + deploy Aero Bar).
   - Generates a single, atomic, idempotent shell payload (`update/custom_rep.sh`) with strict execution order and automatic reboot hooks.

2. **Full 10-Component Google Ecosystem Deployment:**
   - Seamlessly injects Google Services Framework (GSF), Google Play Services, Play Store, Google Files, Gboard (with bilingual layout and preferences), Google Speech Services, Maps, and Chrome directly into `/system/priv-app/`.
   - Automated setup completion flags (`device_provisioned`, `user_setup_complete`) and instant first-boot account sign-in.

3. **Direct CAN-Bus Vehicle Tweaks (No OBD-II Dongle Required):**
   - Direct integration with Dongfeng's `ICanBusService` (`qg.canbus` Binder IPC).
   - Configures: Welcome Light, Seat Welcome / Easy Entry, Speed-Sensing Auto Door Lock (15 km/h), Auto Park & Unlock on Engine Off, and Electric Liftgate safety lock.

4. **Aero Bar & Navigation Dock Deployment:**
   - Deploys the modern single-row (88px) navigation dock, hides legacy dual-row OEM bars, and configures accessibility and overlay permissions automatically.

5. **1:1 Bit-Exact System Clone, Backup & Restore:**
   - Preserves POSIX file permissions, extended attributes, symlinks, and original SELinux contexts.
   - Backs up partitions, `/data/`, APKs, settings databases, and vehicle calibration data.

6. **High-Performance Dark GUI (PySide6 / Qt6):**
   - GPU-accelerated responsive interface matching automotive cockpit design tokens (`#070A0E`, Cyan `#00D2FF`).
   - Full internationalization across **7 languages**: Arabic (full RTL), English, Russian, Chinese, Spanish, Portuguese, and Vietnamese.
   - Built-in FAT32 formatter, live USB detection, and real-time execution terminal.

---

## 🌐 نظرة عامة باللغة العربية (Arabic Summary)

برنامج **Aero Automotive Suite v2.0** هو بيئة عمل هندسية متكاملة مخصصة لشاشات سيارات **دونغ فينغ شاين (Dongfeng Shine / Aeolus D53)**، تتيح لمالكي السيارات وفنيي التعديل إجراء جميع العمليات المتقدمة على نظام السيارة بضغطة زر وبدون الحاجة لأجهزة فحص باهظة الثمن أو فتح الـ Root يدوياً:

### أهم المميزات في الإصدار 2.0:
- **سلة الأوامر المجمعة (Execution Basket):** إمكانية اختيار عدة عمليات مختلفة (تثبيت تطبيقات + تفعيل خدمات جوجل + تعديل خصائص السيارة + تنصيب Aero Bar) ودمجها تلقائياً في فلاشة واحدة عبر سكربت مجمع فائق الأمان.
- **منظومة خدمات جوجل المتكاملة (10 خدمات):** تثبيت متجر Play Store، كيبورد Gboard، خدمات التعرف الصوتي، الخرائط، ومتصفح Chrome كخدمات نظام رسمية ومحمية.
- **تعديل خصائص السيارة عبر الـ CAN-Bus:** قفل الأبواب التلقائي مع السرعة، ترحيب المقعد الذكي عند الدخول، إضاءة الترحيب، وتفعيل الهاند بريك تلقائياً عند إطفاء المحرك.
- **تثبيت بار التحكم الذكي (Aero Bar):** دمج شريط الملاحة الرشيق الموفر لمساحة الشاشة مع تفعيل كافة الصلاحيات بدون تدخل المستخدم.
- **واجهة عصرية بلغات متعددة ودعم كامل للعربية (RTL):** واجهة رسومية سريعة مبنية بـ PySide6 تدعم اللغة العربية بالكامل وتهيئة الفلاشات بصيغة FAT32 تلقائياً.

---

## 📁 Project Architecture & Structure

```
Aero_Suite/
├── main.py                     # Application entry point & Qt lifecycle manager
├── build_release.ps1           # Standalone executable packaging script (PyInstaller)
├── src/
│   ├── core/                   # State store, central paths, i18n engine, constants
│   ├── controllers/            # Hardware USB controller & payload orchestrator
│   ├── payloads/               # Atomic shell generators (GMS, AeroBar, CAN-Bus, Backup)
│   ├── services/               # Execution basket & multi-action transaction engine
│   ├── ui/                     # PySide6 components, dark theme, and views
│   │   ├── components/         # Reusable cards, navigation bar, terminal console
│   │   ├── views/              # Feature screens (Apps, Tweaks, GMS, Bar, Backup, Tools)
│   │   └── assets/             # Vector icons, payment logos, and illustrations
│   └── locales/                # External JSON string catalogs (ar, en, ru, zh, es, pt, vi)
└── docs/                       # Technical references, guides, and changelog
```

---

## 🛠️ Requirements & Setup

### Prerequisites
- Python 3.11 or 3.12 (64-bit)
- Windows 10/11 (or Linux with Qt6 support)

### Installation
```bash
# Clone the repository
git clone https://github.com/YourUsername/Aero-Suite.git
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

### Building Standalone Executable (.exe)
```powershell
powershell -ExecutionPolicy Bypass -File .\build_release.ps1
```

---

## 👤 Author & Support

- **Lead Engineer:** Abdelrhman Hamdy
- **Contact:** abdellrhman.hamdi@gmail.com | +201095449725
- **Vehicle Community:** Dongfeng Shine / Aeolus D53 Global Owners Club

---

## 📄 License & Terms

Proprietary Software — Developed specifically for the Aero Automotive ecosystem. Unauthorized distribution or reverse engineering of binary components is strictly prohibited.
