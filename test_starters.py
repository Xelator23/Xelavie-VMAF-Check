"""Launch real starter scripts with controlled prerequisite commands, no network."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


class StarterTests(unittest.TestCase):
    def launch(self, available, arguments=()):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            marker = folder/'called.txt'
            env = {**os.environ, 'VMAF_TEST_MARKER': str(marker)}
            if os.name == 'nt':
                fake = folder/'fake.ps1'
                fake.write_text("$args | ConvertTo-Json -Compress | Set-Content -LiteralPath $env:VMAF_TEST_MARKER\n$global:LASTEXITCODE=0\n")
                wrapper = folder/'wrapper.ps1'
                quote = lambda value: "'"+str(value).replace("'", "''")+"'"
                # Only prerequisite discovery is mocked; the production launcher is executed.
                wrapper.write_text("function Get-Command { param($Name, $ErrorAction, $CommandType)\n"
                    + "if ($Name -eq "+quote(available)+") { [pscustomobject]@{Source="+quote(fake)+"} }\n}\n"
                    + "& "+quote(ROOT/'vmaf-check.ps1')+' '+ ' '.join(map(quote, arguments))+"\nexit $LASTEXITCODE\n")
                command = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(wrapper)]
            else:
                # A small PATH exposes only dirname and the deliberately selected prerequisite.
                os.symlink(shutil.which('dirname'), folder/'dirname')
                if available:
                    fake = folder/available
                    fake.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$VMAF_TEST_MARKER"\nexit 0\n')
                    fake.chmod(0o755)
                env['PATH'] = str(folder)
                command = ['/bin/sh', str(ROOT/'vmaf-check.sh'), *arguments]
            result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=20)
            return result, marker.read_text() if marker.exists() else ''

    def test_missing_prerequisites_stop_without_bootstrap(self):
        result, called = self.launch('')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('uv wird nicht automatisch installiert', result.stdout+result.stderr)
        self.assertEqual(called, '')

    def test_existing_uv_is_used_with_arguments(self):
        result, called = self.launch('uv', ['--help'])
        self.assertEqual(result.returncode, 0, result.stderr)
        for argument in ('run', '--no-project', '--python', '3.12', '--help'):
            self.assertIn(argument, called)

    def test_no_download_does_not_start_uv(self):
        result, called = self.launch('uv', ['--no-download'])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(called, '')

    def test_existing_python_needs_no_uv(self):
        result, called = self.launch('python' if os.name == 'nt' else 'python3', ['--help'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('vmaf_launcher.py', called)
        self.assertIn('--help', called)


if __name__ == '__main__':
    unittest.main()
