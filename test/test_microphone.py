import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.audio.microphone import MicrophoneController, microphone_event, run_microphone
from gdo.audio.pcm import PCMChunk
from gdo.audio.stt import TranscriptEvent


class MicrophoneTest(unittest.IsolatedAsyncioTestCase):
    def test_event_uses_bash_channel_and_operator_identity(self):
        event = TranscriptEvent('microphone-abc', 3, 'final', 'Hello\nworld')
        self.assertEqual(
            '$chatstream 12 --lang=en --call=microphone-abc --seq=3 --status=final --user=42\nHello world',
            microphone_event(12, '42', 'en', event))
        with self.assertRaises(ValueError):
            microphone_event(12, 'invalid', 'en', event)

    def test_computer_prefix_remains_plain_text(self):
        event = TranscriptEvent('microphone-abc', 3, 'final', 'Computer, mach den Vintage Effekt an')
        self.assertTrue(microphone_event(12, '42', 'de', event).endswith('\nComputer, mach den Vintage Effekt an'))
        event = TranscriptEvent('microphone-abc', 4, 'final', 'Mein Computer ist an')
        self.assertTrue(microphone_event(12, '42', 'de', event).endswith('\nMein Computer ist an'))

    async def test_non_dog_never_checks_or_starts_microphone(self):
        controller = MicrophoneController(MagicMock())
        with patch.object(controller, 'is_running_dog', return_value=False), \
                patch.object(controller, 'settings') as settings:
            await controller.reconcile()
        settings.assert_not_called()
        self.assertIsNone(controller.task)

    async def test_enabled_operator_starts_once_and_off_stops(self):
        controller = MicrophoneController(MagicMock())
        operator = MagicMock()
        operator.get_name.return_value = 'gizmore'
        bash = MagicMock()
        channel = bash.get_or_create_channel.return_value
        started = asyncio.Event()
        async def fake_run(_operator, _channel, _session_user, _language, _minimum):
            started.set()
            await asyncio.Event().wait()
        with patch.object(controller, 'is_running_dog', return_value=True), \
                patch.object(controller, 'settings', side_effect=[(True, '42', None, 'en', 4), (True, '42', None, 'en', 4), (False, '42', None, 'en', 4)]), \
                patch('gdo.core.GDO_User.GDO_User.table') as table, \
                patch('gdo.core.connector.Bash.Bash.get_server', return_value=bash), \
                patch('gdo.audio.microphone.run_microphone', side_effect=fake_run) as run:
            table.return_value.get_by_id.return_value = operator
            await controller.reconcile()
            await started.wait()
            await controller.reconcile()
            self.assertEqual(1, run.call_count)
            bash.get_or_create_channel.assert_called_once_with('gizmore', creator=operator)
            await controller.reconcile()
        self.assertIsNone(controller.task)

    async def test_missing_operator_never_starts_capture(self):
        controller = MicrophoneController(MagicMock())
        with patch.object(controller, 'is_running_dog', return_value=True), \
                patch.object(controller, 'settings', return_value=(True, None, None, 'en', 4)), \
                patch('gdo.audio.microphone.run_microphone') as run, \
                patch('gdo.audio.microphone.Logger.warning') as warning:
            await controller.reconcile()
            await controller.reconcile()
        run.assert_not_called()
        self.assertEqual(1, warning.call_count)

    async def test_pipeline_publishes_synthetic_pcm_to_chatstream(self):
        operator = MagicMock()
        operator.get_id.return_value = '42'
        channel = MagicMock()
        channel.get_id.return_value = '12'
        channel.get_lang_iso.return_value = 'en'
        channel.get_trigger.return_value = '$'
        model = MagicMock()
        model.transcribe.return_value = {'text': 'Hello Mira'}
        async def fake_capture(route, _source, **_kwargs):
            route.feed_input(PCMChunk(route.pcm_format, 0, b'\xff\x7f' * 3200 + b'\0\0' * 12800))
            from gdo.audio.capture import CaptureStats
            return CaptureStats(1, 0)
        events = MagicMock()
        events._subscribers = {'audio_chatstream': [object()]}
        events.publish = AsyncMock()
        with patch('gdo.audio.microphone.load_local_whisper', return_value=model), \
                patch('gdo.audio.microphone.default_microphone', new_callable=AsyncMock, return_value='test-source'), \
                patch('gdo.audio.microphone.capture_pulse', side_effect=fake_capture), \
                patch('gdo.audio.microphone.Logger.debug'), \
                patch('gdo.audio.microphone.Application.EVENTS', events, create=True):
            await run_microphone(operator, channel)
        message = events.publish.await_args.args
        self.assertEqual('audio_chatstream', message[0])
        self.assertIn('$chatstream 12 --lang=en', message[1])
        self.assertIn('--user=42\nHello Mira', message[1])

    async def test_quiet_speech_with_trailing_silence_reaches_whisper(self):
        operator, channel = MagicMock(), MagicMock()
        operator.get_id.return_value = '42'
        channel.get_id.return_value = '12'
        model = MagicMock()
        model.transcribe.return_value = {'text': 'Mikrofon Test'}
        async def fake_capture(route, _source, **_kwargs):
            # Speech RMS exceeds 0.003, but the whole segment RMS does not.
            route.feed_input(PCMChunk(route.pcm_format, 0, b'\x64\x00' * 3200 + b'\0\0' * 19200))
            from gdo.audio.capture import CaptureStats
            return CaptureStats(1, 0)
        events = MagicMock()
        events._subscribers = {'audio_chatstream': [object()]}
        events.publish = AsyncMock()
        with patch('gdo.audio.microphone.load_local_whisper', return_value=model), \
                patch('gdo.audio.microphone.default_microphone', new_callable=AsyncMock, return_value='test-source'), \
                patch('gdo.audio.microphone.capture_pulse', side_effect=fake_capture), \
                patch('gdo.audio.microphone.Logger.debug'), \
                patch('gdo.audio.microphone.Application.EVENTS', events, create=True):
            await run_microphone(operator, channel)
        model.transcribe.assert_called_once()
        self.assertIn('Mikrofon Test', events.publish.await_args.args[1])

    async def test_silent_audio_never_produces_a_chatstream_message(self):
        operator = MagicMock()
        operator.get_id.return_value = '42'
        channel = MagicMock()
        channel.get_id.return_value = '12'
        channel.get_lang_iso.return_value = 'en'
        model = MagicMock()
        async def fake_capture(route, _source, **_kwargs):
            route.feed_input(PCMChunk(route.pcm_format, 0, b'\0\0' * 200))
            from gdo.audio.capture import CaptureStats
            return CaptureStats(1, 0)
        events = MagicMock()
        events._subscribers = {'audio_chatstream': [object()]}
        events.publish = AsyncMock()
        with patch('gdo.audio.microphone.load_local_whisper', return_value=model), \
                patch('gdo.audio.microphone.default_microphone', new_callable=AsyncMock, return_value='test-source'), \
                patch('gdo.audio.microphone.capture_pulse', side_effect=fake_capture), \
                patch('gdo.audio.microphone.Logger.debug'), \
                patch('gdo.audio.microphone.Application.EVENTS', events, create=True):
            await run_microphone(operator, channel)
        model.transcribe.assert_not_called()
        events.publish.assert_not_awaited()

    async def test_short_transcript_is_not_sent(self):
        operator = MagicMock()
        operator.get_id.return_value = '42'
        channel = MagicMock()
        channel.get_id.return_value = '12'
        model = MagicMock()
        model.transcribe.return_value = {'text': 'H.'}
        async def fake_capture(route, _source, **_kwargs):
            route.feed_input(PCMChunk(route.pcm_format, 0, b'\xff\x7f' * 3200 + b'\0\0' * 12800))
            from gdo.audio.capture import CaptureStats
            return CaptureStats(1, 0)
        events = MagicMock()
        events._subscribers = {'audio_chatstream': [object()]}
        events.publish = AsyncMock()
        with patch('gdo.audio.microphone.load_local_whisper', return_value=model), \
                patch('gdo.audio.microphone.default_microphone', new_callable=AsyncMock, return_value='test-source'), \
                patch('gdo.audio.microphone.capture_pulse', side_effect=fake_capture), \
                patch('gdo.audio.microphone.Logger.debug'), \
                patch('gdo.audio.microphone.Application.EVENTS', events, create=True):
            await run_microphone(operator, channel)
        model.transcribe.assert_called_once()
        events.publish.assert_not_awaited()
