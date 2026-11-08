import io
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch
import vmaf_check as v


class P7RemuxTests(unittest.TestCase):
    def stream(self, profile):
        return {'width':3840,'height':2160,'side_data_list':[{
            'dv_profile':profile,'dv_bl_signal_compatibility_id':1,'el_present_flag':0}]}

    def test_mkvmerge_preserves_rational_rate_and_checks_exit_status(self):
        for status in (0,1,2):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as folder:
                root=Path(folder);raw=root/'ref-p81.hevc';raw.touch()
                producer=Mock(stdout=io.BytesIO(),wait=Mock(return_value=0),poll=Mock(return_value=0))
                consumer=Mock(wait=Mock(return_value=0),poll=Mock(return_value=0))
                with patch.object(v.subprocess,'Popen',side_effect=[producer,consumer]), patch.object(v.subprocess,'run',return_value=SimpleNamespace(returncode=status)) as mux, patch.object(v,'probe',return_value=self.stream(8)):
                    args=('ffmpeg','ffprobe',root/'input.mkv',self.stream(7),'compatible','dovi',root,root,'ref',Fraction(24000,1001),'mkvmerge')
                    if status==2:
                        with self.assertRaisesRegex(RuntimeError,'Remux fehlgeschlagen'):v.prepare_dv(*args)
                        self.assertTrue(raw.exists())
                    else:
                        result,_,audit=v.prepare_dv(*args)
                        self.assertFalse(raw.exists());self.assertFalse(audit['reencoded'])
                        self.assertEqual(result,root/'ref-prepared.mkv')
                    self.assertEqual(mux.call_args.args[0],['mkvmerge','-o',str(root/'ref-prepared.mkv'),'--default-duration','0:24000/1001fps',str(raw)])

    def test_missing_mkvmerge_fails_before_extracting(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(v.subprocess,'Popen') as process:
            root=Path(folder)
            with self.assertRaisesRegex(RuntimeError,'mkvmerge'):
                v.prepare_dv('ffmpeg','ffprobe',root/'input.mkv',self.stream(7),'compatible','dovi',root,root,'ref',Fraction(24))
            process.assert_not_called()

    def test_mkvtoolnix_download_requires_pinned_hash(self):
        for system in ('nt','posix'):
            with tempfile.TemporaryDirectory() as folder, patch.object(v,'os',SimpleNamespace(name=system)), patch.object(v.platform,'machine',return_value='x86_64'), patch.object(v,'fetch',return_value='incorrect'), patch.object(v,'unpack') as unpack, patch.object(v,'run') as run:
                manifest=[]
                with self.assertRaisesRegex(RuntimeError,'SHA256'):v.download_mkvmerge(Path(folder),manifest)
                self.assertEqual(manifest,[]);unpack.assert_not_called();run.assert_not_called()

    def test_windows_download_extracts_verified_tool(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            def unpack(archive,dest):(dest/'mkvmerge.exe').touch()
            with patch.object(v,'os',SimpleNamespace(name='nt')), patch.object(v.platform,'machine',return_value='AMD64'), patch.object(v,'fetch',return_value='c02e918900f6d945d9307b426237e456378b79a200589ac6928de39064409a44'), patch.object(v,'unpack',side_effect=unpack):
                manifest=[];tool=v.download_mkvmerge(root,manifest)
                self.assertTrue(Path(tool).is_file());self.assertTrue(manifest[0]['verified_pinned_digest'])

    def test_linux_download_extracts_without_fuse(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            def fetch(url,archive):
                archive.touch()
                return 'c66345b30d6d5fd640ea982ab5e202a99b9f541a20e42aa19edd90f3ddd5dc9b'
            with patch.object(v,'os',SimpleNamespace(name='posix')), patch.object(v.platform,'machine',return_value='x86_64'), patch.object(v,'fetch',side_effect=fetch), patch.object(v,'run') as run:
                tool=Path(v.download_mkvmerge(root,[]))
                run.assert_called_once_with([root/'mkvmerge.AppImage','--appimage-extract'],cwd=root/'mkvtoolnix')
                self.assertIn('export ARGV0=mkvmerge',tool.read_text())
                self.assertIn('exec "$APPDIR/AppRun" "$@"',tool.read_text())


if __name__=='__main__':unittest.main()
