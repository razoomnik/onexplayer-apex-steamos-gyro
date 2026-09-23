import contextlib
import importlib.machinery
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'system' / 'charge-helper'
loader = importlib.machinery.SourceFileLoader('helper', str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
helper = importlib.util.module_from_spec(spec)
loader.exec_module(helper)


class HelperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        files = {'sys/class/dmi/id/board_name': 'ONEXPLAYER APEX\n',
                 'sys/class/power_supply/BATT/capacity': '87\n',
                 'sys/class/power_supply/BATT/status': 'Charging\n',
                 'write_support': 'N\n'}
        for name, data in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data)
        (self.root / 'run').mkdir()
        self.ec = self.root / 'ec'
        data = bytearray([0x55] * 256)
        data[0xA4], data[0xE5], data[0xE6], data[0xE7] = 3, 100, 0, 5
        self.ec.write_bytes(data)
        for p in (patch.object(helper, 'Path', lambda s: self.root / s.lstrip('/')),
                  patch.object(helper, 'IO', self.ec),
                  patch.object(helper, 'WRITE_SUPPORT', self.root / 'write_support'),
                  patch.object(helper.os, 'geteuid', return_value=0)):
            p.start()
            self.addCleanup(p.stop)

    def run_command(self, command):
        out = io.StringIO()
        with patch.object(helper.sys, 'argv', ['helper', command]), contextlib.redirect_stdout(out):
            helper.main()
        return out.getvalue().strip()

    def test_status_uses_apex_register_not_wrong_oxpec_register(self):
        self.assertEqual(self.run_command('status'), 'auto|87|100|Charging')

    def test_block_changes_only_bypass_byte_and_restores_write_gate(self):
        before = self.ec.read_bytes()
        self.assertEqual(self.run_command('block'), 'inhibit-charge')
        after = self.ec.read_bytes()
        self.assertEqual([i for i in range(256) if before[i] != after[i]], [0xE6])
        self.assertEqual(after[0xE6], 3)
        self.assertEqual((self.root / 'write_support').read_text(), 'N\n')
        self.assertEqual(self.run_command('allow'), 'auto')
        self.assertEqual(self.ec.read_bytes(), before)

    def test_unknown_mode_refuses_write(self):
        data = bytearray(self.ec.read_bytes()); data[0xE6] = 0xFF
        self.ec.write_bytes(data)
        with self.assertRaises(RuntimeError):
            self.run_command('block')
        self.assertEqual(self.ec.read_bytes(), data)

    def test_wrong_device_refuses_write(self):
        (self.root / 'sys/class/dmi/id/board_name').write_text('OTHER')
        before = self.ec.read_bytes()
        with self.assertRaises(RuntimeError):
            self.run_command('block')
        self.assertEqual(self.ec.read_bytes(), before)

    def test_failed_readback_restores_write_gate(self):
        with patch.object(helper, 'read_byte', side_effect=[0, 100, 0]):
            with self.assertRaises(RuntimeError):
                self.run_command('block')
        self.assertEqual((self.root / 'write_support').read_text(), 'N\n')


if __name__ == '__main__':
    unittest.main()
