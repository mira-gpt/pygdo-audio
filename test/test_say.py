import unittest
import asyncio
import io
import wave
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.audio.method.say import say
from gdo.audio.method.ipc_say import ipc_say
from gdo.base.Application import Application
from gdo.base.Render import Mode


class SayTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    async def test_speech_requests_play_in_order(self):
        first_started = asyncio.Event()
        release_first = asyncio.Event()
        order = []
        first, second = ipc_say(), ipc_say()

        async def play_first():
            order.append('first start')
            first_started.set()
            await release_first.wait()
            order.append('first end')

        async def play_second():
            order.append('second')

        with patch.object(ipc_say, '_speech_lock', asyncio.Lock()), \
                patch.object(first, '_play_one', side_effect=play_first), \
                patch.object(second, '_play_one', side_effect=play_second):
            one = asyncio.create_task(first.play())
            await first_started.wait()
            two = asyncio.create_task(second.play())
            await asyncio.sleep(0)
            self.assertEqual(['first start'], order)
            release_first.set()
            await asyncio.gather(one, two)
        self.assertEqual(['first start', 'first end', 'second'], order)

    def test_command_queues_text(self):
        method = say()
        self.assertEqual('spk', method.gdo_trig())
        method.param_val = MagicMock(side_effect=lambda key: {'text': 'Quack!', 'lang': 'de'}[key])
        method.reply = MagicMock(return_value='queued')
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.audio.method.say.IPC.send_to_dog') as send:
            self.assertEqual(method.gdo_execute(), 'queued')
        send.assert_called_once_with('audio.ipc_say', ['Quack!', 'de'])

    def test_text_parameter_accepts_all_positional_words(self):
        with patch('gdo.language.GDT_Language.GDO_Language.table'):
            field = say().gdo_parameters()[0]
        field.val(['Hallo', 'Ray,', 'hallo', 'Caffe!'])
        self.assertEqual('Hallo Ray, hallo Caffe!', field.get_value())

    def test_overlong_speech_is_rejected(self):
        method = say()
        method.param_val = MagicMock(side_effect=lambda key: {'text': 'x' * 301, 'lang': 'de'}[key])
        method.err = MagicMock(return_value='rejected')
        with patch('gdo.audio.method.say.IPC.send_to_dog') as send:
            self.assertEqual('rejected', method.gdo_execute())
        send.assert_not_called()

    async def test_voice_is_piped_to_configured_output(self):
        method = ipc_say()
        method.param_val = MagicMock(side_effect=lambda key: {'text': 'Quack!', 'lang': 'de'}[key])
        method.empty = MagicMock()
        voice, player = MagicMock(), MagicMock()
        voice.communicate = AsyncMock(return_value=(b'wav', b''))
        player.communicate = AsyncMock(return_value=(None, None))
        voice.returncode = player.returncode = 0
        module = MagicMock()
        module.cfg_output_device.return_value = 'mira_effects'
        module.get_config_val.return_value = 'espeak'
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.audio.method.ipc_say.module_audio.instance', return_value=module), \
                patch('gdo.audio.method.ipc_say.asyncio.create_subprocess_exec', new_callable=AsyncMock, side_effect=[voice, player]) as spawn:
            await method.play()
        voice.communicate.assert_awaited_once_with(b'Quack!')
        player.communicate.assert_awaited_once_with(b'wav')
        args = spawn.call_args_list[1].args
        self.assertEqual(args[0], 'paplay')
        self.assertEqual(args[args.index('--device') + 1], 'mira_effects')
        self.assertIn('de+f3', spawn.call_args_list[0].args)

    async def test_piper_uses_configured_language_model(self):
        method = ipc_say()
        method.param_val = MagicMock(side_effect=lambda key: {'text': 'Hallo!', 'lang': 'de'}[key])
        method.empty = MagicMock()
        voice, player = MagicMock(), MagicMock()
        voice.communicate = AsyncMock(return_value=(b'wav', b''))
        player.communicate = AsyncMock(return_value=(None, None))
        voice.returncode = player.returncode = 0
        module = MagicMock()
        module.cfg_output_device.return_value = 'mira_effects'
        module.get_config_val.side_effect = lambda key: {
            'audio_tts_backend': 'piper', 'audio_piper_binary': '/opt/piper',
            'audio_piper_model_de': '/opt/de.onnx'}[key]
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.audio.method.ipc_say.module_audio.instance', return_value=module), \
                patch('gdo.audio.method.ipc_say.asyncio.create_subprocess_exec', new_callable=AsyncMock, side_effect=[voice, player]) as spawn:
            await method.play()
        self.assertEqual(('/opt/piper', '--model', '/opt/de.onnx', '--output-file', '-'), spawn.call_args_list[0].args)
        player.communicate.assert_awaited_once_with(b'wav')

    async def test_speech_events_bracket_playback(self):
        method = ipc_say()
        method.param_val = MagicMock(side_effect=lambda key: {'text': 'Hello', 'lang': 'en'}[key])
        method.empty = MagicMock()
        voice, player = MagicMock(), MagicMock()
        voice.communicate = AsyncMock(return_value=(b'wav', b''))
        player.communicate = AsyncMock(return_value=(None, None))
        voice.returncode = player.returncode = 0
        module = MagicMock()
        module.cfg_output_device.return_value = 'mira_effects'
        module.get_config_val.return_value = 'espeak'
        events = MagicMock()
        events.publish = AsyncMock()
        with patch.object(Application, 'IS_DOG', True), \
                patch.object(Application, 'EVENTS', events, create=True), \
                patch('gdo.audio.method.ipc_say.module_audio.instance', return_value=module), \
                patch('gdo.audio.method.ipc_say.asyncio.create_subprocess_exec', new_callable=AsyncMock, side_effect=[voice, player]):
            await method.play()
        calls = events.publish.await_args_list
        self.assertEqual(['audio_speech_start', 'audio_speech_end'], [call.args[0] for call in calls])
        self.assertEqual(calls[0].args[1], calls[1].args[1])
        self.assertEqual('Hello', calls[0].args[2])

    async def test_real_wav_emits_timed_envelope_before_playback_finishes(self):
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(b'\x00\x00' * 800 + b'\x00\x30' * 800)
        method = ipc_say()
        method.param_val = MagicMock(side_effect=lambda key: {'text': 'Hallo', 'lang': 'de'}[key])
        method.empty = MagicMock()
        voice, player = MagicMock(), MagicMock()
        voice.communicate = AsyncMock(return_value=(buffer.getvalue(), b''))
        player.communicate = AsyncMock(return_value=(None, None))
        voice.returncode = player.returncode = 0
        module = MagicMock()
        module.cfg_output_device.return_value = 'sink'
        module.get_config_val.return_value = 'espeak'
        events = MagicMock()
        events.publish = AsyncMock()
        with patch.object(Application, 'IS_DOG', True), \
             patch.object(Application, 'EVENTS', events, create=True), \
             patch('gdo.audio.method.ipc_say.module_audio.instance', return_value=module), \
             patch('gdo.audio.method.ipc_say.asyncio.create_subprocess_exec', new_callable=AsyncMock, side_effect=[voice, player]):
            await method.play()
        calls = events.publish.await_args_list
        self.assertEqual(['audio_speech_start', 'audio_speech_envelope', 'audio_speech_end'], [call.args[0] for call in calls])
        self.assertEqual(calls[0].args[1], calls[1].args[1])
        self.assertEqual([0.0, 1.0], calls[1].args[2])
        self.assertEqual(50, calls[1].args[3])
