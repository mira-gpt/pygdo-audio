import unittest
from types import SimpleNamespace
from unittest.mock import patch

from gdo.audio.session import audio_session_command


class AudioSessionTest(unittest.TestCase):
    def test_cross_user_capture_uses_noninteractive_session(self):
        account = SimpleNamespace(pw_uid=1000, pw_name='gizmore')
        with patch('gdo.audio.session.pwd.getpwnam', return_value=account), \
                patch('gdo.audio.session.os.geteuid', return_value=1002):
            self.assertEqual(['sudo', '-n', '-u', 'gizmore', '--', 'env',
                              'XDG_RUNTIME_DIR=/run/user/1000', 'pactl', 'get-default-source'],
                             audio_session_command(['pactl', 'get-default-source'], 'gizmore'))

    def test_root_audio_session_is_rejected(self):
        with patch('gdo.audio.session.pwd.getpwnam', return_value=SimpleNamespace(pw_uid=0)):
            with self.assertRaisesRegex(ValueError, 'root'):
                audio_session_command(['pactl'], 'root')
