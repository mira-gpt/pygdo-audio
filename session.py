import os
import pwd


def audio_session_command(command: list[str], session_user: str | None = None) -> list[str]:
    """Run an audio client in an explicitly chosen user's desktop session."""
    if not session_user:
        return command
    account = pwd.getpwnam(session_user)
    if account.pw_uid == 0:
        raise ValueError('The audio session must not run as root.')
    prefix = [] if os.geteuid() == account.pw_uid else ['sudo', '-n', '-u', account.pw_name, '--']
    return [*prefix, 'env', f'XDG_RUNTIME_DIR=/run/user/{account.pw_uid}', *command]
