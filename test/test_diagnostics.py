import json
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from gdo.audio.diagnostics import MicrophoneDiagnostics, TimedSTT


class DiagnosticsTest(unittest.IsolatedAsyncioTestCase):
    async def test_counters_do_not_store_speech(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch('gdo.audio.diagnostics.Application.temp_path', side_effect=lambda name: os.path.join(directory, name)):
            diagnostics = MicrophoneDiagnostics()
            diagnostics.mark('capture_chunks', count=True, force=True)
            diagnostics.mark('segments', count=True, force=True)
            backend = AsyncMock()
            backend.transcribe.return_value = 'private spoken words'
            self.assertEqual('private spoken words', await TimedSTT(backend, diagnostics).transcribe(None))
            diagnostics.mark('delivered', count=True, force=True)
            with open(diagnostics.path, encoding='utf-8') as stream:
                payload = stream.read()
            self.assertNotIn('private spoken words', payload)
            data = json.loads(payload)
            self.assertEqual((1, 1, 1, 1, 1), tuple(data[key] for key in
                             ('capture_chunks', 'segments', 'whisper_started', 'whisper_finished', 'delivered')))
            self.assertEqual(0o600, os.stat(diagnostics.path).st_mode & 0o777)
