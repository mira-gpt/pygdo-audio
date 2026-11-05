import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from gdo.audio.pcm import PCMChunk, PCMFormat, PCMRoute
from gdo.audio.stt import SilenceGate, STTStream, TranscriptEvent, WhisperPCMBackend


FORMAT = PCMFormat(16000, 1, 2)


class FakeBackend:
    async def transcribe(self, chunk):
        return {0: ' Hello ', 1: '', 3: ' world '}.get(chunk.sequence, '')


class STTStreamTest(unittest.IsolatedAsyncioTestCase):
    async def test_silence_skips_backend(self):
        backend = MagicMock()
        backend.transcribe = AsyncMock(return_value='Hello')
        gate = SilenceGate(backend)
        self.assertEqual('', await gate.transcribe(PCMChunk(FORMAT, 0, b'\0\0' * 200)))
        backend.transcribe.assert_not_awaited()
        self.assertEqual('Hello', await gate.transcribe(PCMChunk(FORMAT, 1, b'\xff\x7f' * 200)))
        backend.transcribe.assert_awaited_once()

    async def test_order_silence_gap_and_close(self):
        route = PCMRoute(FORMAT)
        for sequence in (0, 1, 3):
            route.feed_input(PCMChunk(FORMAT, sequence, b'\0\0'))
        route.close()
        events = []

        async def emit(event):
            events.append(event)

        await STTStream('mic-1', FakeBackend()).run(route, emit)
        self.assertEqual(events, [TranscriptEvent('mic-1', 0, 'final', 'Hello'),
                                  TranscriptEvent('mic-1', 3, 'final', 'world', 1)])

    async def test_gap_is_reported_even_for_silence(self):
        route = PCMRoute(FORMAT)
        for sequence in (1, 4):
            route.feed_input(PCMChunk(FORMAT, sequence, b'\0\0'))
        route.close()
        events = []
        async def emit(event):
            events.append(event)
        await STTStream('call-1', FakeBackend()).run(route, emit)
        self.assertEqual(events, [TranscriptEvent('call-1', 4, 'final', '', 2)])

    async def test_rejects_out_of_order_input(self):
        route = PCMRoute(FORMAT)
        for sequence in (1, 1):
            route.feed_input(PCMChunk(FORMAT, sequence, b'\0\0'))
        route.close()
        async def emit(_event):
            pass
        with self.assertRaisesRegex(ValueError, 'sequences must increase'):
            await STTStream('mic', FakeBackend()).run(route, emit)

    async def test_queue_capacity_is_explicit(self):
        route = PCMRoute(FORMAT, capacity=1)
        route.feed_input(PCMChunk(FORMAT, 0, b'\0\0'))
        with self.assertRaises(asyncio.QueueFull):
            route.feed_input(PCMChunk(FORMAT, 1, b'\0\0'))

    async def test_whisper_receives_memory_pcm(self):
        model = MagicMock()
        model.transcribe.return_value = {'text': ' Quack '}
        backend = WhisperPCMBackend(model, language='en')
        self.assertEqual(' Quack ', await backend.transcribe(PCMChunk(FORMAT, 0, b'\0\0\xff\x7f')))
        audio = model.transcribe.call_args.args[0]
        self.assertEqual(2, len(audio))
        self.assertEqual(0.0, audio[0])
        self.assertGreater(audio[1], 0.99)
        self.assertEqual('en', model.transcribe.call_args.kwargs['language'])
        with self.assertRaisesRegex(ValueError, '16 kHz'):
            await backend.transcribe(PCMChunk(PCMFormat(48000, 1, 2), 0, b'\0\0'))
