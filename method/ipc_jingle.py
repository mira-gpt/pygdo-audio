import asyncio

from gdo.audio.jingles import jingle_path
from gdo.audio.module_audio import module_audio
from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String


class ipc_jingle(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('key').not_null().maxlen(32).positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            try:
                target = module_audio.instance().cfg_output_device()
                if not target:
                    raise ValueError('Audio output device is not configured')
                path = jingle_path(self.param_val('key'))
                process = await asyncio.create_subprocess_exec(
                    'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
                    '-re', '-i', str(path), '-vn', '-f', 'pulse', '-device', target, 'jingle',
                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                if await process.wait():
                    Logger.warning('Audio jingle playback failed; check audio session and output device.')
            except (ValueError, OSError) as exc:
                Logger.warning(f'Audio jingle playback failed: {exc}')
        return self.empty()
