#!/system/bin/sh
# ============================================================
# AERO SUITE — FACTORY APPS EXTRACTOR & BACKUP HARVESTER
# Dongfeng Shine (Aeolus D53) Infotainment System
# Developed by Abdelrhman Hamdy - Senior Software Engineer
# ============================================================

# 1. Locate USB Mount Point
USB_PATH=""
for dir in /storage/* /mnt/media_rw/* /mnt/usb* /storage/usb*; do
    if [ -f "$dir/update/custom_rep.sh" ]; then
        USB_PATH="$dir"
        break
    fi
done
if [ -z "$USB_PATH" ]; then
    USB_PATH=$(dirname $(dirname "$0"))
fi

LOG_FILE="$USB_PATH/factory_extract.log"
echo "=== FACTORY APPS EXTRACTION START ===" > "$LOG_FILE"
date >> "$LOG_FILE"
echo "USB detected at: $USB_PATH" >> "$LOG_FILE"

DEST_PRIV="$USB_PATH/FactoryBackup/priv-app"
DEST_APP="$USB_PATH/FactoryBackup/app"
mkdir -p "$DEST_PRIV" "$DEST_APP" >> "$LOG_FILE" 2>&1

# Show initial toast notification on head unit
am broadcast -a com.android.systemui.demo -e command toast -e text "Aero Suite: Extracting Factory Apps... Please wait!" >/dev/null 2>&1

# 2. Extract Whitelisted priv-apps
echo "--- Extracting Whitelist Priv-Apps ---" >> "$LOG_FILE"
PRIV_LIST="ArielCallVechileFunction-release-signed AudioPolicy-release BackupRestoreConfirmation BlockedNumberProvider BluetoothPhone-release-signed BluetoothService-release CallLogBackup CanBusService-release CarPlayApp-release CarPlayService-release CarrierConfig CarSignalService-release CellBroadcastReceiver CNEService ContactsProvider CtsShimPrivPrebuilt DabPlayer DefaultContainerService DownloadProvider dpmserviceapp EasyConnect.release EasyService-release-signed EmergencyInfo ExternalStorageProvider ExtServices FactoryTest-release-signed FusedLocation iAP2Service-release InputDevices KeyManagerService-release LastMemory-release Launcher-release-signed Mms MmsService Music-release-signed NuNavbar opentouch OTAService-release PackageInstaller PowerManager-release Provision PushMessageApp-release-signed qcrilmsgtunnel QGBus-release QGIME-release QGMediaProvider-release QGSettingProvider-release QGTtsService-release-signed QingLinkProxyService-release Radio-release-signed RemoteDebug-release Setting-release-signed Settings SettingsProvider SettingsShortcut SharedStorageBackup Shell SnapdragonCamera StatementService StorageManager SystemPolicy-release SystemUI-release-signed TBoxService-release Telecom TelephonyProvider TeleService TSPService-release TunerService-release Vehicle-release-signed"
P_COUNT=0
for app in $PRIV_LIST; do
    SRC="/system/priv-app/$app"
    if [ -d "$SRC" ]; then
        echo "Copying priv-app: $app" >> "$LOG_FILE"
        mkdir -p "$DEST_PRIV/$app"
        cp -r "$SRC/"* "$DEST_PRIV/$app/" >> "$LOG_FILE" 2>&1
        P_COUNT=$((P_COUNT + 1))
    fi
done

# 3. Extract Whitelisted standard apps
echo "--- Extracting Whitelist Apps ---" >> "$LOG_FILE"
APP_LIST="access-qcom-logkit AntHalService BasicDreams Bluetooth BluetoothExt BluetoothMidiService CallFeaturesSetting CarrierDefaultApp CertInstaller CompanionDeviceManager ConfURIDialer CtsShimPrebuilt datastatusnotification embms Exchange2 ExtShared FidoCryptoService HTMLViewer ims imssettings KeyChain NetworkSetting NuNavbar QtiTelephonyService remotesimlockservice SimSettings Stk uceShimService uimlpaservice UserDictionaryProvider WallpaperBackup webview WfdService"
A_COUNT=0
for app in $APP_LIST; do
    SRC="/system/app/$app"
    if [ -d "$SRC" ]; then
        echo "Copying app: $app" >> "$LOG_FILE"
        mkdir -p "$DEST_APP/$app"
        cp -r "$SRC/"* "$DEST_APP/$app/" >> "$LOG_FILE" 2>&1
        A_COUNT=$((A_COUNT + 1))
    fi
done

# 4. Flush cache to USB drive
sync

TOTAL=$((P_COUNT + A_COUNT))
echo "=== EXTRACTION FINISHED ===" >> "$LOG_FILE"
echo "Total Priv-Apps copied: $P_COUNT" >> "$LOG_FILE"
echo "Total Apps copied: $A_COUNT" >> "$LOG_FILE"
echo "Grand Total: $TOTAL apps" >> "$LOG_FILE"
date >> "$LOG_FILE"

# 5. Notify user on screen and with chime sound (NO REBOOT)
am broadcast -a com.android.systemui.demo -e command toast -e text "Extraction Done! $TOTAL Apps Copied. Safe to unplug USB!" >/dev/null 2>&1

for tone in /system/media/audio/ui/Effect_Tick.ogg /system/media/audio/notifications/*.ogg; do
    if [ -f "$tone" ]; then
        stagefright -a -o "$tone" >/dev/null 2>&1 || tinyplay "$tone" >/dev/null 2>&1
        break
    fi
done