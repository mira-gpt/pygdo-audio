import unittest
from unittest.mock import MagicMock

from gdo.audio.meter import MicrophoneMeter


class MeterTest(unittest.TestCase):
    def test_transcript_is_exact_and_cleared_when_disabled(self):
        MicrophoneMeter.transcription_state('on')
        text = 'Hallo, Mira!  Exactly as recognized.'
        MicrophoneMeter.set_transcription_text(text)
        self.assertEqual(text, MicrophoneMeter.transcription_text_snapshot())
        MicrophoneMeter.transcription_state('off')
        MicrophoneMeter.set_transcription_text('late result')
        self.assertEqual('', MicrophoneMeter.transcription_text_snapshot())

    def test_transcription_state_is_independent_of_level(self):
        MicrophoneMeter.update(b'\x00\x40' * 100)
        MicrophoneMeter.transcription_state('off')
        self.assertEqual('on', MicrophoneMeter.snapshot()[0])
        self.assertEqual('off', MicrophoneMeter.transcription_snapshot())
        MicrophoneMeter.transcription_state('on')
        self.assertEqual('on', MicrophoneMeter.transcription_snapshot())
        with self.assertRaises(ValueError):
            MicrophoneMeter.transcription_state('invalid')

    def test_updates_notify_subscribers_and_unsubscribe(self):
        callback = MagicMock()
        MicrophoneMeter.subscribe(callback)
        try:
            MicrophoneMeter.update(b'\x00\x40' * 100)
            callback.assert_called_once()
        finally:
            MicrophoneMeter.unsubscribe(callback)
        MicrophoneMeter.update(b'\x00\x40' * 100)
        callback.assert_called_once()

    def test_levels_stale_and_off(self):
        MicrophoneMeter.state('off')
        self.assertEqual(('off', 0.0), MicrophoneMeter.snapshot())
        MicrophoneMeter.update(b'\0\0' * 100)
        self.assertEqual(('on', 0.0), MicrophoneMeter.snapshot())
        MicrophoneMeter.update(b'\xff\x7f' * 100)
        self.assertGreater(MicrophoneMeter.snapshot()[1], .99)
        self.assertEqual(('unknown', 0.0), MicrophoneMeter.snapshot(MicrophoneMeter._updated + 3))
