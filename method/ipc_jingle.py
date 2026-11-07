import asyncio

from gdo.audio.jingles import jingle_path
from gdo.audio.PlaybackTasks import PlaybackTasks
from gdo.audio.session import audio_session_command
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
            PlaybackTasks.start(self.play())
        return self.empty()

    async def play(self):
        if Application.IS_DOG:
            process = None
            try:
                module = module_audio.instance()
                target = module.cfg_output_device()
                if not target:
                    raise ValueError('Audio output device is not configured')
                path = jingle_path(self.param_val('key'))
                command = audio_session_command([
                    'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
                    '-re', '-i', str(path), '-vn', '-f', 'pulse', '-device', target, 'jingle'],
                    module.get_config_val('audio_output_session_user') or None)
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                if await process.wait():
                    Logger.warning('Audio jingle playback failed; check audio session and output device.')
            except (ValueError, OSError) as exc:
                Logger.warning(f'Audio jingle playback failed: {exc}')
            finally:
                if process is not None and process.returncode is None:
                    try:
                        process.terminate()
                        await process.wait()
                    except ProcessLookupError:
                        pass
        return self.empty()
