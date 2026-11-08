import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.audio.mic_gain import MicGainMonitor, source_enabled
from gdo.base.Application import Application


class MicGainTest(unittest.IsolatedAsyncioTestCase):
    def test_explicit_mute_and_all_channels_zero(self):
        source = {'name': 'mic', 'mute': False, 'volume': {'L': {'value': 0}, 'R': {'value': 1}}}
        self.assertTrue(source_enabled([source], 'mic'))
        source['volume']['R']['value'] = 0
        self.assertFalse(source_enabled([source], 'mic'))
        source['mute'] = True
        self.assertFalse(source_enabled([source], 'mic'))
        self.assertIsNone(source_enabled([source], 'missing'))
        source['mute'] = False
        source['volume'] = {}
        self.assertIsNone(source_enabled([source], 'mic'))

    async def test_events_once_per_state_or_source_and_unknown_recovers(self):
        module = MagicMock()
        module.get_config_val.return_value = 'desktop'
        monitor = MicGainMonitor(module)
        events = MagicMock()
        events.publish = AsyncMock()
        values = [('mic', True), ('mic', True), ('mic', False),
                  ('mic', False), ('mic', None), ('mic', False), ('other', True)]
        with patch.object(Application, 'EVENTS', events, create=True), \
                patch('gdo.audio.mic_gain.read_source_state', new=AsyncMock(side_effect=values)):
            for _ in values:
                await monitor.reconcile()
        self.assertEqual(['audio_mic_enabled', 'audio_mic_disabled',
                          'audio_mic_disabled', 'audio_mic_enabled'],
                         [call.args[0] for call in events.publish.await_args_list])

    async def test_query_failure_does_not_claim_disabled(self):
        module = MagicMock()
        monitor = MicGainMonitor(module)
        events = MagicMock()
        events.publish = AsyncMock()
        with patch.object(Application, 'EVENTS', events, create=True), \
                patch('gdo.audio.mic_gain.read_source_state', new=AsyncMock(side_effect=RuntimeError('not available'))):
            await monitor.reconcile()
        events.publish.assert_not_awaited()
