#!/usr/bin/env bash
set -euo pipefail
# Removing software deliberately leaves the current EC mode unchanged.
if [[ -d "${XDG_DATA_HOME:-$HOME/.local/share}/plasma/plasmoids/local.onexfly.charge-toggle" ]]; then
    kpackagetool6 --type Plasma/Applet --remove local.onexfly.charge-toggle
fi
sudo rm -f /home/.onexfly-charge-helper/charge-helper \
    /etc/polkit-1/rules.d/49-onexfly-charge-toggle.rules \
    /etc/atomic-update.conf.d/onexfly-charge-toggle.conf
printf 'Removed the standalone fix. Hardware mode is unchanged; Decky is unaffected.\n'
