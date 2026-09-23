#!/bin/bash
set -euo pipefail

# Exact sequence manually confirmed to recover Wi-Fi on ONEXPLAYER APEX.
# Decky runs Apex Fixes as root, so sudo is intentionally omitted.

echo "[1/4] Disabling Wi-Fi through NetworkManager"
nmcli radio wifi off
sleep 2

echo "[2/4] Reloading Intel Wi-Fi kernel modules"
modprobe -r iwlmvm iwlwifi
sleep 2

echo "[3/4] Loading iwlwifi"
modprobe iwlwifi
sleep 3

echo "[4/4] Enabling Wi-Fi through NetworkManager"
nmcli radio wifi on

echo "Wi-Fi recovery sequence completed"
