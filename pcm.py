from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass(frozen=True)
class PCMFormat:
    sample_rate: int
    channels: int
    sample_width: int

    def __post_init__(self):
        if self.sample_rate < 1:
            raise ValueError('PCM sample rate must be positive.')
        if self.channels < 1:
            raise ValueError('PCM channel count must be positive.')
        if self.sample_width < 1:
            raise ValueError('PCM sample width must be positive.')

    @property
    def frame_size(self) -> int:
        return self.channels * self.sample_width

    @property
    def bytes_per_second(self) -> int:
        return self.sample_rate * self.frame_size


@dataclass(frozen=True)
class PCMChunk:
    pcm_format: PCMFormat
    sequence: int
    data: bytes

    def __post_init__(self):
        if self.sequence < 0:
            raise ValueError('PCM chunk sequence must not be negative.')
        if len(self.data) % self.pcm_format.frame_size:
            raise ValueError('PCM chunk data must contain complete frames.')

    @property
    def frame_count(self) -> int:
        return len(self.data) // self.pcm_format.frame_size

    @property
    def duration_seconds(self) -> float:
        return self.frame_count / self.pcm_format.sample_rate


class PCMRoute:

    def __init__(self, pcm_format: PCMFormat, capacity: int = 32):
        if capacity < 1:
            raise ValueError('PCM route capacity must be positive.')
        self.pcm_format = pcm_format
        self._input: asyncio.Queue[PCMChunk | None] = asyncio.Queue(capacity)
        self._output: asyncio.Queue[PCMChunk | None] = asyncio.Queue(capacity)
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def feed_input(self, chunk: PCMChunk) -> None:
        self._validate(chunk)
        self._put(self._input, chunk)

    async def read_input(self) -> PCMChunk | None:
        return await self._read(self._input)

    def write_output(self, chunk: PCMChunk) -> None:
        self._validate(chunk)
        self._put(self._output, chunk)

    async def read_output(self) -> PCMChunk | None:
        return await self._read(self._output)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._close_queue(self._input)
        self._close_queue(self._output)

    def _validate(self, chunk: PCMChunk) -> None:
        if self._closed:
            raise RuntimeError('PCM route is closed.')
        if chunk.pcm_format != self.pcm_format:
            raise ValueError('PCM chunk format does not match route format.')

    @staticmethod
    def _close_queue(queue: asyncio.Queue[PCMChunk | None]) -> None:
        if queue.empty():
            queue.put_nowait(None)

    async def _read(self, queue: asyncio.Queue[PCMChunk | None]) -> PCMChunk | None:
        if self._closed and queue.empty():
            return None
        return await queue.get()

    @staticmethod
    def _put(queue: asyncio.Queue[PCMChunk | None], chunk: PCMChunk) -> None:
        queue.put_nowait(chunk)
