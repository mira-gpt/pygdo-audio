import unittest

from gdo.audio.pcm import PCMChunk, PCMFormat, PCMRoute


class PCMFormatTest(unittest.TestCase):

    def test_calculates_frame_and_byte_sizes(self):
        pcm_format = PCMFormat(16000, 1, 2)
        self.assertEqual(2, pcm_format.frame_size)
        self.assertEqual(32000, pcm_format.bytes_per_second)

    def test_rejects_invalid_format(self):
        with self.assertRaises(ValueError):
            PCMFormat(0, 1, 2)

    def test_rejects_incomplete_frames(self):
        with self.assertRaises(ValueError):
            PCMChunk(PCMFormat(16000, 2, 2), 0, b'abc')


class PCMRouteTest(unittest.IsolatedAsyncioTestCase):

    async def test_separates_input_and_output(self):
        pcm_format = PCMFormat(16000, 1, 2)
        route = PCMRoute(pcm_format)
        captured = PCMChunk(pcm_format, 0, b'\x00\x01')
        playback = PCMChunk(pcm_format, 1, b'\x02\x03')

        route.feed_input(captured)
        route.write_output(playback)

        self.assertEqual(captured, await route.read_input())
        self.assertEqual(playback, await route.read_output())

    async def test_rejects_foreign_format_and_closes(self):
        pcm_format = PCMFormat(16000, 1, 2)
        route = PCMRoute(pcm_format)

        with self.assertRaises(ValueError):
            route.feed_input(PCMChunk(PCMFormat(48000, 1, 2), 0, b'\x00\x01'))

        route.close()
        self.assertIsNone(await route.read_input())
        self.assertIsNone(await route.read_output())

        with self.assertRaises(RuntimeError):
            route.write_output(PCMChunk(pcm_format, 0, b'\x00\x01'))

    async def test_drains_queued_audio_before_closing(self):
        pcm_format = PCMFormat(16000, 1, 2)
        route = PCMRoute(pcm_format, capacity=1)
        chunk = PCMChunk(pcm_format, 0, b'\x00\x01')
        route.feed_input(chunk)
        route.close()

        self.assertEqual(chunk, await route.read_input())
        self.assertIsNone(await route.read_input())

    async def test_reports_chunk_duration(self):
        chunk = PCMChunk(PCMFormat(16000, 1, 2), 0, b'\x00\x00' * 160)
        self.assertEqual(0.01, chunk.duration_seconds)
