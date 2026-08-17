#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

sudo systemctl stop inputplumber.service || true
sudo systemctl stop apex-volume-buttons.service 2>/dev/null || true

sudo mkdir -p /etc/inputplumber /etc/systemd/system/inputplumber.service.d
sudo install -m755 "$ROOT/scripts/apex-volume-buttons.py" /etc/inputplumber/apex-volume-buttons.py
sudo install -m644 "$ROOT/systemd/apex-volume-buttons.service" /etc/systemd/system/apex-volume-buttons.service
sudo install -m644 "$ROOT/systemd/05-apex-volume-buttons.conf" /etc/systemd/system/inputplumber.service.d/05-apex-volume-buttons.conf

sudo systemctl daemon-reload
sudo systemctl enable apex-volume-buttons.service
sudo systemctl restart apex-volume-buttons.service
sudo systemctl start inputplumber.service

sleep 3
"$ROOT/verify.sh"
