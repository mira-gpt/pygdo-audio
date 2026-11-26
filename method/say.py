from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_RestOfText import GDT_RestOfText
from gdo.language.GDT_Language import GDT_Language
from gdo.audio.language import VOICES, speech_language
from gdo.audio.SpeechChunks import MAX_SPEECH_BYTES, ipc_parts
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
                raise ValueError('Unsupported speech language; choose ' + ', '.join(VOICES))
            text = self.param_val('text')
            if len(text.encode('utf-8')) > MAX_SPEECH_BYTES:
                raise ValueError('Speech text is limited to 4096 UTF-8 bytes')
            args = [text, language]
            events = [('audio.ipc_say', args)] if len(msgspec.json.encode(args)) <= IPC.MAX_EVENT_ARG_SIZE else [
                ('audio.ipc_say_chunk', part) for part in ipc_parts(text, language)]
            for event in events:
                if Application.db().is_in_transaction():
                    Application.defer_after_commit(IPC.send_to_dog, *event)
                else:
                    IPC.send_to_dog(*event)
        except (ValueError, RuntimeError, OSError) as exc:
            return self.err('audio_jingle_error', (str(exc),))
        return self.empty() if Application.IS_DOG else self.reply('audio_say_queued')
