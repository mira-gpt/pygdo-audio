import asyncio
from pathlib import Path


async def play_file(path: Path, output_device: str) -> None:
    """Play a local file through an explicit PulseAudio/PipeWire sink."""
    if not output_device:
        raise ValueError('Audio output device is not configured')
    process = await asyncio.create_subprocess_exec(
        'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
        '-re', '-i', str(path), '-vn', '-f', 'pulse', '-device', output_device, 'pygdo-audio',
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    try:
        if await process.wait():
            raise RuntimeError('Audio playback failed')
    except asyncio.CancelledError:
        process.terminate()
        await process.wait()
        raise
