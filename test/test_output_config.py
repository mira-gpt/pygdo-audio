import unittest
from unittest.mock import patch

from gdo.audio.module_audio import module_audio


class AudioOutputConfigTest(unittest.TestCase):
    def test_output_is_unset_by_default_and_can_name_a_sink(self):
        module = module_audio()
        setting, = module.gdo_module_config()
        self.assertEqual('audio_output_device', setting.get_name())
        self.assertFalse(setting.get_initial())
        with patch.object(module, 'get_config_val', return_value=''):
            self.assertIsNone(module.cfg_output_device())
        with patch.object(module, 'get_config_val', return_value='virtual_sink'):
            self.assertEqual('virtual_sink', module.cfg_output_device())
