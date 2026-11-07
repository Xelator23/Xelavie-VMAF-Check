#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
    exec python3 "$SCRIPT_DIR/vmaf_launcher.py" "$@"
fi
for arg in "$@"; do
    if [ "$arg" = '--no-download' ]; then
        echo 'Python 3.10+ fehlt; --no-download verhindert den Bootstrap.' >&2
        exit 1
    fi
done
if ! command -v uv >/dev/null 2>&1; then
    echo 'Python 3.10+ oder bereits installiertes uv erforderlich. uv wird nicht automatisch installiert.' >&2
    exit 1
fi
echo 'Python fehlt. Verwende vorhandenes uv fuer Python 3.12 ...'
exec uv run --no-config --no-project --python 3.12 "$SCRIPT_DIR/vmaf_launcher.py" "$@"
