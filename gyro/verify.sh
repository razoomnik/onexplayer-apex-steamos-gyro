#!/bin/bash
set -u

D=/sys/bus/iio/devices/iio:device0
PID="$(systemctl show -p MainPID --value inputplumber.service)"

echo "===== GYRO SERVICES ====="
echo "trigger service: $(systemctl is-active apex-bmi260-trigger.service 2>/dev/null || true)"
echo "inputplumber:     $(systemctl is-active inputplumber.service 2>/dev/null || true)"

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
    echo "Name:       $(cat "$D/name" 2>/dev/null)"
    echo "Trigger:    $(cat "$D/trigger/current_trigger" 2>/dev/null)"

    TRIG=""
    for t in /sys/bus/iio/devices/trigger*; do
        [ -d "$t" ] || continue
        if [ "$(cat "$t/name" 2>/dev/null)" = "bmi260-hrtimer" ]; then
            TRIG="$t"
            break
        fi
    done

    if [ -n "$TRIG" ]; then
        echo "Trigger Hz: $(cat "$TRIG/sampling_frequency" 2>/dev/null)"
    else
        echo "Trigger Hz: unavailable"
    fi

    echo "Buffer:     $(cat "$D/buffer/enable" 2>/dev/null)"
    echo "Watermark:  $(cat "$D/buffer/watermark" 2>/dev/null)"
    echo "Gyro Hz:    $(cat "$D/in_anglvel_sampling_frequency" 2>/dev/null)"
    echo "Accel Hz:   $(cat "$D/in_accel_sampling_frequency" 2>/dev/null)"
else
    echo "ERROR: $D not found"
fi

echo
echo "===== RECENT IMU LOG ====="
sudo journalctl -u inputplumber.service -b --no-pager 2>/dev/null \
  | grep -Ei 'bmi260|trigger|buffer|watermark|imu|iio|error|warn' \
  | tail -50
