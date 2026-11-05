import asyncio

from gdo.audio.module_audio import module_audio
from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String


class ipc_say(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('text').not_null().maxlen(300).positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            try:
                target = module_audio.instance().cfg_output_device()
                if not target:
                    raise ValueError('Audio output device is not configured')
                voice = await asyncio.create_subprocess_exec(
                    'espeak-ng', '-v', 'en-us+f3', '--stdout', '--stdin',
                    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL)
                wav, _ = await voice.communicate(self.param_val('text').encode('utf-8'))
                if voice.returncode:
                    raise RuntimeError('Speech synthesis failed')
                player = await asyncio.create_subprocess_exec(
                    'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
                    '-re', '-i', 'pipe:0', '-vn', '-f', 'pulse', '-device', target, 'mira-voice',
                    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL)
                await player.communicate(wav)
                if player.returncode:
                    raise RuntimeError('Speech playback failed')
            except (ValueError, OSError, RuntimeError) as exc:
                Logger.warning(f'Audio speech failed: {exc}')
        return self.empty()
