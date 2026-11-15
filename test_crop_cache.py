import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import vmaf_check as v


class ContentVerifiedCrops(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.cache = root/'Cache'
        self.source = root/'original.mkv'
        self.source.write_bytes(b'old movie bytes')
        self.tool = root/'binary'
        self.tool.write_bytes(b'ffmpeg')
        self.stream = dict(width=1920, height=1080, pix_fmt='yuv420p10le')
        self.scan = (1920,800,0,140), dict(rectangle=[1920,800,0,140], samples=[{}, {}, {}], skipped=[])

    def detector(self):
        return v.DVCropCache(self.cache,self.tool,self.tool,{},'')

    def invoke(self, cache):
        return cache.detect(self.source,v.crop_source_stamp(self.source),self.source,self.stream,None,())

    def seed(self):
        hashed = threading.Event()
        def hash_file(path, finished):
            result = v.file_sha256(path)
            hashed.set()
            return result
        def detect(*_):
            self.assertTrue(hashed.wait(5))
            return self.scan
        with patch.object(v,'crop_source_hash',side_effect=hash_file),patch.object(v,'detect_crop',side_effect=detect):
            self.invoke(self.detector())
        self.assertEqual(len(list(self.cache.glob('*.json'))),1)

    def test_hit_checks_content_and_reuses_diagnostics(self):
        self.seed()
        with patch.object(v,'detect_crop',side_effect=AssertionError),patch.object(v,'crop_source_hash',wraps=v.crop_source_hash) as digest:
            self.assertEqual(self.invoke(self.detector()),self.scan)
            digest.assert_called_once()

    def test_same_stamp_but_changed_movie_is_rechecked(self):
        self.seed()
        stamp=v.crop_source_stamp(self.source)
        self.source.write_bytes(b'new movie bytes')
        with patch.object(v,'crop_source_stamp',return_value=stamp),patch.object(v,'detect_crop',return_value=self.scan) as detect:
            self.invoke(self.detector())
            detect.assert_called_once()

    def test_stale_tool_and_color_overrides_force_recheck(self):
        self.seed()
        self.stream['_color_overrides']={'color_range':'pc'}
        with patch.object(v,'detect_crop',return_value=self.scan) as detect:
            self.invoke(self.detector())
            detect.assert_called_once()
        del self.stream['_color_overrides']
        self.tool.write_bytes(b'new binary')
        with patch.object(v,'detect_crop',return_value=self.scan) as detect:
            self.invoke(self.detector())
            detect.assert_called_once()

    def test_corrupt_entry_and_absent_permission_fall_back(self):
        self.seed()
        path=next(self.cache.glob('*.json'))
        record=json.loads(path.read_bytes())
        record['payload']['info']['rectangle']=[1920,700,0,190]
        path.write_text(json.dumps(record))
        with patch.object(v,'detect_crop',return_value=self.scan) as detect:
            self.invoke(self.detector())
            detect.assert_called_once()
        with patch.object(v,'crop_source_hash',side_effect=OSError),patch.object(v,'detect_crop',return_value=self.scan):
            self.assertEqual(self.invoke(self.detector()),self.scan)

    def test_large_file_hash_stops_when_scan_ends(self):
        def slow(path,finished):
            self.assertTrue(finished.wait(5))
            return None
        with patch.object(v,'crop_source_hash',side_effect=slow),patch.object(v,'detect_crop',return_value=self.scan):
            self.assertEqual(self.invoke(self.detector()),self.scan)
        self.assertFalse(any(self.cache.glob('*.json')))

    def test_p7_uses_exact_extracted_video_without_rereading_the_remux(self):
        stamp=v.crop_source_stamp(self.source)
        info={'operation':'p7_to_p81_discard_el','annexb_sha256':'a'*64}
        with patch.object(v,'crop_source_hash',side_effect=AssertionError),patch.object(v,'detect_crop',return_value=self.scan) as detect:
            for _ in range(2):
                self.assertEqual(self.detector().detect(self.source,stamp,self.source,self.stream,info,(self.tool,)),self.scan)
            self.assertEqual(detect.call_count,1)
            info['annexb_sha256']='b'*64
            self.detector().detect(self.source,stamp,self.source,self.stream,info,(self.tool,))
            self.assertEqual(detect.call_count,2)

    def test_ambiguous_or_failed_scans_are_not_cached(self):
        with patch.object(v,'detect_crop',return_value=(None,{'reason':'dark'})):
            self.assertIsNone(self.invoke(self.detector())[0])
        with patch.object(v,'detect_crop',side_effect=RuntimeError('decode failure')):
            with self.assertRaisesRegex(RuntimeError,'decode failure'):
                self.invoke(self.detector())
        self.assertFalse(any(self.cache.glob('*.json')))

    def test_different_encode_does_not_invalidate_reference(self):
        self.seed()
        cache=self.detector()
        other=self.source.with_name('other-encode.mkv')
        other.write_bytes(b'another encode')
        with patch.object(v,'detect_crop',return_value=self.scan) as detect:
            self.invoke(cache)
            cache.detect(other,v.crop_source_stamp(other),other,self.stream,None,())
            detect.assert_called_once()

    def test_explicit_mesa_limit_disables_automatic_parallel_scan(self):
        with patch.dict(v.os.environ,LP_NUM_THREADS='3'):
            self.assertFalse(v.parallel_dv_crops(self.stream,self.stream))
