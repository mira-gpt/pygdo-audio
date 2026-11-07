import unittest
import math
import struct
from unittest.mock import MagicMock

from gdo.audio.meter import MicrophoneMeter


class MeterTest(unittest.TestCase):
    def test_active_transcription_language_can_change(self):
        MicrophoneMeter.transcription_state('on', language='de')
        self.assertEqual('de', MicrophoneMeter.transcription_language())
        MicrophoneMeter.transcription_state('on', language='en')
        self.assertEqual('en', MicrophoneMeter.transcription_language())

    def test_audio_features_follow_signal_and_stale_state(self):
        rate = 16000
        data = b''.join(struct.pack('<h', round(16000 * math.sin(2 * math.pi * 1000 * i / rate))) for i in range(800))
        MicrophoneMeter.update(data, rate)
        features = MicrophoneMeter.features()
        self.assertEqual('on', features.status)
        self.assertGreater(features.gain, .3)
        self.assertAlmostEqual(1000, features.frequency_hz, delta=20)
        self.assertIsNone(MicrophoneMeter.features(MicrophoneMeter._updated + 3).frequency_hz)
        MicrophoneMeter.update(b'\0\0' * 800, rate)
        self.assertIsNone(MicrophoneMeter.features().frequency_hz)
        MicrophoneMeter.state('off')
        self.assertEqual(('off', 0.0, None), MicrophoneMeter.features())

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

    def test_transcription_timestamp_resets_on_new_text_and_stop(self):
        from unittest.mock import patch
        MicrophoneMeter.transcription_state('off')
        MicrophoneMeter.transcription_state('on')
        with patch('gdo.audio.meter.time.monotonic', return_value=100):
            MicrophoneMeter.set_transcription_text('first')
        self.assertEqual(100, MicrophoneMeter.transcription_text_timestamp())
        with patch('gdo.audio.meter.time.monotonic', return_value=105):
            MicrophoneMeter.set_transcription_text('second')
        self.assertEqual(105, MicrophoneMeter.transcription_text_timestamp())
        MicrophoneMeter.transcription_state('off')
        self.assertEqual(0, MicrophoneMeter.transcription_text_timestamp())

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
