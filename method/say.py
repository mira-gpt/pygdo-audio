from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_RestOfText import GDT_RestOfText
from gdo.language.GDT_Language import GDT_Language
from gdo.audio.language import VOICES, speech_language
import msgspec.json


class say(Method):
    @classmethod
    def gdo_trig(cls):
        return 'spk'

    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_RestOfText('text').not_null().tooltip('tt_audio_say_text'),
                GDT_Language('lang').audiolangs().tooltip('tt_audio_say_language')]

    def gdo_execute(self):
        try:
            language = speech_language(self, self.param_val('lang'))
            if language not in VOICES:
                raise ValueError('Unsupported speech language; choose en, de, ko, vi, ja, sq, ru or ar')
            text = self.param_val('text')
            if len(text) > 300:
                raise ValueError('Speech text is limited to 300 characters')
            args = ('audio.ipc_say', [text, language])
            if len(msgspec.json.encode(args[1])) > IPC.MAX_EVENT_ARG_SIZE:
                raise ValueError('Speech request exceeds IPC size limit')
            if Application.db().is_in_transaction():
                Application.defer_after_commit(IPC.send_to_dog, *args)
            else:
                IPC.send_to_dog(*args)
        except (ValueError, RuntimeError, OSError) as exc:
            return self.err('audio_jingle_error', (str(exc),))
        return self.empty() if Application.IS_DOG else self.reply('audio_say_queued')
