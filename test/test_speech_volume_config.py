import unittest
from unittest.mock import MagicMock, patch

from gdo.audio.module_audio import module_audio
from gdo.core.GDT_Percent import GDT_Percent


class SpeechVolumeConfigTest(unittest.TestCase):
    def test_speech_volume_is_a_bounded_percentage_defaulting_to_80(self):
        with patch('gdo.ui.WithIcon.t', side_effect=lambda key: key), \
                patch('gdo.core.GDT_User.GDO_User.table', return_value=MagicMock()):
            fields = {field.get_name(): field for field in module_audio().gdo_module_config()}
        volume = fields['audio_speech_volume']
        self.assertIsInstance(volume, GDT_Percent)
        self.assertEqual('80', volume.get_initial())
        self.assertEqual(0, volume._min)
        self.assertEqual(100, volume._max)
