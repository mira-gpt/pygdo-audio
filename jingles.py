from pathlib import Path


JINGLES = {'v8': Path(__file__).resolve().parent / 'jingles' / 'v8.mp3'}


def jingle_path(key: str) -> Path:
    try:
        path = JINGLES[key]
    except KeyError:
        raise ValueError(f'Unknown jingle: {key}') from None
    if not path.is_file():
        raise ValueError(f'Jingle file is missing: {key}')
    return path
