"""Shared, version-independent workspace preference for CLI and UI."""
import json
import os
from pathlib import Path
import tempfile


def config_path():
    if os.environ.get('VMAF_SETTINGS_FILE'):
        return Path(os.environ['VMAF_SETTINGS_FILE'])
    base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) if os.name == 'nt' else Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    return base / 'VMAF-Check' / 'settings.json'


def work_directory():
    path = config_path()
    if path.exists():
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('work_dir'):
            return Path(data['work_dir']).expanduser().resolve()
    return (Path.cwd() / 'VMAF-Arbeit').resolve()


def save_work_directory(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Arbeitsordner angeben.')
    directory = Path(value).expanduser().resolve()
    for name in ('Temp', 'Ergebnisse'):
        (directory / name).mkdir(parents=True, exist_ok=True)
    target = config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=target.parent, prefix='settings-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump({'work_dir': str(directory)}, out, ensure_ascii=False, indent=2)
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return directory
