"""Process-local microphone pipeline counters; never retain speech or text."""
import json
import os
import tempfile
import time

from gdo.base.Application import Application


class MicrophoneDiagnostics:
    def __init__(self):
        self.data = {'pid': os.getpid(), 'started': time.time(), 'state': 'starting',
                     'capture_chunks': 0, 'segments': 0, 'whisper_started': 0,
                     'whisper_finished': 0, 'empty_results': 0,
                     'silence_rejected': 0, 'filtered_results': 0, 'delivered': 0}
        self.last_write = 0.0
        self.path = Application.temp_path(f'microphone-status-{os.getpid()}.json')

    def mark(self, stage, *, count=False, force=False, **fields):
        now = time.time()
        self.data['last_' + stage] = now
        if count:
            self.data[stage] = self.data.get(stage, 0) + 1
        self.data.update(fields)
        if not force and now - self.last_write < 1:
            return
        self.last_write = now
        path = None
        try:
            fd, path = tempfile.mkstemp(prefix='.mic-status-', dir=os.path.dirname(self.path))
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(self.data, stream)
            os.replace(path, self.path)
        except OSError:
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass


class TimedSTT:
    def __init__(self, backend, diagnostics):
        self.backend = backend
        self.diagnostics = diagnostics

    async def transcribe(self, chunk):
        started = time.monotonic()
        self.diagnostics.mark('whisper_started', count=True, force=True, state='transcribing')
        try:
            text = await self.backend.transcribe(chunk)
        except Exception:
            self.diagnostics.mark('whisper_error', force=True, state='error')
            raise
        self.diagnostics.mark('whisper_finished', count=True, force=True, state='listening',
                              last_processing_seconds=round(time.monotonic() - started, 3))
        if not text.strip():
            self.diagnostics.mark('empty_results', count=True, force=True)
        return text
