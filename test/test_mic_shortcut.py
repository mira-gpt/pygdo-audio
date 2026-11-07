import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.audio.method.mic import mic
from gdo.base.Application import Application
from gdo.base.Render import Mode


class MicShortcutTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    async def test_enable_saves_language_before_enabled(self):
        method = mic()
        method.param_val = MagicMock(return_value='ja')
        method.param_value = MagicMock(return_value=True)
        method.reply = MagicMock()
        module = MagicMock()
        module.save_config_val = AsyncMock()
        with patch('gdo.audio.method.mic.whisper_languages', return_value={'ja': 'japanese'}), \
                patch('gdo.audio.method.mic.module_audio.instance', return_value=module):
            await method.gdo_execute()
        self.assertEqual([('audio_microphone_language', 'ja'), ('audio_microphone', '1')],
                         [call.args for call in module.save_config_val.await_args_list])
        self.assertEqual('owner', method.gdo_user_permission())

    async def test_disable_keeps_language(self):
        method = mic()
        method.param_val = MagicMock(return_value=None)
        method.param_value = MagicMock(return_value=False)
        method.reply = MagicMock()
        module = MagicMock()
        module.save_config_val = AsyncMock()
        with patch('gdo.audio.method.mic.module_audio.instance', return_value=module):
            await method.gdo_execute()
        module.save_config_val.assert_awaited_once_with('audio_microphone', '0')

    async def test_enable_defaults_to_callers_language(self):
        method = mic()
        method._env_user = MagicMock(get_lang_iso=MagicMock(return_value='ko'))
        method.param_val = MagicMock(return_value=None)
        method.param_value = MagicMock(return_value=True)
        method.reply = MagicMock()
        module = MagicMock()
        module.save_config_val = AsyncMock()
        with patch('gdo.audio.method.mic.whisper_languages', return_value={'ko': 'korean'}), \
                patch('gdo.audio.method.mic.module_audio.instance', return_value=module):
            await method.gdo_execute()
        self.assertEqual([('audio_microphone_language', 'ko'), ('audio_microphone', '1')],
                         [call.args for call in module.save_config_val.await_args_list])

    async def test_invalid_language_does_not_change_configuration(self):
        method = mic()
        method.param_val = MagicMock(return_value='zzz')
        method.param_value = MagicMock(return_value=True)
        method.err = MagicMock()
        with patch('gdo.audio.method.mic.whisper_languages', return_value={'en': 'english'}), \
                patch('gdo.audio.method.mic.module_audio.instance') as module:
            await method.gdo_execute()
        module.assert_not_called()
        method.err.assert_called_once_with('audio_mic_language_unsupported', ('zzz',))
