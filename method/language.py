from gdo.audio.module_audio import module_audio
from gdo.base.Method import Method
from gdo.core.GDT_Enum import GDT_Enum


class language(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_Enum('language').choices({'en': 'English', 'de': 'Deutsch', 'ko': 'Korean', 'vi': 'Vietnamese', 'ja': 'Japanese'}).not_null().positional().tooltip('tt_audio_language')]

    async def gdo_execute(self):
        language = self.param_val('language')
        await module_audio.instance().save_config_val('audio_microphone_language', language)
        return self.reply('audio_language_set', (language,))
