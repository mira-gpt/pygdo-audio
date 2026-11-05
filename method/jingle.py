from gdo.audio.jingles import jingle_path
from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String


class jingle(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_String('key').not_null().maxlen(32).positional().tooltip('tt_audio_jingle_key')]

    def gdo_execute(self):
        key = self.param_val('key')
        try:
            jingle_path(key)
            args = ('audio.ipc_jingle', [key])
            if Application.db().is_in_transaction():
                Application.defer_after_commit(IPC.send_to_dog, *args)
            else:
                IPC.send_to_dog(*args)
        except (ValueError, RuntimeError, OSError) as exc:
            return self.err('audio_jingle_error', (str(exc),))
        return self.reply('audio_jingle_queued')
