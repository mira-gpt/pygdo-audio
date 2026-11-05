import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.audio.method.microphone import microphone
from gdo.base.Application import Application
from gdo.base.Render import Mode


class MicrophoneCommandTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    async def test_enable_and_disable_save_config(self):
        method = microphone()
        method.param_value = MagicMock(side_effect=[True, False])
        method.reply = MagicMock()
        module = MagicMock()
        module.save_config_val = AsyncMock()
        with patch('gdo.audio.method.microphone.module_audio.instance', return_value=module):
            await method.gdo_execute()
            await method.gdo_execute()
        self.assertEqual([(('audio_microphone', '1'),), (('audio_microphone', '0'),)],
                         [(call.args,) for call in module.save_config_val.await_args_list])
        self.assertEqual('owner', method.gdo_user_permission())
