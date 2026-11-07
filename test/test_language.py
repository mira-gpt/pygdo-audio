import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.audio.language import VOICES, speech_language
from gdo.audio.method.language import language
from gdo.base.Application import Application
from gdo.base.Render import Mode


class LanguageTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    async def test_command_saves_language(self):
        method = language()
        method.param_val = MagicMock(return_value='de')
        method.reply = MagicMock()
        module = MagicMock()
        module.save_config_val = AsyncMock()
        with patch('gdo.audio.method.language.module_audio.instance', return_value=module):
            await method.gdo_execute()
        module.save_config_val.assert_awaited_once_with('audio_microphone_language', 'de')
        self.assertEqual('owner', method.gdo_user_permission())

    def test_voice_languages(self):
        self.assertEqual('de+f3', VOICES['de'])
        for code in ('ko', 'vi', 'ja'):
            self.assertEqual(code, VOICES[code])


def entity(language):
    return SimpleNamespace(get_lang_iso=lambda: language)


class SpeechLanguageTest(unittest.TestCase):
    def test_override_precedes_user_and_channel(self):
        method = SimpleNamespace(_env_user=entity('de'), _env_channel=entity('en'))
        self.assertEqual('en', speech_language(method, 'en'))
        self.assertEqual('de', speech_language(method))

    def test_fallbacks_when_unset(self):
        method = SimpleNamespace(_env_user=entity(None), _env_channel=entity('de'), _env_server=entity('en'))
        self.assertEqual('de', speech_language(method))
        method._env_channel = entity(None)
        self.assertEqual('en', speech_language(method))
        self.assertEqual('en', speech_language(SimpleNamespace()))

    def test_does_not_silently_replace_unsupported_user_language(self):
        self.assertEqual('ko', speech_language(SimpleNamespace(_env_user=entity('ko'), _env_channel=entity('en'))))
