import asyncio
import json
import os
import signal
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

import decky


FixHandler = Callable[[], Awaitable[Dict[str, Any]]]


class Plugin:
    """Backend for Apex Fixes.

    Recovery actions stay whitelisted in ``_registry``. Stateful hardware
    controls (such as joystick LEDs) use dedicated backend methods.
    """

    RGB_USB_ID = "1A2C:B001"
    RGB_DESCRIPTOR_PREFIX = bytes([0x06, 0x01, 0xFF, 0x09, 0x01, 0xA1, 0x01])
    RGB_PACKET_SIZE = 64
    RGB_MIN_COMMAND_INTERVAL = 0.25

    async def _main(self) -> None:
        self._fix_lock = asyncio.Lock()
        self._led_lock = asyncio.Lock()
        self._last_led_write = 0.0
        self._led_reapply_task: Optional[asyncio.Task] = None
        decky.logger.info("Apex Fixes v0.3.0 loaded")

        settings = self._load_settings()
        saved_led_state = settings.get("joystick_leds_enabled")
        if isinstance(saved_led_state, bool):
            self._led_reapply_task = asyncio.create_task(
                self._reapply_led_state(saved_led_state)
            )

    async def _unload(self) -> None:
        task = getattr(self, "_led_reapply_task", None)
        if task is not None and not task.done():
            task.cancel()
        decky.logger.info("Apex Fixes unloaded")

    def _registry(self) -> Dict[str, Tuple[Dict[str, str], FixHandler]]:
        return {
            "wifi_recovery": (
                {
                    "id": "wifi_recovery",
                    "title": "Wi-Fi Recovery",
                    "description": (
                        "Reloads the Intel iwlwifi driver when Wi-Fi drops and "
                        "all wireless networks disappear."
                    ),
                    "button_label": "Restart Wi-Fi",
                },
                self._fix_wifi_recovery,
            ),
        }

    async def get_fixes(self) -> List[Dict[str, str]]:
        return [metadata.copy() for metadata, _handler in self._registry().values()]

    async def run_fix(self, fix_id: str) -> Dict[str, Any]:
        registry = self._registry()
        entry = registry.get(fix_id)
        if entry is None:
            return {
                "ok": False,
                "message": f"Unknown fix: {fix_id}",
                "details": [],
            }

        lock = getattr(self, "_fix_lock", None)
        if lock is None:
            self._fix_lock = asyncio.Lock()
            lock = self._fix_lock

        if lock.locked():
            return {
                "ok": False,
                "message": "Another Apex fix is already running.",
                "details": [],
            }

        _metadata, handler = entry
        async with lock:
            decky.logger.info("Running Apex fix: %s", fix_id)
            try:
                result = await handler()
                if result.get("ok"):
                    decky.logger.info("Apex fix completed: %s", fix_id)
                else:
                    decky.logger.error("Apex fix failed: %s: %s", fix_id, result)
                return result
            except Exception as exc:
                decky.logger.exception("Unhandled error while running Apex fix: %s", fix_id)
                return {
                    "ok": False,
                    "message": str(exc),
                    "details": [],
                }

    # Charge control is shared with the standalone fix and Plasma widget.
    # Decky already runs as root; never launch sudo/pkexec from an RPC.
    async def _charge_helper(self, command: str) -> str:
        if command not in ("status", "allow", "block"):
            raise ValueError("Unsupported charge command")
        helper = Path(__file__).resolve().parent / "scripts" / "charge-helper"
        process = await asyncio.create_subprocess_exec(
            "/usr/bin/python3", "-I", str(helper), command,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), 20)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            if process.returncode is None:
                try:
                    # Let the helper restore its temporary EC write gate.
                    process.terminate()
                except ProcessLookupError:
                    pass
            try:
                await asyncio.wait_for(process.communicate(), 5)
            except asyncio.TimeoutError:
                if process.returncode is None:
                    process.kill()
                await process.communicate()
            raise
        if process.returncode:
            raise RuntimeError(stderr.decode(errors="replace").strip() or
                               f"Charge helper failed ({process.returncode})")
        return stdout.decode().strip()

    @staticmethod
    def _parse_charge_state(output: str) -> Dict[str, Any]:
        mode, capacity, limit, status = output.split("|")
        if mode not in ("auto", "inhibit-charge", "inhibit-charge-awake"):
            raise ValueError("Unknown charge mode")
        capacity, limit = int(capacity), int(limit)
        if not 0 <= capacity <= 100 or not 0 <= limit <= 100:
            raise ValueError("Invalid battery percentage")
        return {"ok": True, "available": True, "blocked": mode != "auto",
                "mode": mode, "capacity": capacity, "limit": limit,
                "battery_status": status}

    def _get_charge_lock(self) -> asyncio.Lock:
        if not hasattr(self, "_charge_lock"):
            self._charge_lock = asyncio.Lock()
        return self._charge_lock

    async def get_charge_state(self) -> Dict[str, Any]:
        async with self._get_charge_lock():
            try:
                return self._parse_charge_state(await self._charge_helper("status"))
            except Exception as exc:
                return {"ok": False, "available": False, "blocked": None,
                        "message": str(exc) or type(exc).__name__}

    async def set_charge_blocked(self, blocked: bool) -> Dict[str, Any]:
        if type(blocked) is not bool:
            return {"ok": False, "available": False, "blocked": None,
                    "message": "Charge block must be true or false."}
        async with self._get_charge_lock():
            try:
                await self._charge_helper("block" if blocked else "allow")
                state = self._parse_charge_state(await self._charge_helper("status"))
                if state["blocked"] != blocked:
                    raise RuntimeError("Charge mode changed before confirmation")
                state["message"] = ("Charge block enabled." if blocked else "Charging allowed.")
                return state
            except Exception as exc:
                decky.logger.exception("Apex charge control failed")
                return {"ok": False, "available": False, "blocked": None,
                        "message": str(exc) or type(exc).__name__}

    # ---------------------------------------------------------------------
    # Joystick RGB control
    # ---------------------------------------------------------------------

    def _settings_path(self) -> Optional[Path]:
        settings_dir = getattr(decky, "DECKY_PLUGIN_SETTINGS_DIR", None)
        if not settings_dir:
            return None
        return Path(settings_dir) / "settings.json"

    def _load_settings(self) -> Dict[str, Any]:
        path = self._settings_path()
        if path is None or not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            decky.logger.exception("Failed to read Apex Fixes settings")
            return {}

    def _save_settings(self, settings: Dict[str, Any]) -> None:
        path = self._settings_path()
        if path is None:
            decky.logger.warning("Decky settings directory is unavailable")
            return

        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(settings, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temp_path, path)

    def _hid_device_root(self, hidraw_class_path: Path) -> Optional[Path]:
        """Return the HID device directory containing report_descriptor."""
        try:
            current = (hidraw_class_path / "device").resolve()
        except OSError:
            return None

        for candidate in [current, *current.parents]:
            if (candidate / "report_descriptor").is_file() and (candidate / "uevent").is_file():
                return candidate
        return None

    def _find_apex_rgb_hidraw(self) -> Optional[str]:
        """Find the Gen1 64-byte vendor HID used by Apex joystick RGB.

        Do not hardcode hidrawX or the dynamic HID instance suffix (.0001 etc.).
        The correct interface is identified by VID:PID plus the known vendor
        report descriptor that exposes a 64-byte output report.
        """
        for hidraw in sorted(Path("/sys/class/hidraw").glob("hidraw*")):
            hid_root = self._hid_device_root(hidraw)
            if hid_root is None:
                continue

            try:
                uevent = (hid_root / "uevent").read_text(encoding="utf-8", errors="replace")
                descriptor = (hid_root / "report_descriptor").read_bytes()
            except OSError:
                continue

            hid_id_match = (
                "HID_ID=0003:00001A2C:0000B001" in uevent
                or self.RGB_USB_ID in hid_root.name.upper()
            )
            vendor_report_match = (
                descriptor.startswith(self.RGB_DESCRIPTOR_PREFIX)
                and b"\x95\x40" in descriptor
                and b"\x91\x02" in descriptor
            )

            if hid_id_match and vendor_report_match:
                return f"/dev/{hidraw.name}"

        return None

    def _build_led_packet(self, enabled: bool) -> bytes:
        # Confirmed working on ONEXPLAYER APEX Gen1 RGB MCU (1A2C:B001):
        # function=0x07, message=0xff, set_property=0xfd,
        # enabled=(0/1), speed=0, brightness_hw_level=4.
        header = bytes([
            0x07,
            0xFF,
            0xFD,
            0x01 if enabled else 0x00,
            0x00,
            0x04,
        ])
        return header + bytes(self.RGB_PACKET_SIZE - len(header))

    async def _write_led_state(self, enabled: bool) -> str:
        target = self._find_apex_rgb_hidraw()
        if target is None:
            raise RuntimeError(
                "Apex RGB HID 1A2C:B001 vendor interface was not found."
            )

        elapsed = time.monotonic() - getattr(self, "_last_led_write", 0.0)
        if elapsed < self.RGB_MIN_COMMAND_INTERVAL:
            await asyncio.sleep(self.RGB_MIN_COMMAND_INTERVAL - elapsed)

        packet = self._build_led_packet(enabled)
        with open(target, "wb", buffering=0) as device:
            written = device.write(packet)

        self._last_led_write = time.monotonic()
        if written != len(packet):
            raise RuntimeError(
                f"Short HID write to {target}: {written}/{len(packet)} bytes"
            )

        decky.logger.info(
            "Apex joystick LEDs set to %s via %s",
            "ON" if enabled else "OFF",
            target,
        )
        return target

    async def _reapply_led_state(self, enabled: bool) -> None:
        # Give USB/HID enumeration a moment to finish after boot / Decky restart.
        try:
            await asyncio.sleep(1.5)
            async with self._led_lock:
                await self._write_led_state(enabled)
            decky.logger.info("Reapplied saved joystick LED state: %s", enabled)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Do not prevent plugin startup if the controller is temporarily absent.
            decky.logger.exception("Failed to reapply saved joystick LED state")

    async def get_led_state(self) -> Dict[str, Any]:
        settings = self._load_settings()
        saved = settings.get("joystick_leds_enabled")
        return {
            "ok": True,
            "available": self._find_apex_rgb_hidraw() is not None,
            # There is no reliable readback on the current Apex hid-oxp path.
            # This is the last state explicitly applied by Apex Fixes.
            "enabled": saved if isinstance(saved, bool) else None,
        }

    async def set_led_enabled(self, enabled: bool) -> Dict[str, Any]:
        if not isinstance(enabled, bool):
            return {
                "ok": False,
                "message": "LED state must be true or false.",
                "enabled": None,
            }

        lock = getattr(self, "_led_lock", None)
        if lock is None:
            self._led_lock = asyncio.Lock()
            lock = self._led_lock

        async with lock:
            try:
                target = await self._write_led_state(enabled)
                settings = self._load_settings()
                settings["joystick_leds_enabled"] = enabled
                self._save_settings(settings)
                return {
                    "ok": True,
                    "message": f"Joystick LEDs {'enabled' if enabled else 'disabled'}.",
                    "enabled": enabled,
                    "device": target,
                }
            except Exception as exc:
                decky.logger.exception("Failed to change joystick LED state")
                return {
                    "ok": False,
                    "message": f"Joystick LED control failed: {exc}",
                    "enabled": None,
                }

    # ---------------------------------------------------------------------
    # Recovery fixes
    # ---------------------------------------------------------------------
    # ---------------------------------------------------------------------
    # Recovery fixes
    # ---------------------------------------------------------------------

    WIFI_RECOVERY_TIMEOUT = 45.0

    def _wifi_recovery_script(self) -> Path:
        return Path(__file__).resolve().parent / "scripts" / "wifi-recovery.sh"

    async def _fix_wifi_recovery(self) -> Dict[str, Any]:
        """Run the exact manually confirmed Apex Wi-Fi recovery sequence.

        The whole helper is one child process.  Individual nmcli/modprobe
        commands have no plugin-side timeout or fallback.  A single 45-second
        watchdog protects Decky's RPC from remaining blocked indefinitely.
        """
        script = self._wifi_recovery_script()
        if not script.is_file():
            return {
                "ok": False,
                "message": f"Wi-Fi recovery helper is missing: {script}",
                "details": [],
            }

        env = {
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "HOME": "/root",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        }

        decky.logger.info(
            "Running Wi-Fi recovery helper with %.0fs overall timeout: %s",
            self.WIFI_RECOVERY_TIMEOUT,
            script,
        )

        process = await asyncio.create_subprocess_exec(
            "/bin/bash",
            str(script),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            start_new_session=True,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.WIFI_RECOVERY_TIMEOUT
            )
        except asyncio.TimeoutError:
            # Kill the whole helper process group.  There are deliberately no
            # per-command watchdogs inside the script; this is the only one.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except Exception:
                decky.logger.exception("Failed to kill timed-out Wi-Fi helper group")

            decky.logger.error(
                "Wi-Fi recovery exceeded the %.0fs overall timeout",
                self.WIFI_RECOVERY_TIMEOUT,
            )
            return {
                "ok": False,
                "message": (
                    "Wi-Fi recovery exceeded the 45-second overall timeout. "
                    "No per-command timeout or fallback was used."
                ),
                "details": [
                    {
                        "command": str(script),
                        "timeout_seconds": int(self.WIFI_RECOVERY_TIMEOUT),
                    }
                ],
            }

        stdout_text = stdout.decode("utf-8", errors="replace").strip()
        stderr_text = stderr.decode("utf-8", errors="replace").strip()

        details = [
            {
                "command": str(script),
                "returncode": process.returncode,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "timeout_seconds": int(self.WIFI_RECOVERY_TIMEOUT),
            }
        ]

        if process.returncode != 0:
            error_text = stderr_text or stdout_text or f"exit code {process.returncode}"
            return {
                "ok": False,
                "message": f"Wi-Fi recovery script failed: {error_text}",
                "details": details,
            }

        return {
            "ok": True,
            "message": "Wi-Fi recovery completed.",
            "details": details,
        }
