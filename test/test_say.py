import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.audio.method.say import say
from gdo.audio.method.ipc_say import ipc_say
from gdo.base.Application import Application
from gdo.base.Render import Mode


class SayTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_command_queues_text(self):
        method = say()
        method.param_val = MagicMock(return_value='Quack!')
        method.reply = MagicMock(return_value='queued')
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.audio.method.say.IPC.send_to_dog') as send:
            self.assertEqual(method.gdo_execute(), 'queued')
        send.assert_called_once_with('audio.ipc_say', ['Quack!'])

    async def test_voice_is_piped_to_configured_output(self):
        method = ipc_say()
        method.param_val = MagicMock(return_value='Quack!')
        method.empty = MagicMock()
        voice, player = MagicMock(), MagicMock()
        voice.communicate = AsyncMock(return_value=(b'wav', b''))
        player.communicate = AsyncMock(return_value=(None, None))
        voice.returncode = player.returncode = 0
        module = MagicMock()
        module.cfg_output_device.return_value = 'mira_effects'
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.audio.method.ipc_say.module_audio.instance', return_value=module), \
                patch('gdo.audio.method.ipc_say.asyncio.create_subprocess_exec', new_callable=AsyncMock, side_effect=[voice, player]) as spawn:
            await method.gdo_execute()
        voice.communicate.assert_awaited_once_with(b'Quack!')
        player.communicate.assert_awaited_once_with(b'wav')
        args = spawn.call_args_list[1].args
        self.assertEqual(args[args.index('-device') + 1], 'mira_effects')
