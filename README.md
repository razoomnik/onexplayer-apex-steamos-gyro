# ONEXPLAYER APEX SteamOS Fixes

Working SteamOS fixes for the **ONEXPLAYER APEX**.

Currently included:

- gyroscope support using the onboard Bosch BMI260 IMU;
- corrected APEX IMU mount matrix;
- BMI260 running at 200 Hz with buffered IIO capture through a **100 Hz software hrtimer trigger**;
- patched InputPlumber PR #612 build;
- persistent physical volume button support;
- corrected physical volume layout: **left = volume down**, **right = volume up**.

Tested on:

- ONE-NETBOOK / ONEXPLAYER APEX
- SteamOS 3.8.25 (build 20260807.2)
- Linux `6.18.42-valve2-1-neptune-618-gaf6356cf2488`
- BIOS 0.14
- BMI260 exposed through ACPI as `BMI0160`
- kernel driver `bmi270_i2c`

## Gyroscope fix

The stock SteamOS kernel can already detect the IMU correctly as `bmi260`, but the stock ONEXPLAYER APEX InputPlumber profile uses an Xbox Elite virtual target, which does not expose gyro to Steam.

Switching the target to `deck-uhid` makes the gyro available, but two additional problems remain:

1. The APEX profile has no correct IMU mount matrix, so physical horizontal/vertical movement is mixed across axes.
2. InputPlumber's older direct-IIO path reads IMU axes separately. On the APEX this can produce visible jitter and occasional directional kicks during rapid direction changes.

A draft InputPlumber buffered-IIO implementation (PR #612) solves the sampling model, but required two additional fixes for the APEX/BMI260:

- Do not perform a direct `raw` IIO read after buffered mode has claimed the device (`EBUSY`).
- Read BMI260 buffered samples as signed **16-bit** values (`i16`), matching the kernel IIO storage format, instead of `i32`.

The APEX has no hardware IIO trigger/IRQ exposed to Linux, so this setup creates a software hrtimer trigger at boot.

### Important trigger-rate finding

The BMI260 itself remains configured at **200 Hz**, but the software hrtimer trigger must run at **100 Hz**.

Testing a 200 Hz hrtimer against the BMI260's 200 Hz sensor ODR caused severe horizontal direction-reversal kicks: when changing direction sharply, the cursor first jumped in the previous/wrong direction. Lowering only the hrtimer trigger to 100 Hz eliminated the kicks while keeping the sensor ODR at 200 Hz.

The likely reason is that the independent software hrtimer is not phase-synchronized with the BMI260's internal 200 Hz sample timing. Running both at the same nominal rate can therefore sample stale/repeated sensor frames around rapid reversals. Sampling the 200 Hz sensor with a 100 Hz software trigger leaves enough margin for a fresh frame between reads.

### Working gyro data path

```text
BMI260 sensor ODR @ 200 Hz
  -> bmi270_i2c
  -> bmi260-hrtimer @ 100 Hz
  -> Linux IIO triggered buffer
  -> patched InputPlumber PR #612
  -> corrected APEX mount matrix
  -> deck-uhid
  -> Steam Input
```

## Volume button fix

The physical APEX volume buttons are exposed through:

```text
AT Translated Set 2 keyboard
VID 0001 / PID 0001
```

Measured physical events:

```text
left button  -> scan 0xb0 -> KEY_VOLUMEUP
right button -> scan 0xae -> KEY_VOLUMEDOWN
```

The APEX InputPlumber profile also grabs this keyboard. During startup InputPlumber briefly creates a virtual keyboard target, but SteamOS later switches the composite target to `deck-uhid` only. The physical keyboard remains grabbed, so its volume events disappear.

The fix runs a very small Python/uinput forwarder **before InputPlumber**. It exclusively owns the AT keyboard and exposes a dedicated virtual device named:

```text
ONEXPLAYER APEX Volume Buttons
```

It also swaps the two physical buttons to the desired layout:

```text
physical LEFT  -> KEY_VOLUMEDOWN
physical RIGHT -> KEY_VOLUMEUP
```

This was tested together with the gyro fix: both gyro and volume buttons remain operational at the same time.

## Installation

The easiest method is:

```bash
./install.sh
```

`install.sh` expects the tested InputPlumber binary at:

```text
bin/inputplumber-pr612-apex-v2
```

If the binary is not present, build it first:

```bash
./build.sh
```

The build happens inside a Podman container and does **not** install a compiler toolchain into SteamOS.

After installation, reboot and verify:

```bash
./verify.sh
```

Expected core state:

```text
volume fix:      active
trigger service: active
inputplumber:     active
Ready: yes
Trigger:    bmi260-hrtimer
Trigger Hz: 100.000000
Buffer:     1
Gyro Hz:    200.000000
Accel Hz:   200.000000
```

## Steam gyro setting

For a simple 2D gyro-to-mouse mapping, `3DOF to 2D Conversion Style = Yaw` produced a straight vertical line during pitch testing on the APEX. Other Steam conversion modes can intentionally combine yaw/roll and may produce curved cursor paths.

## APEX mount matrix

The measured and tested matrix is:

```yaml
mount_matrix:
  x: [0.027995, 0.999583, -0.007058]
  y: [0.917322, -0.028495, -0.397126]
  z: [-0.397161, 0.004643, -0.917737]
```

## Files

- `config/50-onexplayer_apex.yaml` — InputPlumber APEX profile with `deck-uhid` and the corrected IMU mount matrix.
- `scripts/apex-bmi260-trigger.sh` — creates the software IIO hrtimer trigger at boot and sets it to 100 Hz.
- `scripts/apex-volume-buttons.py` — physical volume-button forwarder/remapper.
- `systemd/apex-bmi260-trigger.service` — boot service for the IMU trigger.
- `systemd/apex-volume-buttons.service` — persistent volume-button service.
- `systemd/05-apex-volume-buttons.conf` — makes InputPlumber wait until the volume forwarder owns the AT keyboard.
- `systemd/10-apex-bmi260-trigger.conf` — makes InputPlumber depend on the trigger service.
- `systemd/20-pr612-buffered-imu.conf` — runs the patched InputPlumber binary.
- `build.sh` — reproducibly builds PR #612 with the APEX/BMI260 fixes in a container.
- `install.sh` — installs the complete APEX fix set.
- `verify.sh` — verifies volume, InputPlumber and IIO state, including the software-trigger frequency.
- `uninstall.sh` — removes the custom services and returns InputPlumber to the SteamOS stock binary/config path.

## Upstream

This work is based on ShadowBlip/InputPlumber and the buffered IIO work from PR #612 (`pastaq/imu_refactor`, commit `208de6a` at the time this fix was developed).

This repository is an unofficial community fix and is not affiliated with ONE-NETBOOK, ONEXPLAYER, Valve, or the InputPlumber project.
