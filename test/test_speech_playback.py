import unittest

from gdo.audio.SpeechPlayback import SpeechPlayback


class SpeechPlaybackTest(unittest.TestCase):
    def test_overlapping_playback_is_reference_counted_by_id(self):
        SpeechPlayback.start('one')
        SpeechPlayback.start('two')
        try:
            SpeechPlayback.end('one')
            self.assertTrue(SpeechPlayback.is_playing())
        finally:
            SpeechPlayback.end('one')
            SpeechPlayback.end('two')
        self.assertFalse(SpeechPlayback.is_playing())
