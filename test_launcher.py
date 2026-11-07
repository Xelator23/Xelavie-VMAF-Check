import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import vmaf_launcher as l


class LauncherTests(unittest.TestCase):
    def test_progress_estimate_and_frozen_elapsed(self):
        job=l.Job();job.started=10;job.measure_started=20;job.phase='Laeuft'
        job.frame=40;job.total=100
        with patch.object(l.time,'monotonic',return_value=30):
            state=job.snapshot()
        self.assertEqual(state['percent'],40)
        self.assertEqual(state['elapsed'],20)
        self.assertEqual(state['remaining'],15)
        job.frame=100
        self.assertLess(job.snapshot()['percent'],100)
        job.phase='Fehler';job.finished=35
        self.assertEqual(job.snapshot()['elapsed'],25)
        self.assertIsNone(job.snapshot()['remaining'])
        job.phase='Fertig'
        self.assertEqual(job.snapshot()['percent'],100)
        self.assertEqual(job.snapshot()['remaining'],0)

    def test_progress_protocol_does_not_flood_log(self):
        job=l.Job();job.phase='Laeuft';job.started=1
        process=type('Process',(),{'stdout':io.StringIO(
            'Vorbereitung\nVMAF_PROGRESS {"total":100,"frame":0}\n'
            'VMAF_PROGRESS {"frame":42}\nVMAF_PROGRESS broken\n'),
            'wait':lambda self:1})()
        job.collect(process)
        state=job.snapshot()
        self.assertEqual(state['logs'],['Vorbereitung'])
        self.assertEqual(state['percent'],42)
        self.assertEqual(state['phase'],'Fehler')
        self.assertEqual(state['step'],'VMAF-Messung')

    def test_command_keeps_paths_and_color_arguments_separate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'file with spaces & symbols.mkv';p.write_bytes(b'fixture')
            cmd=l.build_command({'reference':str(p),'encoded':str(p),'percent':'25',
                                 'enc-color':'hdr10','enc-range':'full','download-tools':True})
            self.assertEqual(cmd[3:5],[str(p.resolve()),str(p.resolve())])
            self.assertEqual(cmd[cmd.index('--enc-color')+1],'hdr10')
            self.assertIn('--download-tools',cmd)

    def test_bad_fields_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'video';p.touch();base={'reference':str(p),'encoded':str(p)}
            for extra in ({'percent':'3'},{'threads':'0'},{'crop':'x;evil'},{'shell':'cmd'},
                          {'no-download':True,'download-tools':True}):
                with self.assertRaises(ValueError):l.build_command({**base,**extra})

    def test_browse_directory(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'folder').mkdir();(p/'clip.mkv').touch();(p/'.hidden').touch()
            result=l.browse(d)
            self.assertEqual(result['directories'][0]['name'],'folder')
            self.assertEqual([x['name'] for x in result['files']],['clip.mkv'])

    def test_no_arguments_show_help_without_prompt_or_browser(self):
        with patch.object(sys,'argv',['launcher']),patch('builtins.input',side_effect=AssertionError('No prompts')),patch.object(l,'ui') as ui,patch.object(l.subprocess,'call',return_value=0) as run,contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(l.main(),0)
            self.assertEqual(run.call_args.args[0][3:],['--help'])
            self.assertIn('--gui',out.getvalue())
            ui.assert_not_called()

    def test_gui_flag_opens_browser_mode(self):
        with patch.object(sys,'argv',['launcher','--gui']),patch.object(l,'ui',return_value=0) as ui,patch.object(l.subprocess,'call') as run:
            self.assertEqual(l.main(),0);ui.assert_called_once();run.assert_not_called()

    def test_gui_combination_and_old_flags_are_rejected(self):
        for args in (['--gui','a.mkv','b.mkv'],['--gui','--percent','25'],['--ui'],['--cli']):
            with self.subTest(args=args),patch.object(sys,'argv',['launcher',*args]),patch.object(l,'ui') as ui,patch.object(l.subprocess,'call') as run:
                with self.assertRaises(ValueError):l.main()
                ui.assert_not_called();run.assert_not_called()

    def test_help_shows_gui_flag_and_engine_options(self):
        for flag in ('--help','-h'):
            with patch.object(sys,'argv',['launcher',flag]),patch.object(l.subprocess,'call',return_value=0) as run,contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(l.main(),0)
                self.assertIn('--gui',out.getvalue())
                self.assertEqual(run.call_args.args[0][3:],['--help'])

    def test_direct_args_reach_engine(self):
        args=['a.mkv','b.mkv','--percent','50']
        with patch.object(sys,'argv',['launcher',*args]),patch.object(l.subprocess,'call',return_value=0) as run:
            l.main();self.assertEqual(run.call_args.args[0][3:],args)

    def test_real_process_capture_and_repeat(self):
        job=l.Job()
        for _ in range(2):
            with patch.object(l,'build_command',return_value=[sys.executable,'-u','-c',"print('Ergebnisse: example-output')"]):job.start({})
            deadline=time.time()+10
            while job.snapshot()['running'] and time.time()<deadline:time.sleep(.02)
            state=job.snapshot();self.assertEqual(state['phase'],'Fertig');self.assertEqual(state['result'],'example-output')

    def test_real_process_cancel(self):
        job=l.Job()
        code="import signal,time; signal.signal(getattr(signal,'SIGBREAK',signal.SIGINT),signal.default_int_handler); print('ready',flush=True); time.sleep(30)"
        with patch.object(l,'build_command',return_value=[sys.executable,'-u','-c',code]):job.start({})
        deadline=time.time()+10
        while 'ready' not in job.snapshot()['logs'] and time.time()<deadline:time.sleep(.02)
        job.cancel()
        deadline=time.time()+5
        while job.snapshot()['running'] and time.time()<deadline:time.sleep(.02)
        self.assertEqual(job.snapshot()['phase'],'Abgebrochen')
        self.assertIsNotNone(job.process.poll())

    def test_http_auth_and_invalid_post(self):
        server=l.Server();thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            base=server.origin+server.prefix
            opener=lambda req:urlopen(req,timeout=5)
            with opener(base+'status') as response:self.assertEqual(json.load(response)['phase'],'Bereit')
            with opener(base) as response:self.assertIn('Prüfung starten',response.read().decode())
            for req in [server.origin+'/status',Request(base+'status',headers={'Origin':'https://example.invalid'}),
                        Request(base+'start',data=b'{}',headers={'Content-Type':'text/plain'})]:
                with self.assertRaises(HTTPError):opener(req)
            with self.assertRaises(HTTPError):opener(Request(base+'start',data=b'{}',headers={'Content-Type':'application/json'}))
        finally:server.shutdown();server.server_close();thread.join(timeout=3)


if __name__=='__main__':unittest.main()
