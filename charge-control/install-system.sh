#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    printf 'Run this once with sudo: sudo bash install-system.sh\n' >&2
    exit 1
fi

source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/system" && pwd)
install -d -o root -g root -m 755 /home/.onexfly-charge-helper
install -d -o root -g root -m 755 /etc/atomic-update.conf.d
install -o root -g root -m 755 "$source_dir/charge-helper" /home/.onexfly-charge-helper/charge-helper
install -o root -g root -m 644 "$source_dir/49-onexfly-charge-toggle.rules" /etc/polkit-1/rules.d/49-onexfly-charge-toggle.rules
install -o root -g root -m 644 "$source_dir/onexfly-charge-toggle.conf" /etc/atomic-update.conf.d/onexfly-charge-toggle.conf

printf 'Installed the restricted charge helper and SteamOS update keep-list.\n'
