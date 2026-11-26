"""Bounded speech requests split into IPC-sized pieces and playback chunks."""
import base64
import math
import time
import uuid

MAX_SPEECH_BYTES = 4096
PART_BYTES = 300
MAX_PARTS = math.ceil(MAX_SPEECH_BYTES / PART_BYTES)


def ipc_parts(text, language):
    data = text.encode('utf-8')
    if len(data) > MAX_SPEECH_BYTES:
        raise ValueError('Speech text is limited to 4096 UTF-8 bytes')
    request = uuid.uuid4().hex
    parts = [data[i:i + PART_BYTES] for i in range(0, len(data), PART_BYTES)]
    return [[request, str(index), str(len(parts)), base64.b64encode(part).decode('ascii'), language]
            for index, part in enumerate(parts)]


def playback_chunks(text, limit=300):
    """Prefer whitespace boundaries and keep every character exactly once."""
    while len(text) > limit:
        cut = text.rfind(' ', 0, limit + 1)
        if cut < limit // 2:
            cut = limit
        else:
            cut += 1
        yield text[:cut]
        text = text[cut:]
    if text:
        yield text


class SpeechChunkBuffer:
    def __init__(self):
        self.pending = {}

    def add(self, request, index, total, encoded, language):
        now = time.monotonic()
        self.pending = {key: value for key, value in self.pending.items() if now - value['created'] < 300}
        if not (len(request) == 32 and all(c in '0123456789abcdef' for c in request)
                and 1 <= total <= MAX_PARTS and 0 <= index < total):
            raise ValueError('Invalid speech chunk metadata')
        part = base64.b64decode(encoded, validate=True)
        if not part or len(part) > PART_BYTES:
            raise ValueError('Invalid speech chunk size')
        if request not in self.pending:
            if len(self.pending) >= 128:
                raise ValueError('Too many pending speech requests')
            self.pending[request] = {'created': now, 'total': total, 'language': language, 'parts': {}}
        entry = self.pending[request]
        if entry['total'] != total or entry['language'] != language:
            raise ValueError('Inconsistent speech chunks')
        previous = entry['parts'].get(index)
        if previous is not None and previous != part:
            raise ValueError('Conflicting speech chunk')
        entry['parts'][index] = part
        if len(entry['parts']) != total:
            return None
        del self.pending[request]
        data = b''.join(entry['parts'][i] for i in range(total))
        if len(data) > MAX_SPEECH_BYTES:
            raise ValueError('Speech text is limited to 4096 UTF-8 bytes')
        return data.decode('utf-8'), language
