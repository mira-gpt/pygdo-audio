from gdo.audio.language import whisper_languages
from gdo.audio.module_audio import module_audio
from gdo.base.Method import Method
from gdo.core.GDT_Bool import GDT_Bool
from gdo.core.GDT_String import GDT_String


class mic(Method):
    @classmethod
    def gdo_trig(cls):
        return 'mic'

    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_Bool('enabled').not_null().positional().tooltip('tt_audio_microphone'),
                GDT_String('lang').ascii().minlen(2).maxlen(3).pattern(r'^[a-z]{2,3}$').tooltip('tt_audio_language')]

    async def gdo_execute(self):
        language = self.param_val('lang')
        enabled = self.param_value('enabled')
        if enabled and not language:
            user = getattr(self, '_env_user', None)
            language = user.get_lang_iso() if user else None
        if language:
            try:
                if language not in whisper_languages():
                    return self.err('audio_mic_language_unsupported', (language,))
            except ImportError:
                return self.err('audio_mic_whisper_missing')
        module = module_audio.instance()
        if language:
            await module.save_config_val('audio_microphone_language', language)
        await module.save_config_val('audio_microphone', '1' if enabled else '0')
        return self.reply('audio_mic_requested_on' if enabled else 'audio_mic_requested_off')
