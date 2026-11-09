import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import vmaf_dv as dv


class RendererTests(unittest.TestCase):
    info={'width':3840,'height':2160,'pix_fmt':'yuv420p10le','codec_name':'hevc'}

    def test_scope_falls_back_without_lossy_format_conversion(self):
        for info,path,policy in [(dict(self.info,pix_fmt='yuv444p12le'),'a.mkv','optimized'),
                                 (self.info,'a.mp4','optimized'),(self.info,'a.mkv','classic'),
                                 (dict(self.info,codec_name='h264'),'a.mkv','optimized')]:
            with patch.object(dv,'verified_bundle',side_effect=AssertionError('Must not load')):
                self.assertIsNone(dv.decoder(path,info,(3840,1608,0,276),policy))

    def test_child_environment_isolated_and_diagnostics_disabled(self):
        with patch.object(dv.platform,'machine',return_value='x86_64'),patch.object(dv,'verified_bundle',return_value=(Path('/bundle'),{'executable':'renderer','sha256':{}})),patch.dict(os.environ,{'XELAVIE_NEUTRAL_TARGET':'1','XELAVIE_SKIP_TONE_BODY':'1','VK_INSTANCE_LAYERS':'unrelated'}):
            before=dict(os.environ)
            _,filters,env,audit=dv.decoder('a.mkv',self.info,(3840,1608,0,276))
            self.assertEqual(dict(os.environ),before)
            self.assertNotIn('XELAVIE_NEUTRAL_TARGET',env)
            self.assertNotIn('XELAVIE_SKIP_TONE_BODY',env)
            self.assertEqual(env['XELAVIE_GUARDED_MAP'],'0.15')
            self.assertEqual(env['XELAVIE_ROI'],'3840:2160:0:276:3840:1608:32')
            self.assertIn('format=p010le,libplacebo=',filters)
            self.assertNotIn('format=yuv420p16le',filters)
            self.assertFalse(audit['bit_identical_to_classic'])

    def test_corrupt_bundle_is_not_silently_used(self):
        with tempfile.TemporaryDirectory() as d,patch.object(dv,'bundle_path',return_value=Path(d)):
            (Path(d)/'manifest.json').write_text(json.dumps({'sha256':{'renderer':'0'*64}}))
            (Path(d)/'renderer').write_bytes(b'broken')
            with self.assertRaises(RuntimeError):dv.verified_bundle()

    def test_packaged_bundle_hashes_and_relative_layer(self):
        folder,manifest=dv.verified_bundle()
        self.assertTrue((folder/manifest['executable']).is_file())
        layer=json.loads((folder/'roi.json').read_text())['layer']['library_path']
        self.assertTrue(layer.startswith('./'))
        self.assertTrue((folder/layer).is_file())
