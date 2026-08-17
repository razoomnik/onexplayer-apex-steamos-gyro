#!/usr/bin/env python3

import fcntl
import glob
import os
import signal
import struct
import sys
import time

EV_SYN = 0
EV_KEY = 1
SYN_REPORT = 0
KEY_VOLUMEDOWN = 114
KEY_VOLUMEUP = 115
BUS_VIRTUAL = 0x06
READY_FILE = "/run/apex-volume-buttons.ready"

_IOC_TYPESHIFT = 8
_IOC_SIZESHIFT = 16
_IOC_DIRSHIFT = 30


def ioc(direction, typ, nr, size):
    if isinstance(typ, str):
        typ = ord(typ)
    return ((direction << _IOC_DIRSHIFT) | (typ << _IOC_TYPESHIFT) | (nr << 0) | (size << _IOC_SIZESHIFT))


def io(typ, nr):
    return ioc(0, typ, nr, 0)


def iow(typ, nr, size):
    return ioc(1, typ, nr, size)


EVIOCGRAB = iow("E", 0x90, 4)
UI_DEV_CREATE = io("U", 1)
UI_DEV_DESTROY = io("U", 2)
UI_DEV_SETUP = iow("U", 3, 92)
UI_SET_EVBIT = iow("U", 100, 4)
UI_SET_KEYBIT = iow("U", 101, 4)
EVENT_FMT = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FMT)


def find_source():
    for path in sorted(glob.glob("/sys/class/input/event*")):
        try:
            with open(path + "/device/name", encoding="utf-8") as f:
                name = f.read().strip()
        except OSError:
            continue
        if name == "AT Translated Set 2 keyboard":
            return "/dev/input/" + os.path.basename(path)
    return None


def wait_for_source(timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        source = find_source()
        if source and os.path.exists(source) and os.path.exists("/dev/uinput"):
            return source
        time.sleep(0.1)
    return None


def emit(fd, code, value):
    os.write(fd, struct.pack(EVENT_FMT, 0, 0, EV_KEY, code, value))
    os.write(fd, struct.pack(EVENT_FMT, 0, 0, EV_SYN, SYN_REPORT, 0))


def main():
    try:
        os.unlink(READY_FILE)
    except FileNotFoundError:
        pass

    source_path = wait_for_source()
    if not source_path:
        print("ERROR: AT Translated Set 2 keyboard or /dev/uinput not found", flush=True)
        return 1

    print(f"SOURCE: {source_path}", flush=True)
    source = os.open(source_path, os.O_RDONLY | os.O_NONBLOCK)
    ui = None

    try:
        fcntl.ioctl(source, EVIOCGRAB, 1)
        ui = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
        fcntl.ioctl(ui, UI_SET_EVBIT, EV_KEY)
        fcntl.ioctl(ui, UI_SET_KEYBIT, KEY_VOLUMEDOWN)
        fcntl.ioctl(ui, UI_SET_KEYBIT, KEY_VOLUMEUP)

        setup = struct.pack("HHHH80sI", BUS_VIRTUAL, 0x1A2C, 0xB002, 1, b"ONEXPLAYER APEX Volume Buttons", 0)
        fcntl.ioctl(ui, UI_DEV_SETUP, setup)
        fcntl.ioctl(ui, UI_DEV_CREATE)

        time.sleep(0.3)
        with open(READY_FILE, "w", encoding="utf-8") as f:
            f.write(source_path + "\n")

        print("READY", flush=True)
        print("LEFT  -> VOLUMEDOWN", flush=True)
        print("RIGHT -> VOLUMEUP", flush=True)

        running = True

        def stop(*_args):
            nonlocal running
            running = False

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)

        while running:
            try:
                data = os.read(source, EVENT_SIZE * 64)
            except BlockingIOError:
                time.sleep(0.01)
                continue

            for off in range(0, len(data) - EVENT_SIZE + 1, EVENT_SIZE):
                _, _, event_type, code, value = struct.unpack(EVENT_FMT, data[off:off + EVENT_SIZE])
                if event_type != EV_KEY:
                    continue
                if code == KEY_VOLUMEUP:
                    emit(ui, KEY_VOLUMEDOWN, value)
                elif code == KEY_VOLUMEDOWN:
                    emit(ui, KEY_VOLUMEUP, value)
    finally:
        try:
            os.unlink(READY_FILE)
        except FileNotFoundError:
            pass
        try:
            fcntl.ioctl(source, EVIOCGRAB, 0)
        except OSError:
            pass
        if ui is not None:
            try:
                fcntl.ioctl(ui, UI_DEV_DESTROY)
            except OSError:
                pass
            os.close(ui)
        os.close(source)

    return 0


if __name__ == "__main__":
    sys.exit(main())
