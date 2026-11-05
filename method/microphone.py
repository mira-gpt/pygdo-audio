from gdo.audio.module_audio import module_audio
from gdo.base.Method import Method
from gdo.core.GDT_Bool import GDT_Bool


class microphone(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_Bool('enabled').not_null().positional().tooltip('tt_audio_microphone')]

    async def gdo_execute(self):
        enabled = self.param_value('enabled')
        await module_audio.instance().save_config_val('audio_microphone', '1' if enabled else '0')
        return self.reply('audio_microphone_enabled' if enabled else 'audio_microphone_disabled')
