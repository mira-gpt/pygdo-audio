from gdo.base.Method import Method
from gdo.core.GDT_Enum import GDT_Enum
from gdo.core.GDT_String import GDT_String
from gdo.audio.module_audio import module_audio


class tts(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_Enum('backend').choices({'espeak': 'eSpeak NG', 'piper': 'Piper'}).not_null().positional().tooltip('tt_audio_tts_backend'),
                GDT_String('binary').maxlen(512).tooltip('tt_audio_piper_binary'),
                GDT_String('model_de').maxlen(512).tooltip('tt_audio_piper_model_de'),
                GDT_String('model_en').maxlen(512).tooltip('tt_audio_piper_model_en'),
                GDT_String('model_ru').maxlen(512).tooltip('tt_audio_piper_model_ru'),
                GDT_String('model_ar').maxlen(512).tooltip('tt_audio_piper_model_ar')]

    async def gdo_execute(self):
        module = module_audio.instance()
        for key in ('binary', 'model_de', 'model_en', 'model_ru', 'model_ar'):
            value = self.param_val(key)
            if value:
                await module.save_config_val('audio_piper_' + key, value)
        await module.save_config_val('audio_tts_backend', self.param_val('backend'))
        return self.reply('audio_tts_set', (self.param_val('backend'),))
