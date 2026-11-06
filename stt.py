from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal, Protocol

from gdo.audio.pcm import PCMChunk, PCMFormat, PCMRoute


@dataclass(frozen=True)
class TranscriptEvent:
    stream_id: str
    sequence: int
    status: Literal['partial', 'final']
    text: str
    missing_chunks: int = 0


class STTBackend(Protocol):
    async def transcribe(self, chunk: PCMChunk) -> str: ...


class SilenceGate:
    """Skip quiet signed 16-bit PCM chunks before calling an STT backend."""

    def __init__(self, backend: STTBackend, threshold: float = 0.003, on_silence=None):
        if not 0 <= threshold <= 1:
            raise ValueError('Silence threshold must be between 0 and 1.')
        self.backend = backend
        self.threshold = threshold
        self.on_silence = on_silence

    async def transcribe(self, chunk: PCMChunk) -> str:
        if chunk.pcm_format.sample_width != 2:
            raise ValueError('Silence gate requires signed 16-bit little-endian PCM.')
        import numpy as np
        audio = np.frombuffer(chunk.data, dtype='<i2').astype(np.float32) / 32768.0
        if not audio.size or float(np.sqrt(np.mean(audio * audio))) < self.threshold:
            if self.on_silence:
                self.on_silence()
            return ''
        return await self.backend.transcribe(chunk)


class STTStream:
    def __init__(self, stream_id: str, backend: STTBackend):
        if not stream_id or len(stream_id) > 128:
            raise ValueError('Stream ID must contain 1–128 characters.')
        self.stream_id = stream_id
        self.backend = backend
        self._running = False

    async def run(self, route: PCMRoute, emit: Callable[[TranscriptEvent], Awaitable[None]]) -> None:
        if self._running:
            raise RuntimeError('STT stream is already running.')
        self._running = True
        previous = None
        missing = 0
        try:
            while (chunk := await route.read_input()) is not None:
                if previous is not None:
                    if chunk.sequence <= previous:
                        raise ValueError('PCM chunk sequences must increase.')
                    missing += chunk.sequence - previous - 1
                previous = chunk.sequence
                text = await self.backend.transcribe(chunk)
                if not isinstance(text, str):
                    raise ValueError('STT backend must return text.')
                text = text.strip()
                if text or missing:
                    await emit(TranscriptEvent(self.stream_id, chunk.sequence, 'final', text, missing))
                    missing = 0
        finally:
            self._running = False


class WhisperPCMBackend:
    """Chunked local Whisper; the caller supplies an already-loaded model."""

    FORMAT = PCMFormat(sample_rate=16000, channels=1, sample_width=2)

    def __init__(self, model, language: str | None = None, normalize: bool = False):
        self.model = model
        self.language = language
        self.normalize = normalize
        self._lock = asyncio.Lock()

    async def transcribe(self, chunk: PCMChunk) -> str:
        if chunk.pcm_format != self.FORMAT:
            raise ValueError('Whisper requires 16 kHz mono signed 16-bit little-endian PCM.')
        import numpy as np
        audio = np.frombuffer(chunk.data, dtype='<i2').astype(np.float32) / 32768.0
        if self.normalize and audio.size:
            peak = float(np.max(np.abs(audio)))
            rms = float(np.sqrt(np.mean(audio * audio)))
            if 0 < peak < .9 and rms > 0:
                gain = min(8.0, .06 / rms, .9 / peak)
                if gain > 1:
                    audio *= gain
        async with self._lock:
            result = await asyncio.to_thread(self.model.transcribe, audio, language=self.language, fp16=False)
        text = result.get('text', '')
        if not isinstance(text, str):
            raise ValueError('Whisper did not return transcript text.')
        return text
