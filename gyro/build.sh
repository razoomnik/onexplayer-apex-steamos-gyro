#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$ROOT/bin"

podman run --rm -it \
  -v "$ROOT/bin:/out" \
  docker.io/library/rust:1.92 \
  bash -c '
set -e
export PATH="/usr/local/cargo/bin:/usr/local/rustup/bin:$PATH"

apt-get update >/dev/null
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  git ca-certificates pkg-config build-essential zstd \
  libclang-dev libudev-dev libiio-dev >/dev/null

git clone \
  --depth 1 \
  --branch pastaq/imu_refactor \
  https://github.com/ShadowBlip/InputPlumber.git \
  /src/InputPlumber

cd /src/InputPlumber

echo "===== UPSTREAM ====="
git log -1 --oneline

python3 - <<"PY"
from pathlib import Path

p = Path("src/drivers/iio_imu/bmi_driver.rs")
s = p.read_text()

# BMI260/BMI270 IIO buffered accel/gyro samples use signed 16-bit storage.
count = s.count("channel_iter::<i32>")
if count != 6:
    raise SystemExit(f"ERROR: expected 6 i32 channel iterators, found {count}")

s = s.replace("channel_iter::<i32>", "channel_iter::<i16>")

# A non-blocking IIO buffer can legitimately be empty before the next trigger
# tick. Once buffered mode owns the device, a direct RAW read returns EBUSY,
# so do not try to force-fill the buffer with attr_read_int("raw").
old = """        if matches!(&refill_res, Err(industrial_io::Error::Nix(errno)) if *errno as i32 == nix::errno::Errno::EAGAIN as i32)
            || matches!(&refill_res, Err(industrial_io::Error::Nix(errno)) if *errno as i32 == nix::errno::Errno::EBUSY as i32)
        {
            log::debug!(\"Buffer has no data. Forcing read to fill buffer\");
            if let Some(accel) = &self.accel {
                match accel.x.channel.attr_read_int(\"raw\") {
                    Ok(_) => return Ok(events),
                    Err(e) => return Err(format!(\"Unable to probe accel channel: {:?}\", e).into()),
                };
            };
            if let Some(gyro) = &self.gyro {
                match gyro.x.channel.attr_read_int(\"raw\") {
                    Ok(_) => return Ok(events),
                    Err(e) => return Err(format!(\"Unable to probe gyro channel: {:?}\", e).into()),
                };
            };
            return Ok(events);
        } else if let Err(e) = refill_res {
"""

new = """        if matches!(&refill_res, Err(industrial_io::Error::Nix(errno)) if *errno as i32 == nix::errno::Errno::EAGAIN as i32)
            || matches!(&refill_res, Err(industrial_io::Error::Nix(errno)) if *errno as i32 == nix::errno::Errno::EBUSY as i32)
        {
            // Non-blocking buffer may have no sample yet.
            // Direct RAW reads are invalid while buffered mode owns the IIO device.
            return Ok(events);
        } else if let Err(e) = refill_res {
"""

if old not in s:
    raise SystemExit("ERROR: expected EAGAIN/EBUSY probe block not found")

s = s.replace(old, new, 1)
p.write_text(s)

print("PATCH 1: six BMI buffered channel iterators i32 -> i16")
print("PATCH 2: removed invalid RAW probe on EAGAIN/EBUSY")
PY

echo
echo "===== VERIFY PATCH ====="
grep -n "channel_iter" src/drivers/iio_imu/bmi_driver.rs

if grep -q "channel_iter::<i32>" src/drivers/iio_imu/bmi_driver.rs; then
    echo "ERROR: i32 iterator still present"
    exit 1
fi

echo
echo "===== BUILD ====="
cargo build --release --locked

install -m755 target/release/inputplumber /out/inputplumber-pr612-apex-v2

echo
echo "===== RESULT ====="
/out/inputplumber-pr612-apex-v2 --version
ls -lh /out/inputplumber-pr612-apex-v2
'

echo
echo "Built: $ROOT/bin/inputplumber-pr612-apex-v2"
