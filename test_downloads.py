import hashlib
import io
import os
from pathlib import Path
import ssl
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError,HTTPError
import vmaf_check as v


class DownloadTests(unittest.TestCase):
    def test_certificate_failure_uses_verified_windows_transport(self):
        error=URLError(ssl.SSLCertVerificationError(1,'CERTIFICATE_VERIFY_FAILED'))
        with patch.dict(os.environ,{'VMAF_CA_BUNDLE':'','SSL_CERT_FILE':''}),patch.object(v.urllib.request,'urlopen',side_effect=error),patch.object(v.platform,'system',return_value='Windows'),patch.object(v,'windows_fetch',return_value={'ok':True}) as native:
            self.assertEqual(v.fetch('https://example.invalid/data'),{'ok':True})
            native.assert_called_once_with('https://example.invalid/data',None)

    def test_http_error_never_switches_transport(self):
        with patch.object(v.urllib.request,'urlopen',side_effect=HTTPError('https://example.invalid',404,'missing',{},None)),patch.object(v,'windows_fetch') as native:
            with self.assertRaises(HTTPError):v.fetch('https://example.invalid')
            native.assert_not_called()

    def test_https_required(self):
        with self.assertRaises(ValueError):v.fetch('http://example.invalid')

    def test_stream_download_and_hash(self):
        with tempfile.TemporaryDirectory() as d,patch.object(v.urllib.request,'urlopen',return_value=io.BytesIO(b'payload')) as request:
            target=Path(d)/'asset';self.assertEqual(v.fetch('https://example.invalid/file',target),hashlib.sha256(b'payload').hexdigest())
            context=request.call_args.kwargs['context']
            self.assertTrue(context.check_hostname)
            self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)

    def test_custom_ca_failure_does_not_override_explicit_trust(self):
        error=URLError(ssl.SSLCertVerificationError(1,'CERTIFICATE_VERIFY_FAILED'))
        with patch.dict(os.environ,{'VMAF_CA_BUNDLE':'chosen.pem'}),patch.object(v.ssl,'create_default_context'),patch.object(v.urllib.request,'urlopen',side_effect=error),patch.object(v,'windows_fetch') as native:
            with self.assertRaises(RuntimeError):v.fetch('https://example.invalid')
            native.assert_not_called()


if __name__=='__main__':unittest.main()
