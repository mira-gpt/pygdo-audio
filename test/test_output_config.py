import unittest
from unittest.mock import MagicMock, patch

from gdo.audio.module_audio import module_audio
from gdo.base.Application import Application
from gdo.base.Render import Mode


class AudioOutputConfigTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)
        table = patch('gdo.core.GDO_User.GDO_User.table', return_value=MagicMock())
        table.start()
        self.addCleanup(table.stop)

    def test_output_is_unset_by_default_and_can_name_a_sink(self):
        module = module_audio()
        setting = next(field for field in module.gdo_module_config() if field.get_name() == 'audio_output_device')
        self.assertEqual('audio_output_device', setting.get_name())
        self.assertFalse(setting.get_initial())
        with patch.object(module, 'get_config_val', return_value=''):
            self.assertIsNone(module.cfg_output_device())
        with patch.object(module, 'get_config_val', return_value='virtual_sink'):
            self.assertEqual('virtual_sink', module.cfg_output_device())

    def test_operator_is_an_explicit_unset_user(self):
        from gdo.core.GDT_User import GDT_User
        module = module_audio()
        setting = next(field for field in module.gdo_module_config() if field.get_name() == 'audio_operator')
        self.assertIsInstance(setting, GDT_User)
        self.assertFalse(setting.get_initial())
        with patch.object(module, 'get_config_value', return_value=None):
            self.assertIsNone(module.cfg_audio_operator())

    def test_microphone_is_off_by_default(self):
        setting = next(field for field in module_audio().gdo_module_config() if field.get_name() == 'audio_microphone')
        self.assertEqual('0', setting.get_initial())

    def test_language_and_fragment_filter_defaults(self):
        settings = {field.get_name(): field for field in module_audio().gdo_module_config()}
        self.assertEqual('en', settings['audio_microphone_language'].get_initial())
        self.assertEqual('4', settings['audio_transcript_min_letters'].get_initial())
