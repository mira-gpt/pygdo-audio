import unittest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.audio.jingles import jingle_path
from gdo.audio.method.ipc_jingle import ipc_jingle
from gdo.audio.method.jingle import jingle
from gdo.base.Application import Application
from gdo.base.Render import Mode


class JingleTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'v8.mp3'
        self.path.touch()
        mapping = patch('gdo.audio.jingles.JINGLES', {'v8': self.path})
        mapping.start()
        self.addCleanup(mapping.stop)

    def test_only_known_jingles_resolve(self):
        self.assertTrue(jingle_path('v8').is_file())
        with self.assertRaises(ValueError):
            jingle_path('../v8')

    def test_command_queues_known_jingle(self):
        method = jingle()
        method.param_val = MagicMock(return_value='v8')
        method.reply = MagicMock(return_value='queued')
        database = MagicMock()
        database.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=database), \
                patch('gdo.audio.method.jingle.IPC.send_to_dog') as send:
            self.assertEqual(method.gdo_execute(), 'queued')
        send.assert_called_once_with('audio.ipc_jingle', ['v8'])

    async def test_dog_targets_configured_sink(self):
        method = ipc_jingle()
        method.param_val = MagicMock(return_value='v8')
        method.empty = MagicMock()
        process = MagicMock()
        process.wait = AsyncMock(return_value=0)
        module = MagicMock()
        module.cfg_output_device.return_value = 'mira_stream'
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.audio.method.ipc_jingle.module_audio.instance', return_value=module), \
                patch('gdo.audio.method.ipc_jingle.asyncio.create_subprocess_exec', new_callable=AsyncMock, return_value=process) as spawn:
            await method.gdo_execute()
        args = spawn.call_args.args
        self.assertEqual(args[args.index('-device') + 1], 'mira_stream')
        self.assertIn(str(jingle_path('v8')), args)
