import asyncio
import io
import sys
import unittest
import wave
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.audio.method.ipc_say import edge_speech_to_wav, ipc_say
from gdo.base.Application import Application
from gdo.base.Render import Mode


class EdgeTTSTest(unittest.IsolatedAsyncioTestCase):
    async def test_default_and_configured_voice(self):
        Application.mode(Mode.render_cli)
        method = ipc_say()
        method.param_val = MagicMock(side_effect=lambda key: {'text': 'Hi :*', 'lang': 'en'}[key])
        module = MagicMock()
        module.get_config_val.side_effect = lambda key: {'audio_tts_backend': 'edge', 'audio_edge_voice': None}.get(key)
        with patch('gdo.audio.method.ipc_say.module_audio.instance', return_value=module), \
             patch('gdo.audio.method.ipc_say.edge_speech_to_wav', new_callable=AsyncMock, return_value=b'wav') as synth:
            self.assertEqual(b'wav', await method.prepare())
            synth.assert_awaited_once_with('Hi kisses ', 'en-US-AriaNeural')
            module.get_config_val.side_effect = lambda key: {'audio_tts_backend': 'edge', 'audio_edge_voice': 'ar-EG-SalmaNeural'}.get(key)
            await method.prepare()
            self.assertEqual(('Hi kisses ', 'ar-EG-SalmaNeural'), synth.await_args.args)

    async def test_edge_mp3_is_decoded_to_wav(self):
        async def stream():
            yield {'type': 'WordBoundary'}
            yield {'type': 'audio', 'data': b'mp3'}
        communicate = MagicMock()
        communicate.return_value.stream.return_value = stream()
        decoder = MagicMock(returncode=0, communicate=AsyncMock(return_value=(b'\x00\x00' * 10, b'')))
        with patch.dict(sys.modules, {'edge_tts': SimpleNamespace(Communicate=communicate)}), \
             patch('gdo.audio.method.ipc_say.asyncio.create_subprocess_exec', new_callable=AsyncMock, return_value=decoder):
            result = await edge_speech_to_wav('hello', 'en-US-AriaNeural')
        decoder.communicate.assert_awaited_once_with(b'mp3')
        with wave.open(io.BytesIO(result)) as wav:
            self.assertEqual((1, 2, 24000, 10), (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()))

    async def test_network_error_is_reported_without_text(self):
        async def stream():
            raise OSError('private text')
            yield
        communicate = MagicMock()
        communicate.return_value.stream.return_value = stream()
        with patch.dict(sys.modules, {'edge_tts': SimpleNamespace(Communicate=communicate)}):
            with self.assertRaisesRegex(RuntimeError, '^Edge TTS synthesis failed$'):
                await edge_speech_to_wav('private text', 'voice')

    async def test_cancellation_stops_decoder(self):
        async def stream():
            yield {'type': 'audio', 'data': b'mp3'}
        communicate = MagicMock()
        communicate.return_value.stream.return_value = stream()
        decoder = MagicMock(returncode=None, communicate=AsyncMock(side_effect=asyncio.CancelledError), wait=AsyncMock())
        with patch.dict(sys.modules, {'edge_tts': SimpleNamespace(Communicate=communicate)}), \
             patch('gdo.audio.method.ipc_say.asyncio.create_subprocess_exec', new_callable=AsyncMock, return_value=decoder):
            with self.assertRaises(asyncio.CancelledError):
                await edge_speech_to_wav('hello', 'voice')
        decoder.terminate.assert_called_once()
        decoder.wait.assert_awaited_once()
