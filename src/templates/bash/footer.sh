sync
echo "=== AERO PROCESS STATUS: {{ success_status }} ===" >> "{{ target_log }}"
date >> "{{ target_log }}"

# Record vehicle completion on USB registry (Zero trace on car filesystem!)
mkdir -p "$USB_PATH/completed_cars/${CAR_SERIAL}" 2>/dev/null
touch "$USB_PATH/completed_cars/${CAR_SERIAL}/completed.done"
touch "$USB_PATH/completed_cars/${CAR_SERIAL}.done"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] MODEL: $CAR_MODEL | SERIAL: $CAR_SERIAL | STATUS: {{ success_status }}" >> "$USB_PATH/completed_cars/registry.txt"
sync
{% if with_reboot %}
echo "{{ reboot_msg }}" >> "{{ target_log }}"
sync
sec={{ reboot_delay }}
while [ $sec -gt 0 ]; do
    echo "System will restart after $sec seconds..." >> "{{ target_log }}"
    sleep 1
    sec=$((sec - 1))
done
sync
(sleep 1; setprop sys.powerctl reboot || reboot -f || reboot) &
{% else %}
sync
{% endif %}
