"""Monitor an input level without transcription, recording, or chat events."""
import asyncio
import os
import signal

from gdo.audio.meter import MicrophoneMeter
from gdo.audio.session import audio_session_command
from gdo.base.Logger import Logger


class MeterOnly:
    def __init__(self, module):
        self.module = module
        self.task = None

    def running(self):
        return bool(self.task and not self.task.done())

    async def start(self):
        if self.running():
            return
        if self.module.microphone.settings()[0]:
            raise RuntimeError('Disable microphone transcription before starting the meter-only input')
        from gdo.audio.microphone import default_microphone
        session_user = self.module.get_config_val('audio_microphone_session_user') or None
        source = await default_microphone(session_user)
        command = audio_session_command([
            'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-f', 'pulse',
            '-sample_rate', '16000', '-channels', '1', '-fragment_size', '1600',
            '-i', source, '-ac', '1', '-ar', '16000', '-flush_packets', '1',
            '-f', 's16le', 'pipe:1'], session_user)
        process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE,
                                                       stderr=asyncio.subprocess.DEVNULL, start_new_session=True)
        MicrophoneMeter.state('unknown')
        self.task = asyncio.create_task(self._read(process))

    async def _read(self, process):
        try:
            while True:
                data = await process.stdout.read(1600)
                if not data:
                    break
                data = data[:len(data) - len(data) % 2]
                if data:
                    MicrophoneMeter.update(data)
            if await process.wait():
                Logger.warning('Meter-only microphone input stopped unexpectedly.')
        finally:
            if process.returncode is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                await process.wait()
            MicrophoneMeter.state('off')

    async def stop(self):
        task, self.task = self.task, None
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        MicrophoneMeter.state('off')
