import unittest
from unittest.mock import Mock, patch

from gdo.audio.method.audio import audio
from gdo.base.Application import Application
from gdo.base.Render import Mode


class AudioCommandsTest(unittest.TestCase):
    def test_list_filters_hidden_and_unauthorized_methods(self):
        Application.mode(Mode.render_cli)
        commands = []
        for trigger, allowed, hidden in (('audio.say', True, False),
                                         ('audio.secret', False, False),
                                         ('audio.ipc', True, True)):
            command = Mock()
            command.gdo_module.return_value.get_name = 'audio'
            command.gdo_trigger.return_value = trigger
            command.has_permission.return_value = allowed
            command.gdo_method_hidden.return_value = hidden
            command.allows_connector.return_value = True
            commands.append(command)
        loader = Mock()
        loader._methods = {str(i): (lambda command=command: command) for i, command in enumerate(commands)}
        method = audio()
        method._env_user = Mock()
        with patch('gdo.core.ModuleCommandList.ModuleLoader.instance', return_value=loader):
            text = method.gdo_execute().render(Mode.render_cli)
        self.assertIn('audio.say', text)
        self.assertNotIn('audio.secret', text)
        self.assertNotIn('audio.ipc', text)
