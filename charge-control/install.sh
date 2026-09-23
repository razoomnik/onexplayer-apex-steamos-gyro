#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ $EUID -eq 0 ]]; then
    echo 'Run ./install.sh as the desktop user; sudo is requested for the helper only.' >&2
    exit 1
fi
sudo bash "$ROOT/install-system.sh"
bash "$ROOT/install-plasmoid.sh"
