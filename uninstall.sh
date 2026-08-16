#!/bin/bash
set -euo pipefail

D=/sys/bus/iio/devices/iio:device0

sudo systemctl stop inputplumber.service || true
sudo rm -f /etc/systemd/system/inputplumber.service.d/20-pr612-buffered-imu.conf
sudo rm -f /etc/systemd/system/inputplumber.service.d/10-apex-bmi260-trigger.conf
sudo systemctl disable --now apex-bmi260-trigger.service || true
sudo rm -f /etc/systemd/system/apex-bmi260-trigger.service
sudo rm -f /etc/inputplumber/apex-bmi260-trigger.sh

if [ -d "$D" ]; then
    echo 0 | sudo tee "$D/buffer/enable" >/dev/null 2>&1 || true
    echo "" | sudo tee "$D/trigger/current_trigger" >/dev/null 2>&1 || true
fi

sudo rmdir /sys/kernel/config/iio/triggers/hrtimer/bmi260-hrtimer 2>/dev/null || true
sudo systemctl daemon-reload
sudo systemctl start inputplumber.service

echo "Restored stock InputPlumber service."
inputplumber --version || true
