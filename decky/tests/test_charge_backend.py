import asyncio
import importlib.util
import logging
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock

sys.modules['decky'] = types.SimpleNamespace(logger=logging.getLogger('test'))
spec = importlib.util.spec_from_file_location('apex_plugin', Path(__file__).resolve().parents[1] / 'main.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ChargeBackendTests(unittest.IsolatedAsyncioTestCase):
    async def test_state_read_from_actual_helper(self):
        p = module.Plugin()
        p._charge_helper = AsyncMock(return_value='inhibit-charge|92|100|Not charging')
        state = await p.get_charge_state()
        self.assertTrue(state['blocked'])
        self.assertEqual(state['battery_status'], 'Not charging')

    async def test_block_requires_confirmation(self):
        p = module.Plugin()
        p._charge_helper = AsyncMock(side_effect=['inhibit-charge', 'auto|92|100|Charging'])
        result = await p.set_charge_blocked(True)
        self.assertFalse(result['ok'])
        self.assertIsNone(result['blocked'])

    async def test_non_boolean_rejected_without_io(self):
        p = module.Plugin()
        p._charge_helper = AsyncMock()
        self.assertFalse((await p.set_charge_blocked('false'))['ok'])
        p._charge_helper.assert_not_awaited()

    async def test_missing_battery_and_bad_output_are_unavailable(self):
        for output in [RuntimeError('Battery missing'), 'bad|92|100|Charging']:
            p = module.Plugin()
            p._charge_helper = AsyncMock(side_effect=output) if isinstance(output, Exception) else AsyncMock(return_value=output)
            state = await p.get_charge_state()
            self.assertFalse(state['available'])
            self.assertIsNone(state['blocked'])

    async def test_set_serializes_with_poll_and_reads_back(self):
        p = module.Plugin()
        started, release = asyncio.Event(), asyncio.Event()
        calls = []
        async def helper(command):
            calls.append(command)
            if command == 'block':
                started.set()
                await release.wait()
                return 'inhibit-charge'
            return 'inhibit-charge|92|100|Charging'
        p._charge_helper = helper
        setter = asyncio.create_task(p.set_charge_blocked(True))
        await started.wait()
        poll = asyncio.create_task(p.get_charge_state())
        await asyncio.sleep(0)
        self.assertEqual(calls, ['block'])
        release.set()
        result, state = await asyncio.gather(setter, poll)
        self.assertTrue(result['ok'])
        self.assertTrue(state['blocked'])
        self.assertEqual(calls, ['block', 'status', 'status'])


if __name__ == '__main__':
    unittest.main()
