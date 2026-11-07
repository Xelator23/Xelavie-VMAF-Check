import json
import tempfile
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
from vmaf_library import Queue, statistics


class FakeJob:
    def __init__(self):
        self.lock=threading.Lock();self.result=None;self.report=None
        self.state={'running':False,'phase':'Bereit','logs':[],'result':None}
        self.started=[];self.reject=False
    def snapshot(self): return dict(self.state)
    def start(self,data):
        if self.reject: raise OSError('missing file')
        self.started.append(data);self.state.update(running=True,phase='Laeuft')
    def end(self,phase): self.state.update(running=False,phase=phase)


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.job=FakeJob();self.queue=Queue(self.job,lambda data:None,self.root/'queue.json',autostart=False)
        self.data={'reference':str(self.root/'ref.mkv'),'encoded':str(self.root/'enc.mkv'),'work-dir':str(self.root)}
    def tearDown(self): self.queue.close();self.tmp.cleanup()
    def test_sequential_success_and_failure_continue(self):
        self.queue.add(self.data,True);second=self.queue.add({**self.data,'percent':'25'})
        self.queue.tick();self.queue.tick();self.assertEqual(len(self.job.started),1)
        self.job.end('Fehler');self.queue.tick()
        self.assertEqual(self.queue.active,second);self.assertFalse(self.queue.paused)
        self.assertEqual(self.queue.items[0]['state'],'failed')
        self.job.end('Fertig');self.queue.tick();self.assertEqual(len(self.queue.items),1)
        self.assertEqual(self.queue.items[0]['state'],'failed')
        self.assertEqual(len(json.loads(self.queue.path.read_text())['items']),1)
    def test_success_cleanup_preserves_reports_and_migrates_old_queue(self):
        folder=self.make_report()
        self.queue.add(self.data,True);self.queue.tick();self.job.end('Fertig');self.queue.tick()
        self.assertEqual(self.queue.items,[]);self.assertTrue((folder/'summary.json').exists())
        data=json.loads(self.queue.path.read_text());data['items']=[{'id':'old','state':'done','data':self.data}]
        self.queue.path.write_text(json.dumps(data))
        recovered=Queue(FakeJob(),lambda x:None,self.queue.path,autostart=False)
        self.assertEqual(recovered.items,[]);self.assertEqual(json.loads(self.queue.path.read_text())['items'],[])
        self.assertTrue((folder/'summary.json').exists());recovered.close()
    def test_start_failure_does_not_block_next(self):
        self.queue.add(self.data,True);self.queue.add(self.data)
        self.job.reject=True;self.queue.tick();self.assertFalse(self.queue.paused)
        self.job.reject=False;self.queue.tick();self.assertEqual(len(self.job.started),1)
    def test_reorder_pending_only_and_persist(self):
        active=self.queue.add(self.data,True)
        first=self.queue.add({**self.data,'percent':'25'})
        second=self.queue.add({**self.data,'percent':'50'})
        self.queue.tick();self.queue.action('up',second)
        self.assertEqual([x['id'] for x in self.queue.items],[active,second,first])
        with self.assertRaises(ValueError):self.queue.action('down',active)
        saved=json.loads(self.queue.path.read_text())
        self.assertEqual([x['id'] for x in saved['items']],[active,second,first])
        self.job.end('Fertig');self.queue.tick()
        self.assertEqual(self.queue.active,second)
    def test_pause_and_restart_recovery(self):
        self.queue.add(self.data,True);self.queue.add(self.data);self.queue.tick()
        recovered=Queue(FakeJob(),lambda x:None,self.root/'queue.json',autostart=False)
        self.assertTrue(recovered.paused);self.assertEqual(recovered.items[0]['state'],'interrupted');recovered.close()
        self.queue.action('pause');self.job.end('Fertig');self.queue.tick()
        self.assertEqual(len(self.job.started),1)
        self.queue.action('resume');self.queue.tick();self.assertEqual(len(self.job.started),2)
    def test_cancel_stops_next_and_pending_remove(self):
        self.queue.add(self.data,True);second=self.queue.add(self.data);self.queue.tick()
        with self.assertRaises(ValueError): self.queue.action('remove',self.queue.active)
        self.job.end('Abgebrochen');self.queue.tick();self.assertTrue(self.queue.paused)
        self.queue.action('remove',second);self.assertEqual(len(self.queue.items),1)
    def make_report(self):
        folder=self.root/'Ergebnisse'/'film'/'run';folder.mkdir(parents=True)
        report={'reference':self.data['reference'],'encoded':self.data['encoded'],'mean':97.,'total_frames':10,
            'scored_frames':10,'percent':100,'type':'sdr','timing':{'job_seconds':15,'measurement_seconds':10}}
        (folder/'summary.json').write_text(json.dumps(report));(folder/'frames.csv').write_text('frames')
        self.queue.roots=[str(self.root/'Ergebnisse')]
        return folder
    def test_delete_only_known_report_files(self):
        folder=self.make_report();(folder/'keep.mkv').write_bytes(b'keep')
        with patch('vmaf_library.work_directory',return_value=self.root):
            entries=self.queue.library();self.assertEqual(len(entries),1)
            self.queue.delete_report(entries[0]['id'])
            self.assertFalse((folder/'summary.json').exists());self.assertTrue((folder/'keep.mkv').exists())
            self.assertEqual(self.queue.library(),[])
            with self.assertRaises(ValueError):self.queue.delete_report('../outside')
    def test_protect_source_even_if_named_like_report(self):
        folder=self.make_report();report=json.loads((folder/'summary.json').read_text())
        report['encoded']=str(folder/'frames.csv');(folder/'summary.json').write_text(json.dumps(report))
        with patch('vmaf_library.work_directory',return_value=self.root):
            with self.assertRaises(ValueError):self.queue.delete_report(self.queue.library()[0]['id'])
        self.assertTrue((folder/'frames.csv').exists())
    def test_statistics_separate_models_and_sampling(self):
        base={'encoded':'a.mkv','mean':90.,'type':'sdr','model_sha256':'a','percent':25,'timing':{'job_seconds':10}}
        reports=[{'report':base},{'report':{**base,'mean':100.}}, {'report':{**base,'encoded':'b.mkv','percent':100}}]
        stats=statistics(reports);self.assertEqual(stats['files'],2);self.assertEqual(stats['jobs'],3)
        self.assertEqual(stats['times']['job_seconds'],30);self.assertEqual(len(stats['groups']),2)
        self.assertEqual(stats['groups'][0]['mean'],95)

if __name__=='__main__':unittest.main()
