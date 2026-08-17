# ONEXPLAYER APEX Volume Button Fix

Standalone physical volume-button fix for the ONEXPLAYER APEX. It does not install, remove, or modify the gyro fix.

## Problem

The physical buttons are exposed by:

```text
AT Translated Set 2 keyboard
VID 0001 / PID 0001
```

Measured events on the tested APEX:

```text
physical LEFT  -> scan 0xb0 -> KEY_VOLUMEUP
physical RIGHT -> scan 0xae -> KEY_VOLUMEDOWN
```

InputPlumber grabs this keyboard. SteamOS later removes InputPlumber's virtual keyboard target while the physical source remains grabbed, so the volume events disappear.

## Fix

A small Python/uinput service starts **before InputPlumber**, owns the AT keyboard and exposes a dedicated virtual device:

```text
ONEXPLAYER APEX Volume Buttons
```

It also corrects the desired physical layout:

```text
LEFT  -> volume down
RIGHT -> volume up
```

## Install

```bash
./install.sh
```

## Verify

```bash
./verify.sh
```

Expected state:

```text
volume service: active
Ready: yes
```

## Uninstall only the volume fix

```bash
./uninstall.sh
```

This removes only `apex-volume-buttons.service`, its InputPlumber ordering drop-in and the volume forwarder. It does not touch the BMI260 trigger, PR612 InputPlumber override, mount matrix or gyro profile.
