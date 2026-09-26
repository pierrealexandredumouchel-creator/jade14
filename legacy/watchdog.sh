#!/bin/bash

# /opt/jade14/watchdog.sh
LOG="/var/log/jade14_watchdog.log"
BOT_DIR="/opt/jade14/jade14"
BOT_FILE="jade14.py"

while true; do
    if ! pgrep -f "$BOT_FILE" >/dev/null; then
        echo "$(date) : JADE14 était down — relance..." >> "$LOG"
        cd "$BOT_DIR"
        python3 "$BOT_FILE" &
        sleep 5
        echo "$(date) : JADE14 relancé." >> "$LOG"
    fi
    sleep 30
done
