VOICES = {'en': 'en-us+f3', 'de': 'de+f3', 'ko': 'ko', 'vi': 'vi', 'ja': 'ja'}
LANGUAGES = {'en': 'English', 'de': 'Deutsch', 'ko': '한국어', 'vi': 'Tiếng Việt', 'ja': '日本語'}


def speech_language(method, explicit=None):
    """Explicit choice, user preference, channel, server, then English."""
    if explicit:
        return explicit
    for name in ('_env_user', '_env_channel', '_env_server'):
        entity = getattr(method, name, None)
        if entity:
            language = entity.get_lang_iso()
            if language:
                return language
    return 'en'


