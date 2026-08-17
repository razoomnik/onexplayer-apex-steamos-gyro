#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BIN="$ROOT/bin/inputplumber-pr612-apex-v2"

if [ ! -x "$BIN" ]; then
    echo "ERROR: missing $BIN"
    echo "Run ./build.sh first or place the tested binary there."
    exit 1
fi

sudo systemctl stop inputplumber.service || true

sudo mkdir -p /etc/inputplumber/devices.d /etc/inputplumber
sudo install -m644 "$ROOT/config/50-onexplayer_apex.yaml" /etc/inputplumber/devices.d/50-onexplayer_apex.yaml
sudo install -m755 "$ROOT/scripts/apex-bmi260-trigger.sh" /etc/inputplumber/apex-bmi260-trigger.sh
sudo install -m644 "$ROOT/systemd/apex-bmi260-trigger.service" /etc/systemd/system/apex-bmi260-trigger.service

sudo mkdir -p /etc/systemd/system/inputplumber.service.d
sudo install -m644 "$ROOT/systemd/10-apex-bmi260-trigger.conf" /etc/systemd/system/inputplumber.service.d/10-apex-bmi260-trigger.conf
sudo install -m644 "$ROOT/systemd/20-pr612-buffered-imu.conf" /etc/systemd/system/inputplumber.service.d/20-pr612-buffered-imu.conf

mkdir -p "$HOME/.local/bin"
install -m755 "$BIN" "$HOME/.local/bin/inputplumber-pr612-apex-v2"

sudo systemctl daemon-reload
sudo systemctl enable apex-bmi260-trigger.service
sudo systemctl restart apex-bmi260-trigger.service
sudo systemctl start inputplumber.service

sleep 3
"$ROOT/verify.sh"
