"""In-process speech playback state for plugins; contains no audio or text."""
from threading import Lock


class SpeechPlayback:
    _lock = Lock()
    _active = set()

    @classmethod
    def start(cls, speech_id):
        with cls._lock:
            cls._active.add(speech_id)

    @classmethod
    def end(cls, speech_id):
        with cls._lock:
            cls._active.discard(speech_id)

    @classmethod
    def is_playing(cls):
        with cls._lock:
            return bool(cls._active)
