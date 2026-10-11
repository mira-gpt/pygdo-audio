from pathlib import Path
import tempfile
import unittest

from gdo.audio.whisper import render_chatstream, transcribe_file


class FakeWhisper:

    def __init__(self, text: str):
        self.text = text
        self.calls = []

    def transcribe(self, audio: str, language: str) -> dict:
        self.calls.append((audio, language))
        return {'text': self.text}


class WhisperHelperTest(unittest.IsolatedAsyncioTestCase):

    def test_renders_final_chatstream(self):
        event = render_chatstream(88, 'call-42', 3, 'de', 'Hallo')
        self.assertEqual(
            '$chatstream 88 --lang=de --call=call-42 --seq=3 --status=final\nHallo',
            event,
        )

    def test_rejects_invalid_chatstream_data(self):
        with self.assertRaises(ValueError):
            render_chatstream(0, 'call-42', 0, 'de', 'Hallo')

    async def test_transcribes_and_emits_final_event(self):
        whisper = FakeWhisper(' Hallo Welt ')
        events = []

        async def emit(event: str) -> None:
            events.append(event)

        with tempfile.NamedTemporaryFile() as audio_file:
            event = await transcribe_file(
                audio_file.name,
                88,
                'call-42',
                0,
                emit,
                model_loader=lambda name: whisper,
            )

        self.assertEqual(events, [event])
        self.assertEqual(
            '$chatstream 88 --lang=de --call=call-42 --seq=0 --status=final\nHallo Welt',
            event,
        )
        self.assertEqual(1, len(whisper.calls))

    async def test_rejects_missing_file_without_loading_model(self):
        async def emit(event: str) -> None:
            self.fail('No event should be emitted.')

        with self.assertRaises(ValueError):
            await transcribe_file('/does/not/exist.wav', 88, 'call-42', 0, emit)
