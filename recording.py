"""Explicit, bounded recordings from the existing microphone stream."""
import os
import tempfile
import threading
import wave

from gdo.audio.meter import MicrophoneMeter
from gdo.base.Application import Application
from gdo.base.Logger import Logger


class Recorder:
    _lock = threading.RLock()
    _wave = None
    _path = None
    _bytes = 0
    MAX_BYTES = 30 * 16000 * 2

    @classmethod
    def start(cls):
        with cls._lock:
            if cls._wave:
                raise RuntimeError('A microphone recording is already active')
            if MicrophoneMeter.snapshot()[0] != 'on':
                raise RuntimeError('The microphone listener is not receiving audio')
            directory = tempfile.mkdtemp(prefix='audio-record-', dir=Application.temp_path())
            path = os.path.join(directory, 'recording.wav')
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                stream = os.fdopen(fd, 'wb')
                output = wave.open(stream, 'wb')
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(16000)
            except Exception:
                os.close(fd)
                raise
            cls._stream, cls._wave, cls._path, cls._bytes = stream, output, path, 0
            return path

    @classmethod
    def feed(cls, data):
        with cls._lock:
            if not cls._wave:
                return
            data = data[:max(0, cls.MAX_BYTES - cls._bytes)]
            cls._wave.writeframesraw(data)
            cls._bytes += len(data)
            if cls._bytes >= cls.MAX_BYTES:
                Logger.warning('Microphone recording reached its 30-second limit.')
                cls.stop()

    @classmethod
    def stop(cls):
        with cls._lock:
            if not cls._wave:
                return None
            path = cls._path
            try:
                cls._wave.close()
                cls._stream.close()
            finally:
                cls._wave = cls._stream = cls._path = None
            Logger.message(f'Microphone recording saved: {path}')
            return path

    @classmethod
    def stop_if_requested(cls, text):
        if text.strip().strip('.,!?').strip().casefold() in ('stop', 'stopp'):
            return cls.stop()
        return None
