import unittest

from gdo.audio.pcm import PCMChunk, PCMFormat, PCMRoute
from gdo.audio.turns import SpeechTurns, segment_speech


QUIET = b'\0\0' * 1600
VOICE = b'\0\x40' * 1600
FORMAT = PCMFormat(16000, 1, 2)


class SpeechTurnsTest(unittest.IsolatedAsyncioTestCase):
    def test_silence_does_not_form_a_turn(self):
        turns = SpeechTurns()
        self.assertEqual([], turns.feed(QUIET * 30))
        self.assertIsNone(turns.finish())

    def test_utterance_crosses_chunk_boundary_until_pause(self):
        turns = SpeechTurns()
        self.assertEqual([], turns.feed(QUIET * 3 + VOICE * 7))
        self.assertEqual([], turns.feed(VOICE * 5))
        segments = turns.feed(QUIET * 12)
        self.assertEqual(1, len(segments))
        self.assertEqual(QUIET * 3 + VOICE * 12 + QUIET * 12, segments[0])

    def test_brief_pause_stays_in_same_turn(self):
        turns = SpeechTurns()
        self.assertEqual([], turns.feed(VOICE * 5 + QUIET * 9 + VOICE * 5))
        self.assertEqual(1, len(turns.feed(QUIET * 12)))

    def test_long_speech_is_bounded(self):
        turns = SpeechTurns(max_frames=20)
        segments = turns.feed(VOICE * 21)
        self.assertEqual(1, len(segments))
        self.assertEqual(len(VOICE) * 20, len(segments[0]))
        self.assertEqual(VOICE, turns.finish())

    async def test_route_emits_one_turn_and_closes(self):
        source, destination = PCMRoute(FORMAT), PCMRoute(FORMAT)
        source.feed_input(PCMChunk(FORMAT, 0, VOICE * 10))
        source.feed_input(PCMChunk(FORMAT, 1, VOICE * 3 + QUIET * 12))
        source.close()
        await segment_speech(source, destination)
        segment = await destination.read_input()
        self.assertEqual(VOICE * 13 + QUIET * 12, segment.data)
        self.assertIsNone(await destination.read_input())
