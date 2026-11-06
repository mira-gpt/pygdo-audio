import os
import tempfile
import unittest
import wave
from unittest.mock import MagicMock, patch

from gdo.audio.recording import Recorder
from gdo.audio.method.record import record
from gdo.audio.method.ipc_record import ipc_record
from gdo.base.Application import Application
from gdo.base.Render import Mode


class RecordingTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def tearDown(self):
        with patch('gdo.audio.recording.Logger.message'):
            Recorder.stop()

    def test_private_audio_and_spoken_stop(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(Application, 'temp_path', return_value=directory), \
                patch('gdo.audio.recording.MicrophoneMeter.snapshot', return_value=('on', 0.1)), \
                patch('gdo.audio.recording.Logger.message'):
            path = Recorder.start()
            self.assertEqual(0o700, os.stat(os.path.dirname(path)).st_mode & 0o777)
            self.assertEqual(0o600, os.stat(path).st_mode & 0o777)
            Recorder.feed(b'\x01\x00' * 1600)
            self.assertIsNone(Recorder.stop_if_requested('do not stop'))
            self.assertEqual(path, Recorder.stop_if_requested('Stopp!'))
            with wave.open(path, 'rb') as audio:
                self.assertEqual(1600, audio.getnframes())

    def test_does_not_start_without_microphone(self):
        with patch('gdo.audio.recording.MicrophoneMeter.snapshot', return_value=('off', 0)):
            with self.assertRaises(RuntimeError):
                Recorder.start()

    def test_record_command_queues(self):
        command = record()
        command.param_val = MagicMock(return_value='start')
        command.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.audio.method.record.IPC.send_to_dog') as send:
            command.gdo_execute()
        send.assert_called_once_with('audio.ipc_record', ['start'])
        self.assertEqual('owner', command.gdo_user_permission())

    def test_ipc_start(self):
        method = ipc_record()
        method.param_val = MagicMock(return_value='start')
        method.empty = MagicMock()
        module = MagicMock()
        module.microphone.task.done.return_value = False
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.audio.method.ipc_record.module_audio.instance', return_value=module), \
                patch('gdo.audio.method.ipc_record.Recorder.start') as start, \
                patch('gdo.audio.method.ipc_record.Logger.message'):
            method.gdo_execute()
        start.assert_called_once()
