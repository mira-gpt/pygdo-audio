from collections import deque
import asyncio

import numpy as np

from gdo.audio.pcm import PCMChunk, PCMRoute
from gdo.base.Logger import Logger


class SpeechTurns:
    """Group 16 kHz mono PCM into turns using short pauses as boundaries."""

    FRAME_BYTES = 3200  # 100 ms, 16 kHz mono signed 16-bit PCM

    def __init__(self, threshold=0.003, silence_frames=12, max_frames=120):
        self.threshold = threshold
        self.silence_frames = silence_frames
        self.max_frames = max_frames
        self.pending = bytearray()
        self.preroll = deque(maxlen=3)
        self.frames = []
        self.quiet = 0

    def _frame(self, frame):
        audio = np.frombuffer(frame, dtype='<i2').astype(np.float32) / 32768.0
        loud = bool(audio.size and float(np.sqrt(np.mean(audio * audio))) >= self.threshold)
        if not self.frames:
            if not loud:
                self.preroll.append(frame)
                return None
            self.frames = [*self.preroll, frame]
            self.preroll.clear()
        else:
            self.frames.append(frame)
        self.quiet = 0 if loud else self.quiet + 1
        if self.quiet >= self.silence_frames or len(self.frames) >= self.max_frames:
            return self._flush()
        return None

    def _flush(self):
        if not self.frames:
            return None
        data = b''.join(self.frames)
        self.frames = []
        self.preroll.clear()
        self.quiet = 0
        return data

    def feed(self, data):
        self.pending.extend(data)
        output = []
        while len(self.pending) >= self.FRAME_BYTES:
            frame = bytes(self.pending[:self.FRAME_BYTES])
            del self.pending[:self.FRAME_BYTES]
            if segment := self._frame(frame):
                output.append(segment)
        return output

    def finish(self):
        if self.pending:
            tail = bytes(self.pending[:len(self.pending) - len(self.pending) % 2])
            self.pending.clear()
            if tail:
                if segment := self._frame(tail):
                    return segment
        return self._flush()


async def segment_speech(source: PCMRoute, destination: PCMRoute, on_segment=None):
    if source.pcm_format != destination.pcm_format:
        raise ValueError('Speech routes must use the same PCM format.')
    segmenter = SpeechTurns()
    sequence = 0
    previous = None

    def send(data):
        nonlocal sequence
        try:
            destination.feed_input(PCMChunk(destination.pcm_format, sequence, data))
            if on_segment:
                on_segment()
        except asyncio.QueueFull:
            Logger.warning('Microphone transcription queue is full; a speech turn was dropped.')
        sequence += 1

    try:
        while (chunk := await source.read_input()) is not None:
            if previous is not None and chunk.sequence != previous + 1:
                if tail := segmenter.finish():
                    send(tail)
                Logger.warning('Microphone capture dropped audio; starting a new speech turn.')
            previous = chunk.sequence
            for segment in segmenter.feed(chunk.data):
                send(segment)
        if tail := segmenter.finish():
            send(tail)
    finally:
        destination.close()
