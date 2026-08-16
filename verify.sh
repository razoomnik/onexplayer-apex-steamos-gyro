#!/bin/bash
set -u

D=/sys/bus/iio/devices/iio:device0
PID="$(systemctl show -p MainPID --value inputplumber.service)"

echo "===== SERVICES ====="
echo "volume fix:      $(systemctl is-active apex-volume-buttons.service 2>/dev/null || true)"
echo "trigger service: $(systemctl is-active apex-bmi260-trigger.service 2>/dev/null || true)"
echo "inputplumber:     $(systemctl is-active inputplumber.service 2>/dev/null || true)"

echo
echo "===== VOLUME BUTTONS ====="
if [ -e /run/apex-volume-buttons.ready ]; then
    echo "Ready: yes"
    echo "Source: $(cat /run/apex-volume-buttons.ready 2>/dev/null)"
else
    echo "Ready: no"
fi

grep -B4 -A8 "ONEXPLAYER APEX Volume Buttons" /proc/bus/input/devices 2>/dev/null || true

echo
echo "===== INPUTPLUMBER ====="
echo "PID: $PID"
if [ "$PID" != "0" ]; then
    echo -n "Binary: "
    sudo readlink -f "/proc/$PID/exe" 2>/dev/null || true
    echo -n "Version: "
    sudo "/proc/$PID/exe" --version 2>/dev/null || true
fi

echo
echo "===== IMU ====="
if [ -d "$D" ]; then
    echo "Name:      $(cat "$D/name" 2>/dev/null)"
    echo "Trigger:   $(cat "$D/trigger/current_trigger" 2>/dev/null)"
    echo "Buffer:    $(cat "$D/buffer/enable" 2>/dev/null)"
    echo "Watermark: $(cat "$D/buffer/watermark" 2>/dev/null)"
    echo "Gyro Hz:   $(cat "$D/in_anglvel_sampling_frequency" 2>/dev/null)"
    echo "Accel Hz:  $(cat "$D/in_accel_sampling_frequency" 2>/dev/null)"
else
    echo "ERROR: $D not found"
fi

echo
echo "===== RECENT VOLUME LOG ====="
sudo journalctl -u apex-volume-buttons.service -b --no-pager 2>/dev/null | tail -20

echo
echo "===== RECENT IMU LOG ====="
sudo journalctl -u inputplumber.service -b --no-pager 2>/dev/null \
  | grep -Ei 'bmi260|trigger|buffer|watermark|imu|iio|error|warn' \
  | tail -50
