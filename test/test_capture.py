import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.audio.capture import capture_pulse
from gdo.audio.pcm import PCMRoute
from gdo.audio.stt import WhisperPCMBackend


class CaptureTest(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_source_and_bounded_queue(self):
        route = PCMRoute(WhisperPCMBackend.FORMAT, capacity=1)
        process = MagicMock()
        process.returncode = 0
        process.wait = AsyncMock(return_value=0)
        process.stdout.readexactly = AsyncMock(side_effect=[
            b'\0' * 32000, asyncio.IncompleteReadError(b'\0\0', 32000)])
        with patch('gdo.audio.capture.asyncio.create_subprocess_exec',
                   new_callable=AsyncMock, return_value=process) as spawn:
            stats = await capture_pulse(route, 'test-source', chunk_seconds=1)
        self.assertEqual((2, 1), (stats.chunks, stats.dropped))
        self.assertEqual(0, (await route.read_input()).sequence)
        self.assertIn('test-source', spawn.call_args.args)
        self.assertFalse(route.closed)

    async def test_rejects_implicit_source_without_starting_capture(self):
        route = PCMRoute(WhisperPCMBackend.FORMAT)
        with patch('gdo.audio.capture.asyncio.create_subprocess_exec', new_callable=AsyncMock) as spawn:
            with self.assertRaisesRegex(ValueError, 'explicit'):
                await capture_pulse(route, 'default')
        spawn.assert_not_awaited()

    async def test_cancellation_stops_capture_process(self):
        route = PCMRoute(WhisperPCMBackend.FORMAT)
        process = MagicMock()
        process.pid = 12345
        process.returncode = None
        process.wait = AsyncMock(return_value=0)
        process.stdout.readexactly = AsyncMock(side_effect=asyncio.CancelledError())
        with patch('gdo.audio.capture.asyncio.create_subprocess_exec',
                   new_callable=AsyncMock, return_value=process), \
                patch('gdo.audio.capture.os.killpg') as killpg:
            with self.assertRaises(asyncio.CancelledError):
                await capture_pulse(route, 'test-source')
        killpg.assert_called_once()
