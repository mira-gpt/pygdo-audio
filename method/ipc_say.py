import asyncio
from uuid import uuid4

from gdo.audio.module_audio import module_audio
from gdo.audio.language import VOICES
from gdo.audio.SpeechEnvelope import speech_envelope
from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String


class ipc_say(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('text').not_null().maxlen(300).positional(),
                GDT_String('lang').not_null().positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            speech_id = uuid4().hex
            started = False
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
                    model = module.get_config_val(f'audio_piper_model_{language}')
                    if not binary or not model:
                        raise ValueError(f'Piper executable or {language} model is not configured')
                    command = [binary, '--model', model, '--output-file', '-']
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
                player = await asyncio.create_subprocess_exec(
                    'paplay', '--device', target, '--stream-name', 'mira-voice',
                    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL)
                process = player
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
                if started:
                    try:
                        await events.publish('audio_speech_end', speech_id)
                    except Exception as error:
                        Logger.warning(f'Speech display event failed: {type(error).__name__}')
        return self.empty()
