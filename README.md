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

## Tested device

- ONE-NETBOOK / ONEXPLAYER APEX
- SteamOS 3.8.25
- Linux `6.18.42-valve2-1-neptune-618-gaf6356cf2488`
- BIOS 0.14

This repository is an unofficial community project and is not affiliated with ONE-NETBOOK, ONEXPLAYER, Valve, or InputPlumber.
