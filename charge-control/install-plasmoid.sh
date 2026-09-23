#!/usr/bin/env bash
set -euo pipefail

package_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/package" && pwd)
plugin_id=local.onexfly.charge-toggle

if ! command -v kpackagetool6 >/dev/null; then
    printf 'Plasma 6 / kpackagetool6 is required.\n' >&2
    exit 1
fi

chmod +x "$package_dir/contents/scripts/charge-control"
if kpackagetool6 --type Plasma/Applet --list 2>/dev/null | grep -Fq "$plugin_id"; then
    kpackagetool6 --type Plasma/Applet --upgrade "$package_dir"
else
    kpackagetool6 --type Plasma/Applet --install "$package_dir"
fi

printf '\nInstalled in %s/.local/share/plasma/plasmoids/%s\n' "$HOME" "$plugin_id"
printf 'Open System Tray settings > Entries, enable "Onexfly: зарядка", and set it to Always shown.\n'
