"""
constants.py — Central system constants, whitelists, and banners for Aero Suite.
Calibrated for Dongfeng Shine (Aeolus D53) Android 8.1 / 9 / 10 IVI Systems.
"""

from theme import SIGNATURE_BANNER, DEVELOPER_NAME, DEVELOPER_EMAIL, DEVELOPER_PHONE

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
    {"name": "Google Play Services", "pkg": "com.google.android.gms", "order": 2},
    {"name": "Google Account Manager", "pkg": "com.google.android.gsf.login", "order": 3},
    {"name": "Google Play Store", "pkg": "com.android.vending", "order": 4}
]
