#!/system/bin/sh
# ==========================================
# AERO SUITE — {{ title }}
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

CAR_DIR="$USB_PATH/completed_cars/${CAR_SERIAL}"
mkdir -p "$CAR_DIR" 2>/dev/null
STATE_DIR="$CAR_DIR"
LOG_FILE="$CAR_DIR/{{ log_filename }}"

if [ -f "$CAR_DIR/completed.done" ] || [ -f "$USB_PATH/completed_cars/${CAR_SERIAL}.done" ]; then
    echo "=== CAR [$CAR_MODEL | $CAR_SERIAL] ALREADY PROVISIONED BY THIS USB — SKIPPING ===" >> "$LOG_FILE"
    exit 0
fi

if [ ! -f "$LOG_FILE" ]; then
    echo "=== AERO {{ title }} START ===" > "$LOG_FILE"
else
    echo "" >> "$LOG_FILE"
    echo "=== AERO {{ title }} RESUMED ACROSS REBOOT ===" >> "$LOG_FILE"
fi
echo "Vehicle Model:  $CAR_MODEL" >> "$LOG_FILE"
echo "Vehicle Serial: $CAR_SERIAL" >> "$LOG_FILE"
date >> "$LOG_FILE"
