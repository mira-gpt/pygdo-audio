from gdo.audio.module_audio import module_audio
from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_Bool import GDT_Bool


class ipc_meter(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_Bool('enabled').not_null().positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            try:
                meter = module_audio.instance().meter_only
                if self.param_value('enabled'):
                    await meter.start()
                else:
                    await meter.stop()
            except (RuntimeError, ValueError, OSError) as error:
                Logger.warning(f'Meter-only microphone failed: {error}')
        return self.empty()
