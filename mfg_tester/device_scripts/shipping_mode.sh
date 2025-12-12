#!/bin/sh

echo "Shipping mode discharge monitoring..."

while true; do
    LEVEL=$(cat /sys/class/power_supply/cw221X-bat/capacity 2>/dev/null)
    echo "Battery level: $LEVEL%"

    if [ "$LEVEL" -le 80 ]; then
        echo "Reached 80%, powering off..."
        poweroff
        exit 0
    fi

    sleep 5
done