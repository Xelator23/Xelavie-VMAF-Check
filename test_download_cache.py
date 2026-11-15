import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import vmaf_check as v

class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.cache=self.root/'cache';self.target=self.root/'asset'
        self.payload=b'verified tool payload';self.sha=hashlib.sha256(self.payload).hexdigest()
        self.url='https://example.invalid/tool.zip'
        self.patcher=patch.object(v,'DOWNLOAD_CACHE',self.cache);self.patcher.start();self.addCleanup(self.patcher.stop)
    def download(self,url,target):
        Path(target).write_bytes(self.payload);return self.sha
    def test_cold_then_warm_no_second_download(self):
        with patch.object(v,'fetch',side_effect=self.download) as fetch:
            self.assertEqual(v.verified_fetch(self.url,self.target,self.sha),self.sha)
            self.target.unlink();v.verified_fetch(self.url,self.target,self.sha)
            self.assertEqual(fetch.call_count,1);self.assertEqual(self.target.read_bytes(),self.payload)
            self.assertEqual(list(self.cache.iterdir()),[self.cache/self.sha])
    def test_corruption_is_replaced_not_executed(self):
        self.cache.mkdir();(self.cache/self.sha).write_bytes(b'corrupt')
        with patch.object(v,'fetch',side_effect=self.download) as fetch:v.verified_fetch(self.url,self.target,self.sha)
        fetch.assert_called_once();self.assertEqual((self.cache/self.sha).read_bytes(),self.payload)
    def test_refresh_bypasses_valid_cache(self):
        self.cache.mkdir();(self.cache/self.sha).write_bytes(self.payload)
        with patch.object(v,'fetch',side_effect=self.download) as fetch:v.verified_fetch(self.url,self.target,self.sha,refresh=True)
        fetch.assert_called_once()
    def test_missing_digest_and_http_rejected_even_with_cache(self):
        self.cache.mkdir();(self.cache/self.sha).write_bytes(self.payload)
        with patch.object(v,'fetch') as fetch:
            for digest in (None,'../escape','x'*64,'A'*64):
                with self.assertRaises(RuntimeError):v.verified_fetch(self.url,self.target,digest)
            with self.assertRaises(ValueError):v.verified_fetch('http://example.invalid/tool',self.target,self.sha)
            fetch.assert_not_called()
    def test_failed_download_does_not_poison_good_cache(self):
        self.cache.mkdir();(self.cache/self.sha).write_bytes(self.payload)
        def wrong(url,path):Path(path).write_bytes(b'wrong');return hashlib.sha256(b'wrong').hexdigest()
        with patch.object(v,'fetch',side_effect=wrong):
            with self.assertRaises(RuntimeError):v.verified_fetch(self.url,self.target,self.sha,refresh=True)
        self.assertEqual((self.cache/self.sha).read_bytes(),self.payload)
    def test_cache_write_error_does_not_break_verified_download(self):
        self.cache.write_bytes(b'not a directory')
        with patch.object(v,'fetch',side_effect=self.download):v.verified_fetch(self.url,self.target,self.sha)
        self.assertEqual(self.target.read_bytes(),self.payload)
    def test_cache_cleanup_failure_is_nonfatal(self):
        with patch.object(v,'fetch',side_effect=self.download),patch.object(Path,'unlink',side_effect=PermissionError('cleanup')):
            self.assertEqual(v.verified_fetch(self.url,self.target,self.sha),self.sha)
        self.assertEqual(self.target.read_bytes(),self.payload)

    def test_changed_release_digest_cannot_use_old_entry(self):
        self.cache.mkdir();(self.cache/self.sha).write_bytes(self.payload)
        new_payload=b'new release';new_sha=hashlib.sha256(new_payload).hexdigest()
        def download(url,path):Path(path).write_bytes(new_payload);return new_sha
        with patch.object(v,'fetch',side_effect=download) as fetch:v.verified_fetch(self.url,self.target,new_sha)
        fetch.assert_called_once();self.assertEqual(self.target.read_bytes(),new_payload)

if __name__=='__main__':unittest.main()
