#!/bin/sh

# 日志文件路径
LOG_FILE="/tmp/battery_discharge_log"

# 检查日志目录
LOG_DIR=$(dirname "$LOG_FILE")
[ ! -d "$LOG_DIR" ] && mkdir -p "$LOG_FILE"

echo "Monitoring for discharge status..."
echo "Press Ctrl+C to stop."

# 循环检测直到出现放电状态
while true; do
    # 检查电池状态
    STATUS=$(cat /sys/class/power_supply/cw221X-bat/status 2>/dev/null)

    if [ "$STATUS" = "Discharging" ]; then
        LEVEL=$(cat /sys/class/power_supply/cw221X-bat/capacity 2>/dev/null)
        TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

        # 记录放电状态和电量
        echo "[$TIMESTAMP] Discharging: $LEVEL%" > "$LOG_FILE"
        echo "Discharge detected: $LEVEL%"
        break  # 检测到放电状态后退出循环
    fi

    sleep 1  # 每秒检测一次
done