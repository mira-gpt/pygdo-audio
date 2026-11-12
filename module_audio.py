from __future__ import annotations

from gdo.base.GDO_Module import GDO_Module
from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.core.GDT_String import GDT_String
from gdo.core.GDT_User import GDT_User
from gdo.core.GDT_Bool import GDT_Bool
from gdo.core.GDT_Enum import GDT_Enum
from gdo.core.GDT_UInt import GDT_UInt

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gdo.ui.GDT_Page import GDT_Page


class module_audio(GDO_Module):

    def gdo_classes(self) -> list[type[GDO]]:
        return []

    async def gdo_install(self):
        pass

    def gdo_module_config(self) -> list[GDT]:
        return [
            GDT_String('audio_output_device').maxlen(255).tooltip('tt_audio_output_device'),
            GDT_String('audio_output_session_user').ascii().maxlen(32).tooltip('tt_audio_output_session_user'),
            GDT_Enum('audio_tts_backend').choices({'espeak': 'eSpeak NG', 'piper': 'Piper'}).not_null().initial('espeak').tooltip('tt_audio_tts_backend'),
            GDT_String('audio_piper_binary').maxlen(512).tooltip('tt_audio_piper_binary'),
            GDT_String('audio_piper_model_de').maxlen(512).tooltip('tt_audio_piper_model_de'),
            GDT_String('audio_piper_model_en').maxlen(512).tooltip('tt_audio_piper_model_en'),
            GDT_String('audio_piper_model_ko').maxlen(512).tooltip('tt_audio_piper_model_ko'),
            GDT_String('audio_piper_model_vi').maxlen(512).tooltip('tt_audio_piper_model_vi'),
            GDT_String('audio_piper_model_ja').maxlen(512).tooltip('tt_audio_piper_model_ja'),
            GDT_String('audio_piper_model_sq').maxlen(512).tooltip('tt_audio_piper_model_sq'),
            GDT_String('audio_piper_model_ru').maxlen(512).tooltip('tt_audio_piper_model_ru'),
            GDT_String('audio_piper_model_ar').maxlen(512).tooltip('tt_audio_piper_model_ar'),
            GDT_User('audio_operator').tooltip('tt_audio_operator'),
            GDT_Bool('audio_microphone').not_null().initial('0').tooltip('tt_audio_microphone'),
            GDT_String('audio_microphone_session_user').ascii().maxlen(32).tooltip('tt_audio_microphone_session_user'),
            GDT_String('audio_microphone_language').ascii().minlen(2).maxlen(3).pattern(r'^[a-z]{2,3}$').not_null().initial('en').tooltip('tt_audio_language'),
            GDT_UInt('audio_transcript_min_letters').min(0).max(50).not_null().initial('4').tooltip('tt_audio_transcript_min_letters'),
        ]

    def cfg_output_device(self) -> str | None:
        return self.get_config_val('audio_output_device') or None

    def cfg_audio_operator(self):
        return self.get_config_value('audio_operator')

    def gdo_user_config(self) -> list[GDT]:
        return []

    def gdo_user_settings(self) -> list[GDT]:
        return []

    def gdo_init(self):
        from gdo.audio.microphone import MicrophoneController
        from gdo.audio.meter_only import MeterOnly
        from gdo.audio.mic_gain import MicGainMonitor
        self.microphone = MicrophoneController(self)
        self.meter_only = MeterOnly(self)
        self.mic_gain_monitor = MicGainMonitor(self)

    def gdo_subscribe_events(self):
        from gdo.base.Application import Application
        Application.EVENTS.add_timer_async(2, self.microphone_timer, Application.EVENTS.FOREVER)

    async def microphone_timer(self):
        await self.microphone.reconcile()
        if self.microphone.is_running_dog():
            await self.mic_gain_monitor.reconcile()

    def gdo_load_scripts(self, page: 'GDT_Page'):
        self.add_js('js/pygdo-audio.js')
        self.add_css('css/pygdo-audio.css')
