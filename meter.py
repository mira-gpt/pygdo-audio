"""In-process microphone level, without retaining samples or starting capture."""
import math
import threading
import time
from array import array
import sys
from typing import NamedTuple

import numpy as np


class AudioFeatures(NamedTuple):
    status: str
    gain: float
    frequency_hz: float | None


class MicrophoneMeter:
    _lock = threading.Lock()
    _status = 'unknown'
    _level = 0.0
    _frequency_hz = None
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
            cls._status, cls._level, cls._frequency_hz, cls._updated = state, 0.0, None, time.monotonic()
            callbacks = tuple(cls._subscribers)
        cls._notify(callbacks)

    @classmethod
    def update(cls, data, sample_rate=16000):
        if sample_rate <= 0:
            raise ValueError('Sample rate must be positive')
        samples = array('h')
        samples.frombytes(data)
        if sys.byteorder != 'little':
            samples.byteswap()
        level = math.sqrt(sum((value / 32768.0) ** 2 for value in samples) / len(samples)) if samples else 0.0
        frequency = None
        if len(samples) >= 32 and level >= .001:
            signal = np.asarray(samples, dtype=np.float64)
            signal -= np.mean(signal)
            spectrum = np.abs(np.fft.rfft(signal * np.hanning(len(signal))))
            spectrum[0] = 0
            peak = int(np.argmax(spectrum))
            if peak and spectrum[peak] > 1e-6:
                frequency = peak * sample_rate / len(signal)
        with cls._lock:
            cls._status, cls._level, cls._frequency_hz, cls._updated = 'on', min(level, 1.0), frequency, time.monotonic()
            callbacks = tuple(cls._subscribers)
        cls._notify(callbacks)

    @classmethod
    def snapshot(cls, now=None):
        features = cls.features(now)
        return features.status, features.gain

    @classmethod
    def features(cls, now=None):
        """Current input RMS and dominant spectral frequency; never stores audio."""
        with cls._lock:
            status, level, frequency, updated = cls._status, cls._level, cls._frequency_hz, cls._updated
        now = time.monotonic() if now is None else now
        if status == 'on' and now - updated > 2:
            return AudioFeatures('unknown', 0.0, None)
        return AudioFeatures(status, level, frequency)
