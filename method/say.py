from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String
import msgspec.json


class say(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_String('text').not_null().maxlen(300).positional().tooltip('tt_audio_say_text')]

    def gdo_execute(self):
        try:
            args = ('audio.ipc_say', [self.param_val('text')])
            if len(msgspec.json.encode(args[1])) > IPC.MAX_EVENT_ARG_SIZE:
                raise ValueError('Speech request exceeds IPC size limit')
            if Application.db().is_in_transaction():
                Application.defer_after_commit(IPC.send_to_dog, *args)
            else:
                IPC.send_to_dog(*args)
        except (ValueError, RuntimeError, OSError) as exc:
            return self.err('audio_jingle_error', (str(exc),))
        return self.reply('audio_say_queued')
