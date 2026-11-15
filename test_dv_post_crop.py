import os
from pathlib import Path
import unittest
from unittest.mock import patch
import vmaf_dv as dv

class PostDvCropTests(unittest.TestCase):
    def decoder(self,w,h,crop):
        info={'width':w,'height':h,'pix_fmt':'yuv420p10le','codec_name':'hevc'}
        with patch.object(dv.platform,'machine',return_value='x86_64'),patch.object(dv,'verified_bundle',return_value=(Path('/bundle'),{'executable':'renderer','sha256':{}})),patch.dict(os.environ,{'XELAVIE_NEAREST_TAPS':'up'}):
            return dv.decoder('a.mkv',info,crop)

    def test_full_frame_does_not_crop_or_change_coordinates(self):
        _,filters,env,audit=self.decoder(3840,2160,(3840,2160,0,0))
        self.assertTrue(filters.startswith('format=p010le,'))
        self.assertEqual(audit['output_crop'],(3840,2160,0,0))
        self.assertEqual(env['XELAVIE_NEAREST_TAPS'],'down')

    def test_encode_with_small_borders_keeps_all_filter_context(self):
        _,filters,env,audit=self.decoder(1920,812,(1920,802,0,4))
        self.assertTrue(filters.startswith('format=p010le,'))
        self.assertEqual(audit['pre_crop'],(1920,812,0,0))
        self.assertEqual(audit['output_crop'],(1920,802,0,4))
        self.assertEqual(env['XELAVIE_ROI'],'1920:812:0:4:1920:802:32')

    def test_interior_crop_preserves_coordinates_and_aligned_halo(self):
        _,filters,env,audit=self.decoder(1920,1080,(1280,720,100,100))
        self.assertEqual(audit['pre_crop'],(1408,848,36,36))
        self.assertEqual(audit['output_crop'],(1280,720,64,64))
        self.assertTrue(filters.startswith('crop=1408:848:36:36,format=p010le,'))
        self.assertEqual(env['XELAVIE_ROI'],'1408:848:64:64:1280:720:32')

    def test_crop_near_boundary_is_clamped_with_original_location(self):
        _,filters,env,audit=self.decoder(1920,1080,(1900,1060,10,10))
        self.assertTrue(filters.startswith('format=p010le,'))
        self.assertEqual(audit['output_crop'],(1900,1060,10,10))

    def test_invalid_crop_is_rejected(self):
        with self.assertRaises(ValueError):self.decoder(1920,1080,(1920,1080,2,0))

if __name__=='__main__':unittest.main()
