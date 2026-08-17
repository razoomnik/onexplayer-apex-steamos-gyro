#!/bin/bash
set -u

echo "===== VOLUME SERVICE ====="
echo "volume service: $(systemctl is-active apex-volume-buttons.service 2>/dev/null || true)"

if [ -e /run/apex-volume-buttons.ready ]; then
    echo "Ready: yes"
    echo "Source: $(cat /run/apex-volume-buttons.ready 2>/dev/null)"
else
    echo "Ready: no"
fi

echo
echo "===== VIRTUAL DEVICE ====="
grep -B4 -A8 "ONEXPLAYER APEX Volume Buttons" /proc/bus/input/devices 2>/dev/null || true

echo
echo "===== RECENT LOG ====="
sudo journalctl -u apex-volume-buttons.service -b --no-pager 2>/dev/null | tail -30
