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
    def test_ffmpeg_relocated_downloads(self):
        for system, machine, tag, extension in (
                ('Windows', 'AMD64', 'win64', 'zip'),
                ('Windows', 'ARM64', 'winarm64', 'zip'),
                ('Linux', 'x86_64', 'linux64', 'tar.xz'),
                ('Linux', 'aarch64', 'linuxarm64', 'tar.xz')):
            for owner in ('BtbN', 'FFmpeg-Builds'):
                with self.subTest(system=system, machine=machine, owner=owner):
                    name=f'ffmpeg-master-latest-{tag}-gpl.{extension}'
                    url=f'https://github.com/{owner}/FFmpeg-Builds/releases/download/latest/{name}'
                    digest='a'*64
                    release={'assets':[{'name':name,'browser_download_url':url,'digest':'sha256:'+digest}]}
                    def unpack(_archive, destination):
                        destination.mkdir()
                        for tool in ('ffmpeg','ffprobe'):
                            (destination/(tool+('.exe' if system=='Windows' else ''))).touch()
                    with tempfile.TemporaryDirectory() as d, patch.object(v.platform,'system',return_value=system), patch.object(v.platform,'machine',return_value=machine), patch.object(v,'fetch',side_effect=[release,digest]) as fetch, patch.object(v,'unpack',side_effect=unpack):
                        manifest=[]
                        self.assertEqual(len(v.download_tools(Path(d),manifest)),2)
                        self.assertEqual(fetch.call_args.args,(url,Path(d)/name))
                        self.assertEqual(manifest,[{'url':url,'sha256':digest,'verified_release_digest':True}])

    def test_ffmpeg_relocation_rejects_other_sources(self):
        name='ffmpeg-master-latest-win64-gpl.zip'
        for prefix in ('https://github.com/other/FFmpeg-Builds/releases/download/',
                       'https://github.com.evil.invalid/FFmpeg-Builds/FFmpeg-Builds/releases/download/',
                       'http://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/download/'):
            with tempfile.TemporaryDirectory() as d, patch.object(v.platform,'system',return_value='Windows'), patch.object(v.platform,'machine',return_value='AMD64'), patch.object(v,'fetch',return_value={'assets':[{'name':name,'browser_download_url':prefix+'latest/'+name}]}) as fetch:
                with self.assertRaisesRegex(RuntimeError,'Download-Quelle'):
                    v.download_tools(Path(d),[])
                self.assertEqual(fetch.call_count,1)

    def test_ffmpeg_relocation_keeps_digest_verification(self):
        name='ffmpeg-master-latest-win64-gpl.zip'
        url='https://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/download/latest/'+name
        for digest in (None, 'sha256:'+'b'*64):
            release={'assets':[{'name':name,'browser_download_url':url,'digest':digest}]}
            with tempfile.TemporaryDirectory() as d, patch.object(v.platform,'system',return_value='Windows'), patch.object(v.platform,'machine',return_value='AMD64'), patch.object(v,'fetch',side_effect=[release,'a'*64]), patch.object(v,'unpack') as unpack:
                manifest=[]
                with self.assertRaisesRegex(RuntimeError,'SHA256'):
                    v.download_tools(Path(d),manifest)
                unpack.assert_not_called()
                self.assertEqual(manifest,[])

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
