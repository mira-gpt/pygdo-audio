from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String
from gdo.core.GDT_UInt import GDT_UInt
from gdo.audio.SpeechChunks import MAX_PARTS, SpeechChunkBuffer


class ipc_say_chunk(Method):
    buffer = SpeechChunkBuffer()

    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('request').ascii().not_null().maxlen(32).positional(),
                GDT_UInt('index').max(MAX_PARTS - 1).not_null().positional(),
                GDT_UInt('total').min(1).max(MAX_PARTS).not_null().positional(),
                GDT_String('part').ascii().not_null().maxlen(400).positional(),
                GDT_String('lang').ascii().not_null().maxlen(3).positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            result = self.buffer.add(self.param_val('request'), self.param_value('index'),
                                     self.param_value('total'), self.param_val('part'),
                                     self.param_val('lang'))
            if result:
                text, language = result
                await IPC.execute_dog_event('audio.ipc_say', ['--text=' + text, '--lang=' + language])
        return self.empty()
