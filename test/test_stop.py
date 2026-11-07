import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.audio.PlaybackTasks import PlaybackTasks
from gdo.audio.method.ipc_say import ipc_say
from gdo.audio.method.ipc_stop import ipc_stop
from gdo.audio.method.stop import stop
from gdo.base.Application import Application
from gdo.base.Render import Mode


class AudioStopTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    async def test_stops_only_registered_jobs(self):
        started = asyncio.Event()
        async def playing():
            started.set()
            await asyncio.Event().wait()
        sound = PlaybackTasks.start(playing())
        unrelated = asyncio.create_task(asyncio.Event().wait())
        await started.wait()
        self.assertEqual(1, await PlaybackTasks.stop())
        self.assertTrue(sound.cancelled())
        self.assertFalse(unrelated.done())
        unrelated.cancel()
        await asyncio.gather(unrelated, return_exceptions=True)

    async def test_stop_cancels_speech_synthesis_process(self):
        method = ipc_say()
        method.empty = MagicMock()
        method.param_val = MagicMock(side_effect=lambda key: {'text': 'Hi', 'lang': 'en'}[key])
        module = MagicMock()
        module.cfg_output_device.return_value = 'sink'
        module.get_config_val.side_effect = lambda key: 'espeak' if key == 'audio_tts_backend' else None
        started = asyncio.Event()
        voice = MagicMock(returncode=None)
        async def communicate(*_):
            started.set()
            await asyncio.Event().wait()
        voice.communicate = AsyncMock(side_effect=communicate)
        voice.wait = AsyncMock(return_value=0)
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.audio.method.ipc_say.module_audio.instance', return_value=module), \
                patch('gdo.audio.method.ipc_say.asyncio.create_subprocess_exec', new_callable=AsyncMock, return_value=voice):
            await method.gdo_execute()
            await started.wait()
            handler = ipc_stop()
            handler.empty = MagicMock()
            await handler.gdo_execute()
        voice.terminate.assert_called_once()
        voice.wait.assert_awaited_once()

    async def test_stop_cleans_up_active_speech_and_emits_end(self):
        from gdo.audio.SpeechPlayback import SpeechPlayback
        method = ipc_say()
        method.empty = MagicMock()
        method.param_val = MagicMock(side_effect=lambda key: {'text': 'Hi', 'lang': 'en'}[key])
        module = MagicMock()
        module.cfg_output_device.return_value = 'sink'
        module.get_config_val.side_effect = lambda key: 'espeak' if key == 'audio_tts_backend' else None
        voice = MagicMock(returncode=0, communicate=AsyncMock(return_value=(b'wav', b'')))
        started = asyncio.Event()
        async def playing(*_):
            started.set()
            await asyncio.Event().wait()
        player = MagicMock(returncode=None, communicate=AsyncMock(side_effect=playing), wait=AsyncMock(return_value=0))
        events = MagicMock(publish=AsyncMock())
        with patch.object(Application, 'IS_DOG', True), \
                patch.object(Application, 'EVENTS', events, create=True), \
                patch('gdo.audio.method.ipc_say.module_audio.instance', return_value=module), \
                patch('gdo.audio.method.ipc_say.asyncio.create_subprocess_exec', new_callable=AsyncMock, side_effect=[voice, player]):
            await method.gdo_execute()
            await started.wait()
            self.assertTrue(SpeechPlayback.is_playing())
            await PlaybackTasks.stop()
        player.terminate.assert_called_once()
        self.assertFalse(SpeechPlayback.is_playing())
        self.assertEqual(['audio_speech_start', 'audio_speech_end'],
                         [call.args[0] for call in events.publish.await_args_list])

    def test_public_stop_queues_to_dog(self):
        method = stop()
        method.reply = MagicMock(return_value='queued')
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.audio.method.stop.IPC.send_to_dog') as send:
            self.assertEqual('queued', method.gdo_execute())
        send.assert_called_once_with('audio.ipc_stop', [])
