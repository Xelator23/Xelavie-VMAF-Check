"""Real subprocess tests; use isolated state and never open the user's browser."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.request import Request, build_opener, ProxyHandler

import vmaf_background as b
import vmaf_launcher as l


class BackgroundTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'VMAF_SETTINGS_FILE': str(self.root / 'settings.json')})
        self.env.start()

    def tearDown(self):
        try:
            self.stop_service()
        finally:
            self.env.stop()
            self.temp.cleanup()

    def stop_service(self):
        state = b.live_session()
        if state:
            req = Request(state['url']+'shutdown', data=b'{}', headers={'Content-Type':'application/json'})
            with build_opener(ProxyHandler({})).open(req, timeout=5) as response:
                self.assertTrue(json.load(response)['ok'])
        deadline = time.monotonic()+20
        while b.service_paths()[0].exists() and time.monotonic()<deadline:
            time.sleep(.05)
        self.assertFalse(b.service_paths()[0].exists(), 'Service failed to shut down')

    def launcher_process(self):
        code = ('import sys; sys.path.insert(0,'+repr(str(l.HERE))+'); '
                'import vmaf_launcher as l; l.webbrowser.open=lambda url: False; '
                'sys.argv=["launcher","--gui"]; sys.exit(l.main())')
        return subprocess.Popen([sys.executable,'-B','-c',code], cwd=self.root,
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, encoding='utf-8')

    def test_concurrent_launch_reconnect_and_restart(self):
        processes=[self.launcher_process(), self.launcher_process()]
        for process in processes:
            out, err=process.communicate(timeout=35)
            self.assertEqual(process.returncode,0,err)
            self.assertIn('GUI laeuft im Hintergrund:',out)
        # Both launchers have exited; the single service is still alive.
        first=b.live_session(); self.assertIsNotNone(first)
        with patch.object(l.webbrowser,'open',return_value=True) as browser, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(l.ui(),0)
            browser.assert_called_once_with(first['url'])
        self.assertEqual(b.live_session()['pid'],first['pid'])
        self.stop_service()
        # Stale metadata must not prevent a fresh start after a crash.
        b.atomic_json(b.service_paths()[0],{'port':1,'token':'a'*43,'pid':12345})
        fresh=b.ensure_service(l.HERE/'vmaf_launcher.py')
        self.assertNotEqual(fresh['token'],first['token'])

    def test_shutdown_cancels_job_from_detached_console(self):
        marker=self.root/'cancelled.txt'
        code=('import signal,time; from pathlib import Path; '
              'signal.signal(getattr(signal,"SIGBREAK",signal.SIGINT),signal.default_int_handler); '
              'print("ready",flush=True)\n'
              'try:\n while True: time.sleep(.1)\n'
              'except KeyboardInterrupt: Path('+repr(str(marker))+').write_text("cancelled")\n')
        command=[sys.executable,'-u','-c',code]
        fixture=self.root/'worker.py'
        fixture.write_text('import sys\nsys.path.insert(0,'+repr(str(l.HERE))+')\n'
                           'import vmaf_launcher as l\nimport vmaf_background as b\n'
                           'l.build_command=lambda data: '+repr(command)+'\n'
                           'sys.exit(b.run_service(l.Server))\n',encoding='utf-8')
        state=b.ensure_service(fixture)
        opener=build_opener(ProxyHandler({}))
        req=Request(state['url']+'start',data=b'{"encoded":"dummy.mkv"}',headers={'Content-Type':'application/json'})
        with opener.open(req,timeout=5) as response:self.assertTrue(json.load(response)['ok'])
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            with opener.open(state['url']+'status',timeout=5) as response:status=json.load(response)
            if 'ready' in status['logs']:break
            time.sleep(.05)
        else:self.fail('Dummy job never started')
        self.stop_service()
        self.assertEqual(marker.read_text(),'cancelled')

    def test_exclusive_lock_and_release(self):
        path=b.service_paths()[1]
        first=b.ServiceLock(path); second=b.ServiceLock(path)
        try:
            self.assertTrue(first.acquire());self.assertFalse(second.acquire())
            first.release();self.assertTrue(second.acquire())
        finally:first.release();second.release()

    def test_failed_start_reports_log_and_releases_lock(self):
        (self.root/'queue.json').write_text('invalid json',encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Protokoll:'):
            b.ensure_service(l.HERE/'vmaf_launcher.py',timeout=10)
        self.assertIn('JSONDecodeError',b.service_paths()[2].read_text(encoding='utf-8'))
        self.assertFalse(b.service_paths()[0].exists())
        lock=b.ServiceLock(b.service_paths()[1])
        try:self.assertTrue(lock.acquire())
        finally:lock.release()

    def test_untrusted_session_is_not_used_as_url(self):
        for state in ({'url':'https://example.invalid'}, {'port':80,'pid':2,'token':'../evil'},
                      {'port':'80','pid':2,'token':'a'*43}, []):
            b.atomic_json(b.service_paths()[0],state)
            with patch.object(b,'build_opener') as opener:
                self.assertIsNone(b.live_session());opener.assert_not_called()
        b.service_paths()[0].unlink()

    def test_platform_detachment(self):
        self.assertEqual(b.detached_options('posix'),{'start_new_session':True})
        if os.name=='nt':
            options=b.detached_options()
            self.assertEqual(options['creationflags'],subprocess.CREATE_NEW_CONSOLE)
            self.assertEqual(options['startupinfo'].wShowWindow,subprocess.SW_HIDE)


if __name__=='__main__':unittest.main()
