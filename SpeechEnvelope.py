"""Approximate speech rhythm from synthesized WAV, without storing audio."""
import io
import math
import struct
import wave


def speech_envelope(data, step_ms=50):
    """Return normalized short-window RMS levels; unsupported WAV gives []."""
    try:
        with wave.open(io.BytesIO(data), 'rb') as wav:
            if wav.getsampwidth() != 2 or wav.getnchannels() not in (1, 2):
                return []
            count = max(1, wav.getframerate() * step_ms // 1000)
            levels = []
            while len(levels) < 2400:
                chunk = wav.readframes(count)
                if not chunk:
                    break
                samples = struct.iter_unpack('<h', chunk[:len(chunk) // 2 * 2])
                values = [value for (value,) in samples]
                if not values:
                    break
                levels.append(math.sqrt(sum(v * v for v in values) / len(values)))
            peak = max(levels, default=0)
            if peak < 1:
                return [0.0] * len(levels)
            return [round(min(1.0, value / peak * 1.6), 3) for value in levels]
    except (EOFError, wave.Error, ValueError, struct.error):
        return []
