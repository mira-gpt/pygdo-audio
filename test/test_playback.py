import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.audio.playback import play_file


class PlaybackTest(unittest.IsolatedAsyncioTestCase):
    async def test_uses_explicit_sink(self):
        process = MagicMock()
        process.wait = AsyncMock(return_value=0)
        with patch('gdo.audio.playback.asyncio.create_subprocess_exec',
                   new_callable=AsyncMock, return_value=process) as spawn:
            await play_file(Path('/tmp/remix.mp3'), 'mira_effects')
        args = spawn.call_args.args
        self.assertEqual(args[args.index('-device') + 1], 'mira_effects')
        self.assertIn('/tmp/remix.mp3', args)

    async def test_requires_explicit_sink(self):
        with self.assertRaisesRegex(ValueError, 'not configured'):
            await play_file(Path('/tmp/remix.mp3'), '')
