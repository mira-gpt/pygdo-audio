from __future__ import annotations

import asyncio
import os
from pathlib import Path
from uuid import uuid4

from gdo.audio.capture import capture_pulse
from gdo.audio.meter import MicrophoneMeter
from gdo.audio.pcm import PCMRoute
from gdo.audio.session import audio_session_command
from gdo.audio.stt import SilenceGate, STTStream, WhisperPCMBackend
from gdo.audio.turns import segment_speech
from gdo.audio.whisper import render_chatstream
from gdo.base.Application import Application
from gdo.base.Logger import Logger


def microphone_event(channel_id: int, user_id: str, language: str, event) -> str:
    if not str(user_id).isdecimal() or int(user_id) < 1:
        raise ValueError('Audio operator must have a valid user ID.')
    text = ' '.join(event.text.replace('\x00', '').split())
    header, _, body = render_chatstream(channel_id, event.stream_id, event.sequence, language, text).partition('\n')
    return f'{header} --user={user_id}\n{body}'


async def default_microphone(session_user: str | None = None) -> str:
    command = audio_session_command(['pactl', 'get-default-source'], session_user)
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL)
    stdout, _ = await process.communicate()
    source = stdout.decode('utf-8', errors='replace').strip()
    if process.returncode or not source or source.endswith('.monitor'):
        raise RuntimeError('No default microphone source is available.')
    return source


def load_local_whisper():
    import whisper
    path = Path.home() / '.cache' / 'whisper' / 'base.pt'
    if not path.is_file():
        raise RuntimeError('Local Whisper base model is missing; no download was attempted.')
    return whisper.load_model(str(path), device='cpu')


async def run_microphone(operator, channel, session_user: str | None = None,
                         language: str = 'en', min_letters: int = 4):
    if not Application.EVENTS._subscribers.get('audio_chatstream'):
        raise RuntimeError('No audio chatstream consumer is available.')
    channel_id = int(channel.get_id())
    user_id = str(operator.get_id())
    stream_id = 'microphone-' + uuid4().hex
    model = await asyncio.to_thread(load_local_whisper)
    source = await default_microphone(session_user)
    capture_route = PCMRoute(WhisperPCMBackend.FORMAT, capacity=8)
    speech_route = PCMRoute(WhisperPCMBackend.FORMAT, capacity=4)
    backend = SilenceGate(WhisperPCMBackend(model, language=language))

    async def emit(event):
        if event.missing_chunks:
            Logger.warning(f'Microphone transcription dropped {event.missing_chunks} audio chunks.')
        if sum(character.isalpha() for character in event.text) >= min_letters and event.text:
            await Application.EVENTS.publish('audio_chatstream', microphone_event(channel_id, user_id, language, event))

    MicrophoneMeter.state('unknown')
    capture = asyncio.create_task(capture_pulse(capture_route, source, chunk_seconds=0.2, session_user=session_user, on_audio=MicrophoneMeter.update))
    segments = asyncio.create_task(segment_speech(capture_route, speech_route))
    transcription = asyncio.create_task(STTStream(stream_id, backend).run(speech_route, emit))
    Logger.debug('Microphone transcription started.')
    try:
        done, _ = await asyncio.wait((capture, segments, transcription), return_when=asyncio.FIRST_COMPLETED)
        if capture in done:
            stats = await capture
            capture_route.close()
            await segments
            await transcription
            if stats.dropped:
                Logger.warning(f'Microphone capture dropped {stats.dropped} audio chunks.')
        elif segments in done:
            await segments
            raise RuntimeError('Microphone segmentation stopped unexpectedly.')
        else:
            await transcription
            raise RuntimeError('Microphone transcription stopped unexpectedly.')
    finally:
        MicrophoneMeter.state('unknown')
        for task in (capture, segments, transcription):
            if not task.done():
                task.cancel()
        await asyncio.gather(capture, segments, transcription, return_exceptions=True)
        Logger.debug('Microphone transcription stopped.')


class MicrophoneController:
    def __init__(self, module):
        self.module = module
        self.task = None
        self.active_operator = None
        self.active_session_user = None
        self.active_settings = None
        self.failed_setting = None

    @staticmethod
    def is_running_dog() -> bool:
        from gdo.core.method.launch import launch
        try:
            return int(Path(launch.lock_path()).read_text().strip()) == os.getpid()
        except (OSError, ValueError):
            return False

    def settings(self):
        from gdo.base.GDO_ModuleVal import GDO_ModuleVal
        table = GDO_ModuleVal.table()
        module_id = self.module.get_id()
        enabled = table.get_by_vals({'mv_module': module_id, 'mv_key': 'audio_microphone'})
        operator = table.get_by_vals({'mv_module': module_id, 'mv_key': 'audio_operator'})
        session_user = table.get_by_vals({'mv_module': module_id, 'mv_key': 'audio_microphone_session_user'})
        language = table.get_by_vals({'mv_module': module_id, 'mv_key': 'audio_microphone_language'})
        minimum = table.get_by_vals({'mv_module': module_id, 'mv_key': 'audio_transcript_min_letters'})
        return (bool(enabled and enabled.gdo_val('mv_val') == '1'),
                operator.gdo_val('mv_val') if operator else None,
                session_user.gdo_val('mv_val') if session_user else None,
                language.gdo_val('mv_val') if language else 'en',
                int(minimum.gdo_val('mv_val')) if minimum else 4)

    async def stop(self):
        if self.task and not self.task.done():
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
        self.task = None
        self.active_operator = None
        self.active_session_user = None
        self.active_settings = None

    async def reconcile(self):
        if not self.is_running_dog():
            return
        try:
            settings = self.settings()
            enabled, operator_id, session_user, language, min_letters = settings
            if not enabled:
                await self.stop()
                MicrophoneMeter.state('off')
                self.failed_setting = None
                return
            if self.task and self.task.done():
                try:
                    self.task.result()
                    Logger.warning('Microphone transcription stopped unexpectedly.')
                except asyncio.CancelledError:
                    pass
                except Exception as error:
                    Logger.warning(f'Microphone transcription failed: {error}')
                self.failed_setting = self.active_settings
                await self.stop()
            if self.task and settings != self.active_settings:
                await self.stop()
            if self.task or self.failed_setting == settings:
                return
            if language not in ('en', 'de') or not 0 <= min_letters <= 50:
                raise ValueError('Invalid audio language or transcript filter.')
            if not operator_id or not str(operator_id).isdecimal():
                raise ValueError('Configure an audio operator before enabling the microphone.')
            from gdo.core.GDO_User import GDO_User
            from gdo.core.connector.Bash import Bash
            operator = GDO_User.table().get_by_id(str(operator_id))
            if not operator:
                raise ValueError('The configured audio operator does not exist.')
            bash = Bash.get_server()
            if not bash:
                raise ValueError('The Bash server is unavailable.')
            channel = bash.get_or_create_channel(operator.get_name(), creator=operator)
            self.active_operator = operator_id
            self.active_session_user = session_user
            self.active_settings = settings
            self.task = asyncio.create_task(run_microphone(operator, channel, session_user, language, min_letters))
        except Exception as error:
            await self.stop()
            self.failed_setting = locals().get('settings')
            Logger.warning(f'Microphone configuration failed: {error}')
