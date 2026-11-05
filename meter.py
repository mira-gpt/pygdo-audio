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

    @classmethod
    def state(cls, state):
        with cls._lock:
            cls._status, cls._level, cls._updated = state, 0.0, time.monotonic()

    @classmethod
    def update(cls, data):
        samples = array('h')
        samples.frombytes(data)
        if sys.byteorder != 'little':
            samples.byteswap()
        level = math.sqrt(sum((value / 32768.0) ** 2 for value in samples) / len(samples)) if samples else 0.0
        with cls._lock:
            cls._status, cls._level, cls._updated = 'on', min(level, 1.0), time.monotonic()

    @classmethod
    def snapshot(cls, now=None):
        with cls._lock:
            status, level, updated = cls._status, cls._level, cls._updated
        now = time.monotonic() if now is None else now
        if status == 'on' and now - updated > 2:
            return 'unknown', 0.0
        return status, level
