import asyncio
import io
import json
import math
import wave
from uuid import uuid4

from gdo.audio.module_audio import module_audio
from gdo.audio.language import VOICES
from gdo.audio.SpeechEnvelope import speech_envelope
from gdo.audio.SpeechPlayback import SpeechPlayback
from gdo.audio.PlaybackTasks import PlaybackTasks
from gdo.audio.session import audio_session_command
from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String


def piper_pcm_to_wav(pcm: bytes, model: str) -> bytes:
    """Wrap Piper's raw mono PCM in memory for playback and the duck envelope."""
    if not pcm or len(pcm) % 2:
        raise ValueError('Piper returned empty or invalid audio')
    with open(f'{model}.json', encoding='utf-8') as config_file:
        try:
            rate = json.load(config_file)['audio']['sample_rate']
        except (KeyError, TypeError) as error:
            raise ValueError('Missing Piper sample rate') from error
    if type(rate) is not int or not 8000 <= rate <= 192000:
        raise ValueError('Invalid Piper sample rate')
    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm)
    return output.getvalue()


def speech_volume(value) -> int:
    """Convert a configured percentage to PulseAudio's 0..65536 scale."""
    percent = float(value if value is not None and value != '' else 80)
    if not math.isfinite(percent) or not 0 <= percent <= 100:
        raise ValueError('Invalid speech volume')
    return round(percent * 65536 / 100)


class ipc_say(Method):
    _speech_lock = asyncio.Lock()

    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('text').not_null().maxlen(300).positional(),
                GDT_String('lang').not_null().positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            PlaybackTasks.start(self.play())
        return self.empty()

    async def play(self):
        async with self._speech_lock:
            await self._play_one()

    async def _play_one(self):
        if Application.IS_DOG:
            speech_id = uuid4().hex
            started = False
            playing = False
            process = None
            try:
                module = module_audio.instance()
                target = module.cfg_output_device()
                if not target:
                    raise ValueError('Audio output device is not configured')
                language = self.param_val('lang')
                if language not in VOICES:
                    raise ValueError('Unsupported speech language')
                backend = module.get_config_val('audio_tts_backend') or 'espeak'
                if backend == 'piper':
                    binary = module.get_config_val('audio_piper_binary')
                    model_key = f'audio_piper_model_{language}'
                    model = module.get_config_val(model_key) if module.config_column(model_key) else None
                    if not binary or not model:
                        raise ValueError(f'Piper executable or {language} model is not configured')
                    command = [binary, '--model', model, '--output-raw']
                elif backend == 'espeak':
                    command = ['espeak-ng', '-v', VOICES[language], '--stdout', '--stdin']
                else:
                    raise ValueError('Unsupported speech backend')
                voice = await asyncio.create_subprocess_exec(
                    *command,
                    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL)
                process = voice
                wav, _ = await voice.communicate(self.param_val('text').encode('utf-8'))
                process = None
                if voice.returncode:
                    raise RuntimeError('Speech synthesis failed')
                if backend == 'piper':
                    wav = piper_pcm_to_wav(wav, model)
                player_command = audio_session_command(
                    ['paplay', '--device', target, '--stream-name', 'mira-voice',
                     '--volume', str(speech_volume(module.get_config_val('audio_speech_volume')))],
                    module.get_config_val('audio_output_session_user') or None)
                player = await asyncio.create_subprocess_exec(
                    *player_command,
                    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL)
                process = player
                SpeechPlayback.start(speech_id)
                playing = True
                events = getattr(Application, 'EVENTS', None)
                if events:
                    try:
                        await events.publish('audio_speech_start', speech_id, self.param_val('text'))
                        started = True
                        levels = speech_envelope(wav)
                        if levels:
                            await events.publish('audio_speech_envelope', speech_id, levels, 50)
                    except Exception as error:
                        Logger.warning(f'Speech display event failed: {type(error).__name__}')
                await player.communicate(wav)
                process = None
                if player.returncode:
                    raise RuntimeError('Speech playback failed')
            except (ValueError, OSError, RuntimeError) as exc:
                Logger.warning(f'Audio speech failed: {exc}')
            finally:
                if process is not None and process.returncode is None:
                    try:
                        process.terminate()
                        await process.wait()
                    except ProcessLookupError:
                        pass
                if playing:
                    SpeechPlayback.end(speech_id)
                if started:
                    try:
                        await events.publish('audio_speech_end', speech_id)
                    except Exception as error:
                        Logger.warning(f'Speech display event failed: {type(error).__name__}')
        return self.empty()
