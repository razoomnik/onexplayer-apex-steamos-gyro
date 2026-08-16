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
        echo 200 > "$t/sampling_frequency"
        exit 0
    fi
done

echo "ERROR: $TRIGNAME was not created" >&2
exit 1
