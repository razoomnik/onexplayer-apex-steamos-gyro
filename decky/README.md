# Apex Fixes — Decky plugin

Version 0.3.0 adds **Battery → Block charging** to the existing joystick LED
control and Wi-Fi recovery actions. ON means charging is blocked; OFF allows it.
The switch reads the actual Apex EC mode, including changes made by the Plasma
widget. It does not save or reapply a conflicting software preference at startup.
The battery's reported charging status may take several seconds to update after
a command. Missing battery, unsupported device and command failures are shown
in the panel; an unknown state cannot be toggled.

## Install on SteamOS

From this repository:

```bash
cd decky
./install.sh
```

This installs the plugin to `/home/deck/homebrew/plugins/ApexFixes` and restarts
Decky Loader. The previous installed plugin is backed up outside the plugin
folder under `/home/deck/homebrew/backups/`. Decky settings are not removed.
Alternatively run `python3 build.py` and install `ApexFixes.zip` using Decky's
local plugin installation. No npm dependencies are needed: the existing plugin
frontend uses Decky's supplied UI and React runtime globals.

The plugin has Decky's `_root` flag and invokes its bundled restricted helper
directly. No password prompt is required for toggles. The helper is copied at
build time from `../charge-control/system/charge-helper`; it uses the same EC
address and lock as the standalone fix. Installing the Plasma widget is optional.
See [charge-control](../charge-control/README.md) for the hardware diagnosis.

Plugin files and Decky settings reside in `/home`. No custom kernel build or
read-only SteamOS root modification is required. The running kernel must provide
`ec_sys` and debugfs. The state may reset after full power removal; the panel
always reads the actual hardware state rather than assuming a saved value.

## Other existing controls

- Joystick LEDs: confirmed Apex Gen1 `1A2C:B001` vendor HID; saved LED preference
  is reapplied on plugin startup.
- Wi-Fi Recovery: the existing `nmcli`/`iwlwifi` recovery sequence with a single
  45-second overall watchdog is unchanged.

## Development and checks

Edit `src/index.js`, `main.py`, and the canonical charge helper. Then run:

```bash
python3 build.py
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s ../charge-control/tests -v
node --check src/index.js
node --test tests/frontend.test.mjs
```

The initial frontend and Wi-Fi/LED backend are preserved from the installed
Apex Fixes 0.2.3. The source JS and packaged `dist/index.js` are intentionally
identical; `build.py` also creates a ready-to-install ZIP.

To uninstall just the plugin, remove Apex Fixes through Decky's plugin settings.
This does not remove the standalone charge fix or change the hardware charge mode.
