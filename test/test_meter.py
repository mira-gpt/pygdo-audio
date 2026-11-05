import unittest

from gdo.audio.meter import MicrophoneMeter


class MeterTest(unittest.TestCase):
    def test_levels_stale_and_off(self):
        MicrophoneMeter.state('off')
        self.assertEqual(('off', 0.0), MicrophoneMeter.snapshot())
        MicrophoneMeter.update(b'\0\0' * 100)
        self.assertEqual(('on', 0.0), MicrophoneMeter.snapshot())
        MicrophoneMeter.update(b'\xff\x7f' * 100)
        self.assertGreater(MicrophoneMeter.snapshot()[1], .99)
        self.assertEqual(('unknown', 0.0), MicrophoneMeter.snapshot(MicrophoneMeter._updated + 3))
