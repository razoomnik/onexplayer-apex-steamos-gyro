#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ $EUID -ne 0 ]]; then
    exec sudo bash "$ROOT/install.sh"
fi
TARGET=/home/deck/homebrew/plugins/ApexFixes
if [[ ! -d /home/deck/homebrew/plugins ]]; then
    echo 'Install Decky Loader first.' >&2
    exit 1
fi
python3 "$ROOT/build.py"
if [[ -d "$TARGET" ]]; then
    BACKUP="/home/deck/homebrew/backups/ApexFixes-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$(dirname "$BACKUP")"
    cp -a "$TARGET" "$BACKUP"
    printf 'Backup: %s\n' "$BACKUP"
fi
install -d -m 755 "$TARGET/dist" "$TARGET/scripts"
for f in main.py plugin.json package.json LICENSE README.md; do
    install -o root -g root -m 644 "$ROOT/$f" "$TARGET/$f"
done
install -o root -g root -m 644 "$ROOT/dist/index.js" "$TARGET/dist/index.js"
install -o root -g root -m 755 "$ROOT/scripts/charge-helper" "$TARGET/scripts/charge-helper"
install -o root -g root -m 755 "$ROOT/scripts/wifi-recovery.sh" "$TARGET/scripts/wifi-recovery.sh"
systemctl restart plugin_loader.service
printf 'Apex Fixes 0.3.0 installed. Open Decky > Apex Fixes > Battery.\n'
