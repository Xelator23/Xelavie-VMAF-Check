"""Set XELAVIE_DV_TEST_ICD to a Mesa Lavapipe manifest for the native regression."""
import os
from pathlib import Path
import re
import subprocess
import unittest

import vmaf_dv


@unittest.skipUnless(os.environ.get('XELAVIE_DV_TEST_ICD'), 'CPU Vulkan test manifest required')
class RepeatedDolbyVisionFrameTests(unittest.TestCase):
    def test_identical_pixels_with_changing_metadata(self):
        root = Path(__file__).resolve().parent / 'native' / 'dv' / 'test-fixtures'
        source = dict(width=320, height=192, codec_name='hevc', pix_fmt='yuv420p10le')
        reused = []
        for name in ('constant', 'changed'):
            path = root / (name + '.mkv')
            exe, filters, settings, _ = vmaf_dv.decoder(path, source, (320, 192, 0, 0))
            settings.update(VK_DRIVER_FILES=os.environ['XELAVIE_DV_TEST_ICD'],
                            VK_ICD_FILENAMES=os.environ['XELAVIE_DV_TEST_ICD'],
                            VK_LOADER_LAYERS_DISABLE='~implicit~')
            command = [exe, '-nostdin', '-v', 'info', '-init_hw_device', 'vulkan=vk:llvmpipe',
                       '-filter_hw_device', 'vk', '-i', str(path), '-map', '0:V:0', '-an', '-sn',
                       '-vf', filters + 'format=yuv420p16le', '-pix_fmt', 'yuv420p16le',
                       '-f', 'rawvideo', '-']
            with self.subTest(metadata=name):
                self.assertEqual(settings.pop('XELAVIE_REPEAT_FRAMES'), '1')
                previous = subprocess.run(command, env=settings, capture_output=True, check=True, timeout=60)
                current = subprocess.run(command, env=dict(settings, XELAVIE_REPEAT_FRAMES='1'),
                                         capture_output=True, check=True, timeout=60)
                self.assertEqual(len(previous.stdout), 24 * 320 * 192 * 3)
                self.assertTrue(previous.stdout == current.stdout, 'Rendered 16-bit image data differ')
                counts = re.findall(rb'Identical rendered inputs reused: (\d+)', current.stderr)
                self.assertTrue(counts)
                reused.append(sum(map(int, counts)))
        self.assertGreaterEqual(reused[0], 18)
        self.assertGreater(reused[1], 0)
        self.assertLessEqual(reused[1], reused[0] - 5)
