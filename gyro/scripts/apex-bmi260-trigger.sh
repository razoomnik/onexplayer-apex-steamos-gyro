#!/bin/bash
set -e

TRIGNAME=bmi260-hrtimer
CFG="/sys/kernel/config/iio/triggers/hrtimer/$TRIGNAME"

modprobe iio-trig-hrtimer

if ! mountpoint -q /sys/kernel/config; then
    mount -t configfs none /sys/kernel/config
fi

if [ ! -d "$CFG" ]; then
    mkdir "$CFG"
fi

for t in /sys/bus/iio/devices/trigger*; do
    [ -d "$t" ] || continue

    if [ "$(cat "$t/name" 2>/dev/null)" = "$TRIGNAME" ]; then
        # Keep the BMI260 itself at 200 Hz, but sample it with the software
        # trigger at 100 Hz. Running both at 200 Hz caused direction-reversal
        # kicks on the APEX because the hrtimer is not synchronized with the
        # sensor's internal ODR/data-ready timing.
        echo 100 > "$t/sampling_frequency"
        exit 0
    fi
done

echo "ERROR: $TRIGNAME was not created" >&2
exit 1
