"""Run with an installed wheel's Python: python -I packaging_smoke.py."""
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from urllib.request import urlopen


def main():
    from xelavie_vmaf_check import vmaf_launcher as launcher
    from xelavie_vmaf_check import vmaf_cli, vmaf_check, vmaf_settings
    assert 'site-packages' in str(Path(launcher.__file__).resolve())
    version = importlib.metadata.version('xelavie-vmaf-check')
    assert vmaf_check.__version__.replace('-nightly.', '.dev') == version
    executable = Path(sys.executable).parent / ('xelavie-vmaf-check.exe' if os.name == 'nt' else 'xelavie-vmaf-check')
    with tempfile.TemporaryDirectory() as directory:
        os.environ['VMAF_SETTINGS_FILE'] = str(Path(directory)/'settings.json')
        for arguments, expected in [(['--version'], vmaf_check.__version__), (['--help'], '--percent'), ([], '--gui')]:
            result = subprocess.run([str(executable), *arguments], cwd=directory, input='', text=True, capture_output=True, timeout=20)
            assert result.returncode == 0, result.stderr
            assert expected in result.stdout, result.stdout
            assert 'Original-Datei:' not in result.stdout
        result = subprocess.run([str(executable), 'missing-original.mkv'], cwd=directory, input='', text=True, capture_output=True, timeout=20)
        assert result.returncode != 0  # Missing encode must fail, never prompt.
        # Load CLI code, engine subprocess and all UI assets from the installed wheel.
        assert callable(vmaf_cli.collect_inputs)
        vmaf_settings.save_work_directory(str(Path(directory)/'work'))
        server = launcher.Server()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for route, expected in [('', b'Pr'), ('logo.png', b'\x89PNG'), ('vmaf_navigation.js', b'const'), ('status', b'phase')]:
                with urlopen(server.origin+server.prefix+route, timeout=5) as response:
                    assert expected in response.read(), route
            with urlopen(server.origin+server.prefix+'settings', timeout=5) as response:
                assert json.load(response)['work_dir'] == str((Path(directory)/'work').resolve())
            assert (launcher.HERE/'download_windows.ps1').is_file()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
    print('Installed wheel: CLI, engine, UI assets, settings and version OK:', version)


if __name__ == '__main__':
    main()
