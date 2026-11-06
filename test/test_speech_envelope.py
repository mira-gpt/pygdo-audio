import io
import struct
import unittest
import wave

from gdo.audio.SpeechEnvelope import speech_envelope


class SpeechEnvelopeTest(unittest.TestCase):
    def test_silence_and_speech_have_distinct_levels(self):
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(struct.pack('<1600h', *([0] * 800 + [12000] * 800)))
        levels = speech_envelope(buffer.getvalue())
        self.assertEqual(2, len(levels))
        self.assertEqual(0, levels[0])
        self.assertGreater(levels[1], .8)

    def test_invalid_audio_fails_closed(self):
        self.assertEqual([], speech_envelope(b'not a wav'))
