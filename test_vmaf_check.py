"""Offline regression tests; no real decoder or VMAF scores are simulated as validation of the metric."""
import contextlib
import argparse
from fractions import Fraction
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import vmaf_check as v


def stream(hdr=False):
    return dict(width=1920, height=1080, sample_aspect_ratio='1:1',
                avg_frame_rate='24000/1001', r_frame_rate='24000/1001',
                color_transfer='smpte2084' if hdr else 'bt709',
                color_primaries='bt2020' if hdr else 'bt709',
                color_space='bt2020nc' if hdr else 'bt709', color_range='tv')


class Tests(unittest.TestCase):
    def test_frame_metadata_avoids_scan(self):
        for data in ({'nb_frames':'240'}, {'tags':{'NUMBER_OF_FRAMES':'240'}},
                     {'tags':{'NUMBER_OF_FRAMES-eng':'240'}},
                     {'nb_frames':'240','tags':{'NUMBER_OF_FRAMES':'240'}}):
            with patch.object(v,'count_frames') as scan:
                count, report = v.automatic_frame_count('probe',Path('movie.mkv'),data)
            scan.assert_not_called()
            self.assertEqual(count,240)
            self.assertEqual(report['method'],'metadata')

    def test_frame_metadata_fallback(self):
        for data in ({}, {'duration':'10','avg_frame_rate':'24/1'},
                     {'nb_frames':'N/A'}, {'nb_frames':'0'}, {'nb_frames':'-1'},
                     {'nb_frames':'2.5'}, {'nb_frames':'240','tags':{'NUMBER_OF_FRAMES':'241'}}):
            with patch.object(v,'count_frames',return_value=240) as scan:
                count, report = v.automatic_frame_count('probe',Path('movie.mkv'),data)
            scan.assert_called_once()
            self.assertEqual(count,240)
            self.assertEqual(report['method'],'scan')

    def test_frame_scan_rejects_empty_video(self):
        with patch.object(v,'count_frames',return_value=0),self.assertRaises(RuntimeError):
            v.automatic_frame_count('probe',Path('movie.mkv'),{})

    def crop_result(self,text):
        return type('Result',(),{'returncode':0,'stderr':text})()

    def test_auto_crop_skips_dark_first_sample(self):
        s=stream();s['duration']='100'
        results=[self.crop_result('crop=-2:-2:1920:1080')]+[self.crop_result('crop=1920:800:0:140')]*6
        with patch.object(v.subprocess,'run',side_effect=results),contextlib.redirect_stdout(io.StringIO()):
            crop,report=v.detect_crop('ffmpeg','ffprobe',Path('ref'),s)
        self.assertEqual(crop,(1920,800,0,140));self.assertEqual(len(report['skipped']),1)

    def test_auto_crop_retries_sparse_samples(self):
        s=stream();s['duration']='100'
        results=[self.crop_result('')]*6+[self.crop_result('crop=1920:800:0:140')]*3
        with patch.object(v.subprocess,'run',side_effect=results) as call,contextlib.redirect_stdout(io.StringIO()):
            crop,report=v.detect_crop('ffmpeg','ffprobe',Path('ref'),s)
        self.assertEqual(call.call_count,9);self.assertEqual(crop,(1920,800,0,140))

    def test_auto_crop_fully_black_never_guesses(self):
        s=stream();s['duration']='100'
        with patch.object(v.subprocess,'run',return_value=self.crop_result('')) as call,contextlib.redirect_stdout(io.StringIO()):
            crop,report=v.detect_crop('ffmpeg','ffprobe',Path('ref'),s)
        self.assertIsNone(crop);self.assertEqual(call.call_count,13);self.assertEqual(len(report['skipped']),13)

    def test_auto_crop_keeps_visible_full_frame_sample(self):
        s=stream();s['duration']='100'
        results=[self.crop_result('crop=1920:1080:0:0')]+[self.crop_result('crop=1920:800:0:140')]*6
        with patch.object(v.subprocess,'run',side_effect=results),contextlib.redirect_stdout(io.StringIO()):
            crop,_=v.detect_crop('ffmpeg','ffprobe',Path('ref'),s)
        self.assertEqual(crop,(1920,1080,0,0))

    def test_color_preset_individual_precedence(self):
        args=argparse.Namespace(ref_color='hdr10',ref_primaries=None,ref_transfer=None,
                                ref_matrix=None,ref_range='full')
        values=v.color_overrides(args,'ref')
        self.assertEqual(values['color_transfer'],'smpte2084')
        self.assertEqual(values['color_range'],'pc')

    def test_partial_override_does_not_guess_other_fields(self):
        source=stream()
        del source['color_transfer']
        effective=v.apply_colors(source,{'color_range':'tv'})
        with self.assertRaises(RuntimeError): v.classify(effective)

    def test_overrides_leave_source_unchanged_and_audited(self):
        source=stream()
        source['color_transfer']='unknown'
        values={'color_transfer':'bt709','color_range':'pc'}
        effective=v.apply_colors(source,values)
        self.assertEqual(source['color_transfer'],'unknown')
        audit=v.color_audit(source,effective,values)
        self.assertEqual(audit['detected']['color_transfer'],'unknown')
        self.assertEqual(audit['effective']['color_transfer'],'bt709')
        self.assertIn('color_range',audit['overridden_existing_fields'])
        self.assertTrue(audit['sdr_full_to_limited'])

    def test_filters_use_independent_colors_before_normalization(self):
        ref=v.apply_colors(stream(True),v.COLOR_PRESETS['hlg'])
        enc=v.apply_colors(stream(True),v.COLOR_PRESETS['hdr10'])
        g=v.graph(Fraction(24),1,2,True,crop=v.geometry(ref,enc,None))
        enc_part,ref_part=g.split('[1:V:0]')
        self.assertIn('color_trc=smpte2084',enc_part)
        self.assertNotIn('arib-std-b67',enc_part)
        self.assertIn('color_trc=arib-std-b67',ref_part)
        self.assertLess(ref_part.index('setparams='),ref_part.index('zscale='))

    def test_full_range_sdr_is_normalized(self):
        ref=v.apply_colors(stream(),{'color_range':'pc'})
        self.assertEqual(v.classify(ref),'sdr')
        self.assertIn('scale=in_range=full:out_range=limited',v.color_filter(ref))
        self.assertNotIn('scale=',v.color_filter(stream()))

    def dv_stream(self,profile,compat=1):
        s=stream(True)
        s['codec_name']='av1' if profile==10 else 'hevc'
        s['side_data_list']=[{'side_data_type':'DOVI configuration record','dv_profile':profile,
                             'dv_bl_signal_compatibility_id':compat,'rpu_present_flag':1,
                             'el_present_flag':int(profile==7)}]
        return s

    def test_profile10_av1(self):
        s=self.dv_stream(10)
        self.assertEqual(v.classify(s),'dv')
        s['codec_name']='hevc'
        with self.assertRaises(RuntimeError): v.classify(s)

    def test_all_modern_profile_pairs(self):
        for a in (5,7,8,10):
            for b in (5,7,8,10):
                with self.subTest(reference=a,encoded=b):
                    streams=[self.dv_stream(a),self.dv_stream(b)]
                    self.assertEqual(v.validate_pair(*streams)[0],'hdr')
                    plan=v.dv_plan(streams)
                    self.assertEqual(plan['mode'],'compatible' if 7 in (a,b) else 'rendered')
                    self.assertEqual(plan['profile7_conversion'],7 in (a,b))

    def test_no_silent_full_p7(self):
        with self.assertRaises(RuntimeError): v.dv_plan([self.dv_stream(7),self.dv_stream(8)],'rendered')
        with self.assertRaises(RuntimeError): v.normalization('dv7')

    def test_baselayer_compatibility_matrix(self):
        for a in (7,8,10):
            for b in (7,8,10):
                self.assertEqual(v.dv_plan([self.dv_stream(a),self.dv_stream(b)],'base-layer')['mode'],'base-layer')
        for bad in (self.dv_stream(5,0),self.dv_stream(8,4),self.dv_stream(10,4)):
            with self.assertRaises(RuntimeError): v.dv_plan([self.dv_stream(7),bad],'base-layer')

    def test_baselayer_filters_and_validation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            s=self.dv_stream(7)
            clean=stream(True)
            clean['codec_name']='hevc'
            with patch.object(v,'logged') as call, patch.object(v,'probe',return_value=clean):
                result,_,detail=v.prepare_dv('ffmpeg','ffprobe',root/'input.mkv',s,'base-layer',None,root,root,'ref',Fraction(24))
            cmd=call.call_args[0][0]
            self.assertIn('hevc_mp4toannexb,filter_units=remove_types=62|63,dovi_rpu=strip=1',cmd)
            self.assertIn('copy',cmd)
            self.assertFalse(detail['reencoded'])
            with patch.object(v,'logged'), patch.object(v,'probe',return_value=s):
                with self.assertRaises(RuntimeError):
                    v.prepare_dv('ffmpeg','ffprobe',root/'input.mkv',s,'base-layer',None,root,root,'ref',Fraction(24))

    def test_p7_sample_is_not_full_film_certificate(self):
        data={'frames':[{'side_data_list':[{'disable_residual_flag':0}]}]}
        with patch.object(v,'run',return_value=json.dumps(data)):
            result=v.profile7_sample('ffprobe','input')
        self.assertEqual(result['disable_residual_flags'],[0])
        self.assertEqual(result['full_film_mel_fel_classification'],'not_determined')

    def test_sdr_hdr_classification(self):
        self.assertEqual(v.classify(stream()), 'sdr')
        self.assertEqual(v.classify(stream(True)), 'hdr')

    def test_unsupported_hdr(self):
        s = stream(True)
        s['color_transfer'] = 'arib-std-b67'
        self.assertEqual(v.classify(s),'hlg')
        s = stream(True)
        s['side_data_list'] = [{'side_data_type': 'DOVI configuration record'}]
        with self.assertRaises(RuntimeError): v.classify(s)

    def test_missing_color(self):
        s = stream()
        del s['color_transfer']
        with self.assertRaises(RuntimeError): v.classify(s)

    def test_mismatched_geometry(self):
        s = stream()
        s['width'] = 1280
        with self.assertRaises(RuntimeError): v.geometry(stream(), s, None)

    def test_2160_to_1080(self):
        r,e = stream(),stream()
        r.update(width=3840,height=2160)
        self.assertEqual(v.validate_pair(r,e)[0],'sdr')
        g = v.geometry(r,e,(3840,1600,0,280))
        self.assertEqual(g['enc'],(1920,800,0,140))
        self.assertEqual(g['target'],(1920,800))
        filters = v.graph(Fraction(24),2,2,False,crop=g)
        self.assertIn('crop=3840:1600:0:280',filters)
        self.assertIn('crop=1920:800:0:140',filters)
        self.assertEqual(filters.count('scale=1920:800'),2)

    def test_already_cropped_encode(self):
        r,e = stream(),stream()
        r.update(width=3840,height=2160)
        e.update(width=1920,height=800)
        g = v.geometry(r,e,(3840,1600,0,280))
        self.assertEqual(g['enc'],(1920,800,0,0))

    def test_dv_profile_guard(self):
        s = stream(True)
        s['side_data_list']=[{'side_data_type':'DOVI configuration record','dv_profile':5,'rpu_present_flag':1,'el_present_flag':0}]
        self.assertEqual(v.classify(s),'dv')
        s['side_data_list'][0]['dv_profile']=7
        with self.assertRaises(RuntimeError): v.classify(s)

    def test_hdr_normalization(self):
        self.assertIn('npl=1000',v.normalization('hlg'))
        self.assertIn('apply_dolbyvision=1',v.normalization('dv'))
        self.assertEqual(v.normalization('hdr'),'')

    def test_mixed_hdr_sdr(self):
        with self.assertRaises(RuntimeError): v.validate_pair(stream(), stream(True))

    def test_vfr(self):
        s = stream()
        s['r_frame_rate'] = '30/1'
        with self.assertRaises(RuntimeError): v.validate_pair(stream(), s)

    def test_crop_union_conservative(self):
        self.assertEqual(v.union_crop([(1920,800,0,140), (1920,1080,0,0)],1920,1080), (1920,1080,0,0))
        self.assertEqual(v.union_crop([(1917,801,1,139)],1920,1080), (1918,802,0,138))

    def test_manual_crop(self):
        self.assertEqual(v.parse_crop('1920:800:0:140',1920,1080), (1920,800,0,140))
        for value in ('1920:800:0:141', '3000:800:0:0', '-2:80:0:0', 'wrong'):
            with self.assertRaises(RuntimeError): v.parse_crop(value,1920,1080)

    def test_graph_temporal_sampling(self):
        for step in (1,2,4):
            g = v.graph(Fraction(24000,1001), step, 2, False, crop=(1920,800,0,140))
            self.assertEqual(g.count('crop=1920:800:0:140'), 2)
            self.assertIn('n_subsample='+str(step),g)
            self.assertNotIn('select=',g)
            self.assertIn('shortest=1:repeatlast=0',g)

    def test_archive_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            with zipfile.ZipFile(p/'bad.zip','w') as z: z.writestr('../outside', 'bad')
            with self.assertRaises(RuntimeError): v.unpack(p/'bad.zip',p/'unpack')
            self.assertFalse((p/'outside').exists())

    def test_archive_normal(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            with zipfile.ZipFile(p/'good.zip','w') as z: z.writestr('bin/test', 'ok')
            v.unpack(p/'good.zip',p/'unpack')
            self.assertEqual((p/'unpack/bin/test').read_text(),'ok')

    def test_auto_crop_samples(self):
        s = stream()
        s['duration'] = '100'
        fake = type('Result',(),{'returncode':0,'stderr':'crop=1920:800:0:140\n'})()
        with patch.object(v.subprocess,'run',return_value=fake) as call:
            crop, report = v.detect_crop('ffmpeg','ffprobe',Path('ref'),s)
        self.assertEqual(crop,(1920,800,0,140))
        self.assertEqual(call.call_count,7)
        self.assertEqual(len(report['samples']),7)
        self.assertGreater(report['black_limit'],16/255)
        self.assertIn('cropdetect=limit=0.094117647',call.call_args.args[0][call.call_args.args[0].index('-vf')+1])

    def test_hdr_negative_probe_rejects_silent_success(self):
        fake = type('Result',(),{'returncode':0,'stderr':b''})()
        with tempfile.TemporaryDirectory() as d:
            def pretend_success(*args,**kwargs):
                (Path(d)/'hdr-probe-pq.json').write_text(json.dumps({'frames':[{},{}]}))
                return fake
            with patch.object(v.vmaf_hdr,'worker_path',return_value='worker'),patch.object(v.subprocess,'run',side_effect=pretend_success):
                with self.assertRaisesRegex(RuntimeError,'Negativtest'):v.check_hdr_conversion('ffmpeg',d,2)

    def test_simulated_full_pipeline_all_percentages(self):
        for percent, expected in ((100,9),(50,5),(25,3)):
            with self.subTest(percent=percent), tempfile.TemporaryDirectory() as d:
                p = Path(d)
                for name in ('original.mkv','encode.mkv'): (p/name).write_bytes(b'fixture')
                (p/'model.json').write_text('{}')
                def fake_evaluate(ffmpeg,ref,enc,fps,step,threads,hdr,root,log,limit=None,crop=None,display='1080',frame_count=None,optimize=True):
                    if limit is None:self.assertEqual(frame_count,9)
                    data = {'frames':[{'frameNum':i,'metrics':{'vmaf':90.0}} for i in range(0,limit or 9,step)]}
                    (root/'scores.json').write_text(json.dumps(data))
                    Path(log).write_text('simulated')
                    return ['simulated']
                args = ['vmaf_check',str(p/'original.mkv'),str(p/'encode.mkv'),'--percent',str(percent),
                        '--crop','none','--no-download','--model',str(p/'model.json'),'--output',str(p/'out'),'--temp-dir',str(p/'temp')]
                with patch.object(sys,'argv',args), patch.object(v.shutil,'which',return_value='fake'), \
                        patch.object(v,'probe',return_value=stream()), patch.object(v,'count_frames',return_value=9), \
                        patch.object(v,'evaluate',side_effect=fake_evaluate), patch.object(v,'run',return_value='fake-version'), patch.object(v,'required_filters'), \
                        contextlib.redirect_stdout(io.StringIO()), patch.object(v.time,'monotonic',side_effect=[100,120,123,125]):
                    self.assertEqual(v.main(),0)
                reports = list((p/'out').glob('*/summary.json'))
                self.assertEqual(len(reports),1)
                report = json.loads(reports[0].read_text())
                self.assertEqual(report['scored_frames'],expected)
                self.assertEqual(report['mean'],90)
                self.assertEqual(report['timing'],{'preparation_seconds':20,'measurement_seconds':3,
                    'finalization_seconds':2,'job_seconds':25,'measurement_fps':3})


if __name__ == '__main__':
    unittest.main()
