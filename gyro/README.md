# ONEXPLAYER APEX Gyroscope Fix

Standalone gyroscope fix for the ONEXPLAYER APEX. It does not install, remove, or configure the volume-button fix.

## Tested configuration

- BMI260 exposed through ACPI as `BMI0160`
- kernel driver `bmi270_i2c`
- BMI260 sensor ODR: **200 Hz**
- software IIO hrtimer trigger: **100 Hz**
- patched InputPlumber PR #612
- virtual target: `deck-uhid`

The 100 Hz software trigger is intentional. Testing a 200 Hz hrtimer against the BMI260's 200 Hz ODR caused severe direction-reversal kicks. Keeping the sensor at 200 Hz while triggering buffered reads at 100 Hz eliminated those kicks on the tested APEX.

## Data path

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

## Install

```bash
./install.sh
```

If the tested binary is not present in `bin/`, build it first:

```bash
./build.sh
```

## Verify

```bash
./verify.sh
```

Expected core state:

```text
trigger service: active
inputplumber:     active
Trigger:    bmi260-hrtimer
Trigger Hz: 100.000000
Buffer:     1
Gyro Hz:    200.000000
Accel Hz:   200.000000
```

## Uninstall only the gyro fix

```bash
./uninstall.sh
```

This removes only the gyro-owned InputPlumber profile, trigger service and PR612 binary override. It does not touch `apex-volume-buttons.service` or its files.

## Mount matrix

```yaml
mount_matrix:
  x: [0.027995, 0.999583, -0.007058]
  y: [0.917322, -0.028495, -0.397126]
  z: [-0.397161, 0.004643, -0.917737]
```
