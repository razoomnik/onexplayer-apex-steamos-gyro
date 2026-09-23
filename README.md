# ONEXPLAYER APEX SteamOS Fixes

Independent SteamOS fixes for the **ONEXPLAYER APEX**.

Each fix is intentionally isolated. There is **no combined installer** and uninstalling one fix does not remove the files or services owned by another.

## Fixes

### Gyroscope

Directory: [`gyro/`](gyro/)

Fixes the onboard Bosch BMI260 gyro path for Steam Input using the tested APEX mount matrix, a 100 Hz software hrtimer trigger with the sensor at 200 Hz, and the patched InputPlumber PR #612 build.

Install only this fix:

```bash
cd gyro
./install.sh
```

### Volume buttons

Directory: [`volume-buttons/`](volume-buttons/)

Restores the physical volume buttons when InputPlumber grabs the APEX AT keyboard, and maps the physical layout to:

```text
LEFT  -> volume down
RIGHT -> volume up
```

Install only this fix:

```bash
cd volume-buttons
./install.sh
```

### Battery charge blocking

Directory: [`charge-control/`](charge-control/)

Fixes the Apex-specific EC register mismatch that lets the generic `oxpec`
interface report a charge block while the battery continues charging. Includes
an optional Plasma tray switch and a passwordless, restricted helper.

```bash
cd charge-control
./install.sh
```

Verified on BIOS 0.14 / EC 0.12 and SteamOS kernel
`7.2.4-valve1-1-neptune-72-g5ab4af5e2eb9`: blocking produces `Not charging`,
zero charging power and stable stored energy. This controls manual blocking;
it does not correct the generic KDE percentage-limit setting.

### Decky: Apex Fixes

Directory: [`decky/`](decky/)

Adds **Battery → Block charging** to the Apex Fixes plugin alongside joystick
LED control and Wi-Fi recovery. The toggle reflects the actual hardware mode
and works together with the Plasma switch without password prompts.

```bash
cd decky
./install.sh
```

Decky bundles its own copy of the charge helper. It can be installed or removed
independently of all standalone fixes. `python3 decky/build.py` also creates an
installable `decky/ApexFixes.zip`.

## Tested device

- ONE-NETBOOK / ONEXPLAYER APEX
- SteamOS 3.8.25
- Linux `6.18.42-valve2-1-neptune-618-gaf6356cf2488`
- BIOS 0.14

This repository is an unofficial community project and is not affiliated with ONE-NETBOOK, ONEXPLAYER, Valve, or InputPlumber.
