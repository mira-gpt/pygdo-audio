"""In-process microphone level, without retaining samples or starting capture."""
import math
import threading
import time
from array import array
import sys


class MicrophoneMeter:
    _lock = threading.Lock()
    _status = 'unknown'
    _level = 0.0
    _updated = 0.0
    _subscribers = set()
    _transcription = 'unknown'
    _transcription_text = ''

    @classmethod
    def transcription_state(cls, state):
        if state not in ('off', 'starting', 'on', 'error', 'unknown'):
            raise ValueError('Invalid transcription state')
        with cls._lock:
            if cls._transcription == state:
                return
            cls._transcription = state
            cls._transcription_text = ''
            callbacks = tuple(cls._subscribers)
        cls._notify(callbacks)

    @classmethod
    def transcription_snapshot(cls):
        with cls._lock:
            return cls._transcription

    @classmethod
    def set_transcription_text(cls, text):
        with cls._lock:
            if cls._transcription != 'on' or not text:
                return
            cls._transcription_text = text
            callbacks = tuple(cls._subscribers)
        cls._notify(callbacks)

    @classmethod
    def transcription_text_snapshot(cls):
        with cls._lock:
            return cls._transcription_text if cls._transcription == 'on' else ''

    @classmethod
    def subscribe(cls, callback):
        with cls._lock:
            cls._subscribers.add(callback)

    @classmethod
    def unsubscribe(cls, callback):
        with cls._lock:
            cls._subscribers.discard(callback)

    @staticmethod
    def _notify(callbacks):
        for callback in callbacks:
            try:
                callback()
            except Exception:
                pass  # A display subscriber must not stop microphone capture.

    @classmethod
    def state(cls, state):
        with cls._lock:
            cls._status, cls._level, cls._updated = state, 0.0, time.monotonic()
            callbacks = tuple(cls._subscribers)
        cls._notify(callbacks)

    @classmethod
    def update(cls, data):
        samples = array('h')
        samples.frombytes(data)
        if sys.byteorder != 'little':
            samples.byteswap()
        level = math.sqrt(sum((value / 32768.0) ** 2 for value in samples) / len(samples)) if samples else 0.0
        with cls._lock:
            cls._status, cls._level, cls._updated = 'on', min(level, 1.0), time.monotonic()
            callbacks = tuple(cls._subscribers)
        cls._notify(callbacks)

    @classmethod
    def snapshot(cls, now=None):
        with cls._lock:
            status, level, updated = cls._status, cls._level, cls._updated
        now = time.monotonic() if now is None else now
        if status == 'on' and now - updated > 2:
            return 'unknown', 0.0
        return status, level
