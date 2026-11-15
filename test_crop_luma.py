import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
import vmaf_check as v


class CropOutputTests(unittest.TestCase):
    def test_unsupported_output_retries_same_window_and_keeps_original_format(self):
        calls=[]
        def run(cmd,**kwargs):
            calls.append(list(cmd))
            if len(calls)<=2:
                return subprocess.CompletedProcess(cmd,1,'','Invalid output format')
            return subprocess.CompletedProcess(cmd,0,'','crop=1920:800:0:140')
        info=dict(width=1920,height=1080,duration='100',pix_fmt='yuv420p10le')
        with patch.object(v,'classify',return_value='dv'),patch.object(v,'color_filter',return_value=''),patch.object(v.subprocess,'run',side_effect=run):
            crop,_=v.detect_crop('ffmpeg','ffprobe',Path('ref.mkv'),info)
        self.assertEqual(crop,(1920,800,0,140))
        self.assertEqual(len(calls),9)
        self.assertEqual(calls[0][calls[0].index('-ss')+1],calls[1][calls[1].index('-ss')+1])
        self.assertEqual(calls[1][calls[1].index('-ss')+1],calls[2][calls[2].index('-ss')+1])
        self.assertIn('format=p416le:',calls[0][calls[0].index('-vf')+1])
        self.assertIn('format=yuv444p16le:',calls[1][calls[1].index('-vf')+1])
        for cmd in calls[2:]:
            self.assertIn('format=yuv420p16le:',cmd[cmd.index('-vf')+1])
        self.assertIn('format=yuv420p16le:',v.normalization('dv'))

    def test_decode_failure_is_reported_immediately(self):
        info=dict(width=1920,height=1080,duration='100',pix_fmt='yuv420p10le')
        failed=subprocess.CompletedProcess([],1,'','corrupt decoded frame')
        with patch.object(v,'classify',return_value='dv'),patch.object(v,'color_filter',return_value=''),patch.object(v.subprocess,'run',return_value=failed) as run:
            with self.assertRaisesRegex(RuntimeError,'corrupt decoded frame'):
                v.detect_crop('ffmpeg','ffprobe',Path('ref.mkv'),info)
        self.assertEqual(run.call_count,1)

    def test_zero_exit_render_failure_retries_and_does_not_count_black_frames(self):
        info=dict(width=1920,height=1080,duration='100',pix_fmt='yuv420p10le')
        def run(cmd,**kwargs):
            vf=cmd[cmd.index('-vf')+1]
            if 'format=p416le:' in vf:
                return subprocess.CompletedProcess(cmd,0,'','Failed rendering image! crop=100:100:0:0')
            return subprocess.CompletedProcess(cmd,0,'','crop=1920:800:0:140')
        with patch.object(v,'classify',return_value='dv'),patch.object(v,'color_filter',return_value=''),patch.object(v.subprocess,'run',side_effect=run):
            rectangle,info=v.detect_crop('ffmpeg','ffprobe',Path('ref.mkv'),info)
        self.assertEqual(rectangle,(1920,800,0,140))
        self.assertEqual(len(info['samples']),7)
