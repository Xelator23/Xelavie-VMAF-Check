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
case "$(uname -m)" in
    x86_64) arch=x86_64; expected=287491da03f2a785c70fa75b13e1f849918c2f2b5415fe84876b8214eeb792f9 ;;
    aarch64|arm64) arch=aarch64; expected=2d3ec076a0c4c0e8250bb6418c44080828b544f1a3be0b6e46adf9fb6923de45 ;;
    *) echo 'Auto-Bootstrap unterstuetzt Linux x64/ARM64.' >&2; exit 1 ;;
esac
bootstrap_dir=$(mktemp -d "${TMPDIR:-/tmp}/vmaf-bootstrap.XXXXXXXX")
cleanup() {
    case "$bootstrap_dir" in
        "${TMPDIR:-/tmp}"/vmaf-bootstrap.*) rm -rf -- "$bootstrap_dir" ;;
    esac
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
asset="uv-$arch-unknown-linux-musl.tar.gz"
url="https://github.com/astral-sh/uv/releases/download/0.13.7/$asset"
echo 'Python fehlt. Lade geprueften temporaeren uv/Python-Bootstrap ...'
if command -v curl >/dev/null 2>&1; then
    curl --fail --location --proto '=https' --tlsv1.2 --output "$bootstrap_dir/uv.tar.gz" "$url"
elif command -v wget >/dev/null 2>&1; then
    wget -O "$bootstrap_dir/uv.tar.gz" "$url"
else
    echo 'Zum initialen Download wird curl oder wget benoetigt.' >&2
    exit 1
fi
printf '%s  %s\n' "$expected" "$bootstrap_dir/uv.tar.gz" | sha256sum --check --status
tar -xzf "$bootstrap_dir/uv.tar.gz" -C "$bootstrap_dir"
export UV_CACHE_DIR="$bootstrap_dir/cache"
export UV_PYTHON_INSTALL_DIR="$bootstrap_dir/python"
export UV_PYTHON_BIN_DIR="$bootstrap_dir/bin"
export UV_NO_CONFIG=1
"$bootstrap_dir/uv-$arch-unknown-linux-musl/uv" run --no-project --python 3.12 "$SCRIPT_DIR/vmaf_launcher.py" "$@"
