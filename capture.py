from __future__ import annotations

import asyncio
import os
import signal
from dataclasses import dataclass

from gdo.audio.pcm import PCMChunk, PCMRoute
from gdo.audio.stt import WhisperPCMBackend
from gdo.audio.session import audio_session_command


@dataclass(frozen=True)
class CaptureStats:
    chunks: int
    dropped: int


async def capture_pulse(route: PCMRoute, source: str, chunk_seconds: int = 4,
                        session_user: str | None = None, on_audio=None) -> CaptureStats:
    """Capture an explicitly selected PulseAudio source until EOF or cancellation."""
    if not source or source == 'default':
        raise ValueError('An explicit microphone source is required.')
    if route.pcm_format != WhisperPCMBackend.FORMAT:
        raise ValueError('Capture currently requires 16 kHz mono 16-bit PCM.')
    if type(chunk_seconds) not in (int, float) or not 0.1 <= chunk_seconds <= 30:
        raise ValueError('Chunk duration must be 0.1–30 seconds.')
    size = int(route.pcm_format.bytes_per_second * chunk_seconds)
    size -= size % route.pcm_format.frame_size
    command = audio_session_command([
        'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
        '-f', 'pulse', '-i', source, '-ac', '1', '-ar', '16000',
        '-f', 's16le', 'pipe:1'], session_user)
    process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE,
                                                   start_new_session=True)
    sequence = 0
    dropped = 0
    try:
        while True:
            try:
                data = await process.stdout.readexactly(size)
            except asyncio.IncompleteReadError as error:
                data = error.partial
                data = data[:len(data) - len(data) % route.pcm_format.frame_size]
                if data:
                    if on_audio:
                        on_audio(data)
                    try:
                        route.feed_input(PCMChunk(route.pcm_format, sequence, data))
                    except asyncio.QueueFull:
                        dropped += 1
                    sequence += 1
                break
            if on_audio:
                on_audio(data)
            try:
                route.feed_input(PCMChunk(route.pcm_format, sequence, data))
            except asyncio.QueueFull:
                dropped += 1
            sequence += 1
        if await process.wait():
            raise RuntimeError('Microphone capture failed.')
        return CaptureStats(sequence, dropped)
    finally:
        if process.returncode is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            await process.wait()
