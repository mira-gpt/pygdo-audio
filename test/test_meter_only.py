import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.audio.meter import MicrophoneMeter
from gdo.audio.meter_only import MeterOnly
from gdo.audio.microphone import MicrophoneController


class MeterOnlyTest(unittest.IsolatedAsyncioTestCase):
    async def test_transcription_reconcile_does_not_stop_meter(self):
        module = MagicMock()
        module.meter_only = MeterOnly(module)
        task = asyncio.create_task(asyncio.Event().wait())
        module.meter_only.task = task
        controller = MicrophoneController(module)
        try:
            with patch.object(controller, 'is_running_dog', return_value=True), \
                    patch.object(controller, 'settings', return_value=(True, None, None, 'en', 4)), \
                    patch.object(module.meter_only, 'stop', new_callable=AsyncMock) as stop, \
                    patch('gdo.audio.microphone.Logger.warning'):
                await controller.reconcile()
            stop.assert_not_awaited()
            self.assertTrue(module.meter_only.running())
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def test_meter_can_start_when_transcription_enabled(self):
        module = MagicMock()
        module.microphone.settings.return_value = (True, None, None, 'en', 4)
        module.get_config_val.return_value = None
        process = MagicMock()
        process.stdout.read = AsyncMock(return_value=b'')
        process.returncode = 0
        process.wait = AsyncMock(return_value=0)
        meter = MeterOnly(module)
        with patch('gdo.audio.microphone.default_microphone', new_callable=AsyncMock, return_value='test-source'), \
                patch('gdo.audio.meter_only.asyncio.create_subprocess_exec', new_callable=AsyncMock, return_value=process):
            await meter.start()
            await meter.task

    async def test_level_monitor_reads_pcm_without_transcribing(self):
        module = MagicMock()
        module.microphone.settings.return_value = (False, None, None, 'en', 4)
        module.get_config_val.return_value = None
        process = MagicMock()
        process.stdout.read = AsyncMock(side_effect=[b'\x00\x40' * 200, b''])
        process.returncode = 0
        process.wait = AsyncMock(return_value=0)
        meter = MeterOnly(module)
        with patch('gdo.audio.microphone.default_microphone', new_callable=AsyncMock, return_value='test-source'), \
                patch('gdo.audio.meter_only.asyncio.create_subprocess_exec', new_callable=AsyncMock, return_value=process), \
                patch.object(MicrophoneMeter, 'update') as update:
            await meter.start()
            await meter.task
        update.assert_called_once()
        self.assertFalse(meter.running())

    async def test_disabled_listener_does_not_turn_off_running_meter(self):
        module = MagicMock()
        module.meter_only = MeterOnly(module)
        task = asyncio.create_task(asyncio.Event().wait())
        module.meter_only.task = task
        controller = MicrophoneController(module)
        MicrophoneMeter.update(b'\x00\x40' * 100)
        try:
            with patch.object(controller, 'is_running_dog', return_value=True), \
                    patch.object(controller, 'settings', return_value=(False, None, None, 'en', 4)):
                await controller.reconcile()
            self.assertEqual('on', MicrophoneMeter.snapshot()[0])
            self.assertEqual('off', MicrophoneMeter.transcription_snapshot())
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
