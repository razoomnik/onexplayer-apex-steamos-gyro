#!/bin/bash
set -euo pipefail

sudo systemctl stop inputplumber.service || true
sudo systemctl disable --now apex-volume-buttons.service || true
sudo rm -f /etc/systemd/system/apex-volume-buttons.service
sudo rm -f /etc/systemd/system/inputplumber.service.d/05-apex-volume-buttons.conf
sudo rm -f /etc/inputplumber/apex-volume-buttons.py
sudo rm -f /run/apex-volume-buttons.ready
sudo systemctl daemon-reload
sudo systemctl start inputplumber.service

echo "Removed only the APEX volume-button fix."
