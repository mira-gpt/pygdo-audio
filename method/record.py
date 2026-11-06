from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_Enum import GDT_Enum


class record(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_Enum('action').choices({'start': 'start', 'stop': 'stop'}).not_null().positional().tooltip('tt_audio_record_action')]

    def gdo_execute(self):
        args = ('audio.ipc_record', [self.param_val('action')])
        if Application.db().is_in_transaction():
            Application.defer_after_commit(IPC.send_to_dog, *args)
        else:
            IPC.send_to_dog(*args)
        return self.reply('audio_record_queued')
