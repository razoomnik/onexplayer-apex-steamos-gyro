# Apex charge blocking

A standalone Plasma tray switch and restricted helper for ONEXPLAYER APEX.
A separate [Decky integration](../decky/README.md) provides the same switch in
Gaming Mode; either frontend can be installed independently.

## Why the ordinary limit and charge block did not work

On the tested SteamOS kernel `7.2.4-valve1-1-neptune-72-g5ab4af5e2eb9`, `oxpec`
reads/writes generic charge offsets `0xA3/0xA4`. The installed OneXConsole
0.9.4-fix5 explicitly selects EC SRAM `0x4E5/0x4E6` for `ONEXPLAYER APEX`,
corresponding to ACPI EC offsets `0xE5/0xE6`. The old sysfs interface could report
`inhibit-charge` while the real Apex charge block was still disabled.

The helper writes only `0` (allow) or `3` (block) at `0xE6`, using the in-tree
`ec_sys` driver. It checks the board and existing values, serializes access
across both frontends, and restores the original `write_support` setting after
writing. Only the root helper has access to EC. It reads the real threshold at
`0xE5` but does not modify the threshold or the force-charge minimum at `0xE7`.

Hardware validation on BIOS 0.14 / EC 0.12, 2026-09-23:

- Both old sysfs inhibit modes allowed energy to increase from 74.041 to 76.685 Wh.
- The correct offset stopped charging: `Not charging`, `power_now=0`, energy stable.
- Allow/block and the Plasma clicks were verified, without password prompts.
- Charging stopped at 92%, well below full; this was not the battery reaching 100%.

The generic KDE percentage setting is still affected by the kernel driver.
Do not use its `charge_behaviour` readback to determine this helper's actual mode.
This fix implements manual charge blocking, not automatic 50% charge cycling.

## Install just this fix

```bash
./install.sh
```

The installer requests sudo for the root helper, then installs the Plasma widget
as the desktop user. Enable **Onexfly: зарядка** in the system tray if necessary.
Closed lock means block; open lock means allow. A warning is shown if the battery
reports charging while the block is selected. ACPI status updates can be delayed.

For terminal-only use: `sudo bash install-system.sh`. To install only the widget
when the helper is already present: `bash install-plasmoid.sh`.

```bash
pkexec /home/.onexfly-charge-helper/charge-helper status
pkexec /home/.onexfly-charge-helper/charge-helper block
pkexec /home/.onexfly-charge-helper/charge-helper allow
```

Only active local user `deck` receives passwordless access, only to this helper.
It accepts exactly `status`, `block`, or `allow`; no register or path arguments.
`status` prints `mode|capacity|actual_limit|battery_status`.

Files are under `/home`; the polkit rule is retained via
`/etc/atomic-update.conf.d/onexfly-charge-toggle.conf`. There is no replacement
kernel module to rebuild after updates. The kernel must continue to ship `ec_sys`.
A full power removal may reset the hardware mode; the widget reads it afresh.

## Uninstall just this fix

Optionally run `allow` first if you want to enable charging, then:

```bash
./uninstall.sh
```

Uninstall does not change the hardware state or remove the Decky plugin, gyro,
volume-button fix, or shared `ec_sys` driver. Decky carries its own helper copy.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Tests simulate the EC and check the register selection, exact single-byte write,
mode validation, model guard, and write-support restoration on failed readback.
