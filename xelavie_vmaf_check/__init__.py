"""Installed command entry point; portable launchers use the same source files."""
import sys


def main():
    from .vmaf_launcher import main as launch
    try:
        return launch()
    except (ValueError, OSError, EOFError) as exc:
        print('FEHLER:', exc, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
