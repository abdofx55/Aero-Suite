"""
constants.py — Central system constants, whitelists, and banners for Aero Suite.
Calibrated for Dongfeng Shine (Aeolus D53) Android 8.1 / 9 / 10 IVI Systems.
"""

import os
import sys

from theme import SIGNATURE_BANNER, DEVELOPER_NAME, DEVELOPER_EMAIL, DEVELOPER_PHONE

def get_base_dir() -> str:
    if getattr(sys, 'frozen', False) or "__compiled__" in globals() or hasattr(sys, '__nuitka_version__'):
        if sys.argv and sys.argv[0]:
            candidate = os.path.dirname(os.path.abspath(sys.argv[0]))
            if os.path.exists(os.path.join(candidate, "apks")):
                return candidate
        if sys.executable:
            candidate = os.path.dirname(os.path.abspath(sys.executable))
            if os.path.exists(os.path.join(candidate, "apks")):
                return candidate
        if sys.argv and sys.argv[0]:
            return os.path.dirname(os.path.abspath(sys.argv[0]))
        return os.path.dirname(os.path.abspath(sys.executable))

    cur_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(cur_dir)
    return os.path.dirname(src_dir) if os.path.basename(src_dir).lower() == "src" else src_dir

BASE_DIR = get_base_dir()
APKS_DIR = os.path.join(BASE_DIR, "apks")
GMS_DIR = os.path.join(APKS_DIR, "google_services")
SYSTEM_MODS_DIR = os.path.join(APKS_DIR, "system_mods")
HVAC_MOD_APK = os.path.join(SYSTEM_MODS_DIR, "SystemUI_mod_160px.apk")
HVAC_STOCK_APK = os.path.join(SYSTEM_MODS_DIR, "SystemUI_stock_200px.apk")
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")
FACTORY_BACKUP_DIR = os.path.join(BASE_DIR, "FactoryBackup")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

for d in [APKS_DIR, SYSTEM_MODS_DIR, BACKUPS_DIR, LOGS_DIR]:
    os.makedirs(d, exist_ok=True)

# ---------------------------------------------------------------------------
# Dongfeng Shine Factory Whitelist (69 priv-apps & 33 apps)
# ---------------------------------------------------------------------------
FACTORY_PRIV_APPS = [
    "ArielCallVechileFunction-release-signed", "AudioPolicy-release", "BackupRestoreConfirmation",
    "BlockedNumberProvider", "BluetoothPhone-release-signed", "BluetoothService-release",
    "CallLogBackup", "CanBusService-release", "CarPlayApp-release", "CarPlayService-release",
    "CarrierConfig", "CarSignalService-release", "CellBroadcastReceiver", "CNEService",
    "ContactsProvider", "CtsShimPrivPrebuilt", "DabPlayer", "DefaultContainerService",
    "DownloadProvider", "dpmserviceapp", "EasyConnect.release", "EasyService-release-signed",
    "EmergencyInfo", "ExternalStorageProvider", "ExtServices", "FactoryTest-release-signed",
    "FusedLocation", "iAP2Service-release", "InputDevices", "KeyManagerService-release",
    "LastMemory-release", "Launcher-release-signed", "Mms", "MmsService", "Music-release-signed",
    "NuNavbar", "opentouch", "OTAService-release", "PackageInstaller", "PowerManager-release",
    "Provision", "PushMessageApp-release-signed", "qcrilmsgtunnel", "QGBus-release",
    "QGIME-release", "QGMediaProvider-release", "QGSettingProvider-release",
    "QGTtsService-release-signed", "QingLinkProxyService-release", "Radio-release-signed",
    "RemoteDebug-release", "Setting-release-signed", "Settings", "SettingsProvider",
    "SettingsShortcut", "SharedStorageBackup", "Shell", "SnapdragonCamera", "StatementService",
    "StorageManager", "SystemPolicy-release", "SystemUI-release-signed", "TBoxService-release",
    "Telecom", "TelephonyProvider", "TeleService", "TSPService-release", "TunerService-release",
    "Vehicle-release-signed"
]

FACTORY_APPS = [
    "access-qcom-logkit", "AntHalService", "BasicDreams", "Bluetooth", "BluetoothExt",
    "BluetoothMidiService", "CallFeaturesSetting", "CarrierDefaultApp", "CertInstaller",
    "CompanionDeviceManager", "ConfURIDialer", "CtsShimPrebuilt", "datastatusnotification",
    "embms", "Exchange2", "ExtShared", "FidoCryptoService", "HTMLViewer", "ims", "imssettings",
    "KeyChain", "NetworkSetting", "NuNavbar", "QtiTelephonyService", "remotesimlockservice",
    "SimSettings", "Stk", "uceShimService", "uimlpaservice", "UserDictionaryProvider",
    "WallpaperBackup", "webview", "WfdService"
]

FACTORY_LAUNCHER_PKG = "com.qinggan.app.launcher"

# GMS Package Identifier Order for Clean Setup
GMS_PACKAGES_SEQUENCE = [
    {"name": "Google Services Framework", "pkg": "com.google.android.gsf", "order": 1},
    {"name": "Google Account Manager", "pkg": "com.google.android.gsf.login", "order": 2},
    {"name": "Google Play Services", "pkg": "com.google.android.gms", "order": 3},
    {"name": "Google Play Store", "pkg": "com.android.vending", "order": 4},
    {"name": "Files by Google", "pkg": "com.google.android.apps.nbu.files", "order": 5}
]

# Complete GMS Purge Package List (Used identically across install, clean reinstall, and uninstall) - Exactly 10 packages
GMS_FULL_PURGE_PACKAGES = [
    "com.google.android.gsf",
    "com.google.android.gsf.login",
    "com.google.android.gms",
    "com.android.vending",
    "com.google.android.apps.nbu.files",
    "com.google.android.googlequicksearchbox",
    "com.google.android.tts",
    "com.google.android.inputmethod.latin",
    "com.android.chrome",
    "com.google.android.apps.maps",
]

# Complete System Priv-App & App Cleanup Patterns for GMS
GMS_FULL_PRIVAPP_PATTERNS = [
    "1_GSF*", "2_GSF*", "3_GMS*", "4_PlayStore*", "5_Google*", "6_Google*", "7_Google*",
    "GSF*", "GMS*", "PlayStore*", "playstore*", "Phonesky*", "phonesky*", "vending*",
    "GooglePlayServices*", "GoogleServicesFramework*", "GoogleLoginService*",
    "*Search*", "*quicksearch*",
    "*GoogleFiles*", "*Google_Files*", "*GoogleSpeech*", "*speech*", "*tts*",
    "Google*"
]

# Canonical execution order for multi-payload batch execution (Basket & Unified Manual)
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
    "fetch_logs": 75,           # Diagnostic dump (executed post-boot before final launch)
    "open_settings": 80,
    "open_app": 80,
    "reboot_screen": 90         # Very end
}



