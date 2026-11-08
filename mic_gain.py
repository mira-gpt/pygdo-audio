"""Monitor explicit desktop microphone mute/zero gain, not signal silence."""
import asyncio
import json

from gdo.audio.microphone import default_microphone
from gdo.audio.session import audio_session_command


def source_enabled(sources, name):
    """Return True/False, or None if the audio server cannot establish state."""
    source = next((item for item in sources if isinstance(item, dict) and item.get('name') == name), None)
    if not source or not isinstance(source.get('mute'), bool):
        return None
    if source['mute']:
        return False
    volume = source.get('volume')
    if not isinstance(volume, dict) or not volume:
        return None
    values = [channel.get('value') if isinstance(channel, dict) else None for channel in volume.values()]
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in values):
        return None
    return any(value > 0 for value in values)


async def read_source_state(session_user):
    name = await default_microphone(session_user)
    process = await asyncio.create_subprocess_exec(
        *audio_session_command(['pactl', '-f', 'json', 'list', 'sources'], session_user),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        output, _ = await asyncio.wait_for(process.communicate(), timeout=3)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise
    if process.returncode:
        raise RuntimeError('Cannot query microphone source state')
    sources = json.loads(output)
    if not isinstance(sources, list):
        raise ValueError('Invalid microphone source list')
    return name, source_enabled(sources, name)


class MicGainMonitor:
    def __init__(self, module):
        self.module = module
        self.last = None

    async def reconcile(self):
        from gdo.base.Application import Application
        try:
            name, enabled = await read_source_state(
                self.module.get_config_val('audio_microphone_session_user') or None)
        except (OSError, ValueError, RuntimeError, asyncio.TimeoutError):
            self.last = None
            return
        if enabled is None:
            self.last = None
            return
        current = (name, enabled)
        if current != self.last:
            self.last = current
            await Application.EVENTS.publish('audio_mic_enabled' if enabled else 'audio_mic_disabled')
