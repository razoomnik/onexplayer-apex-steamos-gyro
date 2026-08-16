# ONEXPLAYER APEX SteamOS Gyroscope Fix

Working gyroscope support for the **ONEXPLAYER APEX** on SteamOS using the onboard Bosch BMI260 IMU.

This project documents and packages the configuration that was tested on:

- ONE-NETBOOK / ONEXPLAYER APEX
- SteamOS 3.8.25 (build 20260807.2)
- Linux `6.18.42-valve2-1-neptune-618-gaf6356cf2488`
- BIOS 0.14
- BMI260 exposed through ACPI as `BMI0160`
- kernel driver `bmi270_i2c`

## What was wrong

The stock SteamOS kernel can already detect the IMU correctly as `bmi260`, but the stock ONEXPLAYER APEX InputPlumber profile uses an Xbox Elite virtual target, which does not expose gyro to Steam.

Switching the target to `deck-uhid` makes the gyro available, but two additional problems remain:

1. The APEX profile has no correct IMU mount matrix, so physical horizontal/vertical movement is mixed across axes.
2. InputPlumber's older direct-IIO path reads IMU axes separately. On the APEX this can produce visible jitter and occasional directional kicks during rapid direction changes.

A draft InputPlumber buffered-IIO implementation (PR #612) solves the sampling model, but required two additional fixes for the APEX/BMI260:

- Do not perform a direct `raw` IIO read after buffered mode has claimed the device (`EBUSY`).
- Read BMI260 buffered samples as signed **16-bit** values (`i16`), matching the kernel IIO storage format, instead of `i32`.

The APEX also has no hardware IIO trigger/IRQ exposed to Linux, so this setup creates a **200 Hz hrtimer IIO trigger** at boot.

## Working data path

```text
BMI260
  -> bmi270_i2c
  -> bmi260-hrtimer @ 200 Hz
  -> Linux IIO triggered buffer
  -> patched InputPlumber PR #612
  -> corrected APEX mount matrix
  -> deck-uhid
  -> Steam Input
```

## Installation

The easiest method is:

```bash
./install.sh
```

`install.sh` expects the tested binary at:

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
InputPlumber binary: .../inputplumber-pr612-apex-v2
Trigger:   bmi260-hrtimer
Buffer:    1
Gyro Hz:   200.000000
Accel Hz:  200.000000
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
- `scripts/apex-bmi260-trigger.sh` — creates the software IIO hrtimer trigger at boot.
- `systemd/apex-bmi260-trigger.service` — boot service for the trigger.
- `systemd/10-apex-bmi260-trigger.conf` — makes InputPlumber depend on the trigger service.
- `systemd/20-pr612-buffered-imu.conf` — runs the patched InputPlumber binary.
- `build.sh` — reproducibly builds PR #612 with the APEX/BMI260 fixes in a container.
- `install.sh` — installs the complete fix.
- `verify.sh` — verifies the active binary and IIO state.
- `uninstall.sh` — returns InputPlumber to the SteamOS stock binary/config path.

## Upstream

This work is based on ShadowBlip/InputPlumber and the buffered IIO work from PR #612 (`pastaq/imu_refactor`, commit `208de6a` at the time this fix was developed).

This repository is an unofficial community fix and is not affiliated with ONE-NETBOOK, ONEXPLAYER, Valve, or the InputPlumber project.
