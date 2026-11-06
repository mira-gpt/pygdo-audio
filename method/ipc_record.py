from gdo.audio.recording import Recorder
from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_Enum import GDT_Enum


class ipc_record(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_Enum('action').choices({'start': 'start', 'stop': 'stop'}).not_null().positional()]

    def gdo_execute(self):
        if Application.IS_DOG:
            try:
                if self.param_val('action') == 'start':
                    Recorder.start()
                    Logger.message('Microphone recording started; maximum 30 seconds.')
                else:
                    Recorder.stop()
            except (OSError, RuntimeError, ValueError) as error:
                Logger.warning(f'Microphone recording failed: {error}')
        return self.empty()
