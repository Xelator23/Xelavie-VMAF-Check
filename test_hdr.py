import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import vmaf_hdr as hdr
import vmaf_check as v


class HDRTests(unittest.TestCase):
    def test_compact_transport_rejects_unknown_or_missing_model(self):
        with tempfile.TemporaryDirectory() as d:
            model=Path(d)/'custom.json'
            self.assertFalse(hdr.compact_model_supported(model))
            model.write_text('{"model_dict": {"conversion_target": {}}}')
            self.assertFalse(hdr.compact_model_supported(model))

    def test_sparse_worker_capability_and_legacy_fallback(self):
        for code,text,expected in ((0,'protocol=2 sparse25=1',True),
                                   (0,'protocol=1',False),(1,'sparse25=1',False),
                                   (0,'not-sparse25=1',False)):
            with patch.object(hdr.subprocess,'run',return_value=subprocess.CompletedProcess([],code,text,'')):
                self.assertEqual(hdr.sparse_worker_supported(['worker']),expected)
        for error in (OSError('missing'),subprocess.TimeoutExpired('worker',10)):
            with patch.object(hdr.subprocess,'run',side_effect=error):
                self.assertFalse(hdr.sparse_worker_supported(['worker']))

    def test_sparse_pairs_preserve_scored_neighbours_and_tails(self):
        for count in range(1,25):
            reference=[bytes([i]) for i in range(count)]
            encoded=[bytes([100+i]) for i in range(count)]
            ref=io.BytesIO(b''.join(v for i,v in enumerate(reference) if i%4!=2))
            enc=io.BytesIO(b''.join(v for i,v in enumerate(encoded) if i%4==0))
            pairs=list(hdr.frame_pairs(ref,enc,1,{'total_frames':count}))
            self.assertEqual(len(pairs),count)
            for index in range(0,count,4):
                self.assertEqual(pairs[index],(reference[index],encoded[index]))
                for neighbour in (index-1,index+1):
                    if 0<=neighbour<count:self.assertEqual(pairs[neighbour][0],reference[neighbour])

    def test_sparse_pairs_reject_missing_and_extra_samples(self):
        for ref,enc in ((b'01',b'a'),(b'013',b''),(b'013x',b'a'),(b'013',b'ax')):
            with self.assertRaises(RuntimeError):
                list(hdr.frame_pairs(io.BytesIO(ref),io.BytesIO(enc),1,{'total_frames':4}))

    def test_decoder_counter_requires_successful_end(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'progress'
            path.write_text('frame=4\nprogress=continue\nframe=7\nprogress=end\n')
            self.assertEqual(hdr.decoded_count(path),7)
            path.write_text('frame=4\nprogress=continue\n')
            with self.assertRaises(RuntimeError):hdr.decoded_count(path)

    def test_sparse_plan_rejects_unknown_temporal_requirements(self):
        model={'model_dict':{'feature_names':['Cambi_feature_cambi_score',
            'Speed_chroma_feature_speed_chroma_uv_score','VMAF_integer_feature_adm3_score',
            'VMAF_integer_feature_motion3_score'],'feature_opts_dicts':[{}, {}, {}, {'motion_max_val':18.0}]}}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'model.json';path.write_text(json.dumps(model))
            plan=hdr.sparse_plan(path,4,24)
            self.assertEqual((plan['reference_rendered'],plan['encoded_rendered']),(18,6))
            self.assertIsNone(hdr.sparse_plan(path,2,24))
            model['model_dict']['feature_opts_dicts'][-1]['motion_moving_average']=True
            path.write_text(json.dumps(model));self.assertIsNone(hdr.sparse_plan(path,4,24))
            model['model_dict']['feature_names'].append('unknown_temporal_feature')
            path.write_text(json.dumps(model));self.assertIsNone(hdr.sparse_plan(path,4,24))

    def test_missing_zimg_is_failure_not_evidence(self):
        result=subprocess.CompletedProcess([],1,b'',b'libvmaf built without zimg')
        with tempfile.TemporaryDirectory() as d,patch.object(hdr,'worker_path',return_value='worker'),patch.object(hdr.subprocess,'run',return_value=result):
            with self.assertRaisesRegex(RuntimeError,'Positivtest'):hdr.check_conversion(d,2)

    def test_positive_and_negative_are_both_required(self):
        with tempfile.TemporaryDirectory() as d:
            def run(cmd,**kw):
                if cmd[-1]=='pq':
                    (Path(d)/cmd[-2]).write_text(json.dumps({'frames':[{},{}]}))
                    return subprocess.CompletedProcess(cmd,0,b'',b'')
                return subprocess.CompletedProcess(cmd,1,b'',b'unknown colour')
            with patch.object(hdr,'worker_path',return_value='worker'),patch.object(hdr.subprocess,'run',side_effect=run) as calls:
                hdr.check_conversion(d,2)
                self.assertEqual(calls.call_count,2)

    def test_partial_raw_frame_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'unvollstaendig'):hdr.read_frame(io.BytesIO(b'123'),6)
        self.assertEqual(hdr.read_frame(io.BytesIO(b''),6),b'')

    def test_dv_device_is_explicit_software(self):
        self.assertIn('vulkan=vk:llvmpipe',v.dv_device_args('dv'))
        self.assertEqual(v.dv_device_args('hdr'),[])

    def test_old_dv_renderer_is_rejected(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(v.os.environ):
            root=Path(d);icd=root/'driver.json';icd.write_text('{}')
            result=subprocess.CompletedProcess([],0,'','llvmpipe Initialized libplacebo v7.372.0')
            with patch.object(v.subprocess,'run',return_value=result):
                with self.assertRaises(v.DVBackendTooOld):v.configure_cpu_vulkan('ffmpeg',root,[],True,icd)

    def test_current_dv_renderer_is_recorded(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(v.os.environ):
            root=Path(d);icd=root/'driver.json';icd.write_text('{}')
            result=subprocess.CompletedProcess([],0,'','llvmpipe Initialized libplacebo v7.387.0')
            with patch.object(v.subprocess,'run',return_value=result):
                result=v.configure_cpu_vulkan('ffmpeg',root,[],True,icd)
                self.assertFalse(result['gpu']);self.assertEqual(result['libplacebo_version'],'7.387.0')

    def test_renderer_thread_limit_is_audited_without_overriding_it(self):
        for limit in (None,'4','0'):
            with self.subTest(limit=limit),tempfile.TemporaryDirectory() as d,patch.dict(v.os.environ):
                v.os.environ.pop('LP_NUM_THREADS',None)
                if limit is not None:v.os.environ['LP_NUM_THREADS']=limit
                root=Path(d);icd=root/'driver.json';icd.write_text('{}')
                process=subprocess.CompletedProcess([],0,'','llvmpipe Initialized libplacebo v7.387.0')
                with patch.object(v.subprocess,'run',return_value=process),patch('builtins.print') as output:
                    result=v.configure_cpu_vulkan('ffmpeg',root,[],True,icd)
                self.assertEqual(v.os.environ.get('LP_NUM_THREADS'),limit)
                self.assertEqual(result['renderer_threads'],limit if limit is not None else 'auto')
                self.assertEqual(result['renderer_threads_source'],'LP_NUM_THREADS' if limit is not None else 'Mesa default')
                self.assertIn('Mesa-Threads:',output.call_args.args[0])

    def test_open_gop_metadata_difference_uses_decoded_counts(self):
        with patch.object(v,'automatic_frame_count',return_value=(97,{'method':'decoded','count':97})),\
             patch.object(v,'count_frames',side_effect=[97,97]):
            count,original,prepared=v.prepared_frame_count('ffprobe',Path('ref'),Path('prepared'),99,{})
            self.assertEqual(count,97)
            self.assertEqual(prepared['previous_count'],99)

    def test_actual_preparation_frame_loss_is_rejected(self):
        with patch.object(v,'automatic_frame_count',return_value=(97,{})),\
             patch.object(v,'count_frames',side_effect=[97,96]):
            with self.assertRaisesRegex(RuntimeError,'97 -> 96'):
                v.prepared_frame_count('ffprobe',Path('ref'),Path('prepared'),99,{})

    def test_failed_worker_reaps_decoders(self):
        # Each decoder would block on its pipe without proper cleanup.
        # Windows venv python.exe is a launcher spawning another process; use
        # the actual interpreter to model the native FFmpeg/worker processes.
        python=getattr(sys,'_base_executable',sys.executable)
        producer=[python,'-c','import sys; sys.stdout.buffer.write(bytes(16*16*3)*10000)']
        worker=[python,'-c','import sys; sys.exit(7)']
        children=[];original=hdr.subprocess.Popen
        def track(*args,**kw):
            child=original(*args,**kw);children.append(child);return child
        with tempfile.TemporaryDirectory() as d,patch.object(hdr,'worker_command',return_value=worker),patch.object(hdr.subprocess,'Popen',side_effect=track):
            with self.assertRaises(RuntimeError):hdr.evaluate([producer,producer],16,16,2,1,Path(d),Path(d)/'test.log',False)
        self.assertEqual(len(children),3)
        self.assertTrue(all(child.poll() is not None for child in children))


if __name__=='__main__':unittest.main()
