#!/bin/sh

# 日志文件路径
LOG_FILE="/mnt/sdcard/battery_log"
INTERVAL=60  # 检查间隔（秒），默认1分钟

# 检查日志目录是否存在，不存在则创建
LOG_DIR=$(dirname "$LOG_FILE")
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
fi

echo "Starting battery monitoring. Logging to: $LOG_FILE"
echo "Press Ctrl+C to stop."

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

    # 检查电池是否存在
    BATTERY_PRESENT=$(cat /sys/class/power_supply/cw221X-bat/present 2>/dev/null)

    if [ "$BATTERY_PRESENT" = "1" ]; then
        # 获取电池信息
        BATTERY_LEVEL=$(cat /sys/class/power_supply/cw221X-bat/capacity 2>/dev/null)
        BATTERY_STATUS=$(cat /sys/class/power_supply/cw221X-bat/status 2>/dev/null)

        if [ -n "$BATTERY_LEVEL" ] && [ -n "$BATTERY_STATUS" ]; then
            echo "[$TIMESTAMP] Battery: $BATTERY_LEVEL% - Status: $BATTERY_STATUS" >> "$LOG_FILE"
        else
            echo "[$TIMESTAMP] Error: Failed to read battery information" >> "$LOG_FILE"
        fi
    else
        echo "[$TIMESTAMP] Battery not present" >> "$LOG_FILE"
    fi

    sleep $INTERVAL
done