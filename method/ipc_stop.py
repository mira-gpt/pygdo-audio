from gdo.audio.PlaybackTasks import PlaybackTasks
from gdo.base.Application import Application
from gdo.base.Method import Method


class ipc_stop(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    async def gdo_execute(self):
        if Application.IS_DOG:
            await PlaybackTasks.stop()
        return self.empty()
