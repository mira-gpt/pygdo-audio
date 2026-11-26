import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import msgspec.json
from gdo.audio.SpeechChunks import SpeechChunkBuffer, ipc_parts, playback_chunks
from gdo.audio.method.say import say
from gdo.audio.method.ipc_say import ipc_say
from gdo.audio.method.ipc_say_chunk import ipc_say_chunk
from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Render import Mode


class SpeechChunksTest(unittest.TestCase):
    def test_transfer_reassembles_out_of_order_and_preserves_unicode(self):
        text = ('Café 🦆 --quote="hi"\n' * 100)[:800]
        parts = ipc_parts(text, 'fr')
        buffer = SpeechChunkBuffer()
        result = None
        for request, index, total, encoded, language in reversed(parts):
            self.assertLessEqual(len(msgspec.json.encode([request, index, total, encoded, language])), IPC.MAX_EVENT_ARG_SIZE)
            result = buffer.add(request, int(index), int(total), encoded, language)
        self.assertEqual((text, 'fr'), result)

    def test_playback_chunks_preserve_all_characters(self):
        text = 'Hello world. ' * 90
        parts = list(playback_chunks(text))
        self.assertEqual(text, ''.join(parts))
        self.assertTrue(all(len(part) <= 300 for part in parts))

    def test_byte_limit_and_conflicting_parts(self):
        self.assertTrue(ipc_parts('ä' * 2048, 'de'))
        with self.assertRaises(ValueError):
            ipc_parts('ä' * 2049, 'de')
        parts = ipc_parts('x' * 301, 'en')
        request, index, total, encoded, language = parts[0]
        buffer = SpeechChunkBuffer()
        self.assertIsNone(buffer.add(request, int(index), int(total), encoded, language))
        with self.assertRaises(ValueError):
            buffer.add(request, int(index), int(total), 'YQ==', language)

    def test_4k_request_is_sent_as_bounded_ipc_pieces(self):
        Application.mode(Mode.render_cli)
        method = say()
        method.param_val = MagicMock(side_effect=lambda key: {'text': 'ä' * 2048, 'lang': 'de'}[key])
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
             patch.object(Application, 'IS_DOG', True), \
             patch('gdo.audio.method.say.IPC.send_to_dog') as send:
            method.gdo_execute()
        self.assertGreater(send.call_count, 1)
        self.assertTrue(all(call.args[0] == 'audio.ipc_say_chunk' for call in send.call_args_list))


class SpeechPlaybackChunksTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    async def test_each_playback_chunk_clones_language_in_order(self):
        text = 'Hello friend. ' * 80
        method = ipc_say().input('text', text).input('lang', 'fr')
        played = []
        async def play_one(speech, *_args):
            played.append((speech.param_val('text'), speech.param_val('lang')))
        with patch.object(ipc_say, '_play_one', autospec=True, side_effect=play_one):
            await method.play()
        self.assertGreater(len(played), 1)
        self.assertEqual(text, ''.join(part for part, _ in played))
        self.assertTrue(all(language == 'fr' and len(part) <= 300 for part, language in played))

    async def test_ipc_parts_reassemble_into_one_speech_request(self):
        text = '--hello 🦆 ' * 100
        parts = ipc_parts(text, 'en')
        buffer = SpeechChunkBuffer()
        with patch.object(Application, 'IS_DOG', True), \
             patch('gdo.audio.method.ipc_say_chunk.IPC.execute_dog_event', new_callable=AsyncMock) as execute:
            for part in reversed(parts):
                handler = ipc_say_chunk()
                handler.empty = MagicMock()
                handler.buffer = buffer
                handler._raw_args.add_cli_line(part)
                await handler.gdo_execute()
        execute.assert_awaited_once_with('audio.ipc_say', ['--text=' + text, '--lang=en'])
        reassembled = ipc_say()
        reassembled._raw_args.add_cli_line(execute.await_args.args[1])
        self.assertEqual(text, reassembled.param_val('text'))
        self.assertEqual('en', reassembled.param_val('lang'))
