from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
import re
from typing import Protocol


class WhisperModel(Protocol):

    def transcribe(self, audio: str, language: str) -> dict:
        ...


ChatStreamEmitter = Callable[[str], Awaitable[None]]
WhisperModelLoader = Callable[[str], WhisperModel]

CALL_ID_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
LANGUAGE_PATTERN = re.compile(r'^[a-z]{2}$')


def load_whisper_model(model_name: str) -> WhisperModel:
    try:
        import whisper
    except ImportError as error:
        raise RuntimeError('Whisper is not installed.') from error
    return whisper.load_model(model_name)


def render_chatstream(channel_id: int, call_id: str, sequence: int, language: str, text: str) -> str:
    if channel_id < 1:
        raise ValueError('Chat stream channel id must be positive.')
    if not CALL_ID_PATTERN.fullmatch(call_id):
        raise ValueError('Chat stream call id is invalid.')
    if sequence < 0:
        raise ValueError('Chat stream sequence must not be negative.')
    if not LANGUAGE_PATTERN.fullmatch(language):
        raise ValueError('Chat stream language must be an ISO 639-1 code.')
    return f'$chatstream {channel_id} --lang={language} --call={call_id} --seq={sequence} --status=final\n{text}'


async def transcribe_file(
    audio_file: str | Path,
    channel_id: int,
    call_id: str,
    sequence: int,
    emit: ChatStreamEmitter,
    language: str = 'de',
    model_name: str = 'base',
    model_loader: WhisperModelLoader = load_whisper_model,
) -> str:
    path = Path(audio_file)
    if not path.is_file():
        raise ValueError('Audio file does not exist.')
    model = await asyncio.to_thread(model_loader, model_name)
    result = await asyncio.to_thread(model.transcribe, str(path), language=language)
    text = result.get('text', '')
    if not isinstance(text, str):
        raise ValueError('Whisper did not return transcript text.')
    event = render_chatstream(channel_id, call_id, sequence, language, text.strip())
    await emit(event)
    return event
