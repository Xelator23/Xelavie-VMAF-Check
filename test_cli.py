import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import vmaf_cli as c
import vmaf_launcher as l


class CliTests(unittest.TestCase):
    def test_preview_filters_and_limits_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);(base/'Filme').mkdir();(base/'Film eins.mkv').touch();(base/'Andere.mkv').touch()
            rows=c.preview_rows('Film',base)
            self.assertIn('  [Ordner] Filme',rows)
            self.assertIn('  [Datei]  Film eins.mkv',rows)
            self.assertNotIn('Andere.mkv','\n'.join(rows))
            self.assertIn('1 weitere Treffer',c.preview_rows('Film',base,limit=1)[-1])
            self.assertIn('Keine passenden',c.preview_rows('Unbekannt',base)[-1])
    def test_live_preview_redraw_and_selection(self):
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()) as out:
            base=Path(tmp);file=base/'Film.mkv';file.touch()
            keys=iter('Fi\t\r')
            self.assertEqual(c.windows_input('Datei: ','',base,lambda:next(keys),preview=True),str(file))
            self.assertIn('[Datei]  Film.mkv',out.getvalue())
            self.assertIn('\x1b[J',out.getvalue())
            self.assertTrue(out.getvalue().endswith('\n'))
    def test_empty_prompt_and_completion_uses_base(self):
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
            base=Path(tmp);file=base/'film.mkv';file.touch()
            keys=iter('\t\r')
            self.assertEqual(c.windows_input('Datei: ','',base,lambda:next(keys)),str(file))
    def test_navigate_parent_other_directory_and_list(self):
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()) as out:
            base=Path(tmp);a=base/'a';b=base/'anderer Ordner';a.mkdir();b.mkdir();(b/'film.mkv').touch()
            with patch.object(c,'path_input',side_effect=['cd ..','cd "anderer Ordner"','dir','film.mkv']) as prompt:
                self.assertEqual(c.choose_file('Original',a),str(b/'film.mkv'))
            self.assertEqual(prompt.call_args_list[1].args[1],base)
            self.assertEqual(prompt.call_args_list[2].args[1],b)
            self.assertIn('Datei   film.mkv',out.getvalue())
    def test_absolute_path_not_appended_to_start_directory(self):
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
            base=Path(tmp);(base/'a').mkdir();(base/'b').mkdir();file=base/'b'/'film.mkv';file.touch()
            with patch.object(c,'path_input',side_effect=[str(file.parent),'film.mkv']):
                self.assertEqual(c.choose_file('Encode',base/'a'),str(file))
    def test_cd_completion_only_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);(base/'Filmordner').mkdir();(base/'Film.mkv').touch()
            self.assertEqual(c.completions('cd Fil',base),['cd '+str(base/'Filmordner')+os.sep])
    @unittest.skipUnless(os.name=='nt','Windows drive syntax')
    def test_drive_root_and_cd_d(self):
        self.assertEqual(c.navigation_path('D:'),('D:\\',False))
        self.assertEqual(c.navigation_path('cd /d "D:\\Andere Filme"'),('D:\\Andere Filme',True))
    def test_completion_spaces_unicode_and_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);(base/'Film eins.mkv').touch();(base/'Film zwei.mkv').touch();(base/'Bilder').mkdir()
            self.assertEqual(c.completions('Film ',base),[str(base/'Film eins.mkv'),str(base/'Film zwei.mkv')])
            self.assertEqual(c.completions('Bil',base),[str(base/'Bilder')+os.sep])
            (base/'Prüfung.mkv').touch()
            self.assertEqual(c.completions('Prü',base),[str(base/'Prüfung.mkv')])
            self.assertEqual(c.completions('missing/',base),[])
    def test_windows_tab_cycle_and_edit(self):
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
            base=Path(tmp);(base/'A.mkv').touch();(base/'B.mkv').touch()
            keys=iter('\t\t\r')
            self.assertEqual(c.windows_input('Datei: ',str(base)+os.sep,base,lambda:next(keys)),str(base/'B.mkv'))
            keys=iter('\x15abc\xe0K\bZ\r')
            self.assertEqual(c.windows_input('',str(base),base,lambda:next(keys)),'aZc')
            keys=iter('\x03')
            with self.assertRaises(KeyboardInterrupt):c.windows_input('','',base,lambda:next(keys))
    def test_invalid_file_reprompt_and_relative_path(self):
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
            base=Path(tmp);(base/'movie.mkv').touch()
            with patch.object(c,'path_input',side_effect=['bad.mkv','"movie.mkv"']):
                self.assertEqual(c.choose_file('Datei',base),str(base/'movie.mkv'))
    def test_separate_saved_directories_and_color_flags(self):
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
            base=Path(tmp);ref=base/'original';enc=base/'encoded';ref.mkdir();enc.mkdir()
            a=ref/'a.mkv';b=enc/'b.mkv';a.touch();b.touch()
            with patch.dict(os.environ,{'VMAF_SETTINGS_FILE':str(base/'settings.json')}):
                with patch.object(c,'choose_file',side_effect=[str(a),str(b)]),patch('builtins.input',side_effect=['25','1','1','1','2']):
                    data=c.collect_inputs()
                cmd=l.build_command(data)
                self.assertIn('--ref-color',cmd);self.assertIn('--enc-color',cmd)
                self.assertEqual(data['enc-range'],'full');self.assertEqual(data['ref-color'],'bt709')
                self.assertEqual(json.loads((base/'cli.json').read_text()),{'reference_dir':str(ref),'encoded_dir':str(enc)})
                with patch.object(c,'choose_file',side_effect=[str(a),str(b)]) as choose,patch('builtins.input',side_effect=['','','']):
                    automatic=c.collect_inputs()
                self.assertEqual(choose.call_args_list[0].args[1],ref)
                self.assertEqual(choose.call_args_list[1].args[1],enc)
                self.assertEqual(automatic['ref-color'],'');self.assertEqual(automatic['enc-color'],'')
    def test_noninteractive_input_does_not_use_console_editor(self):
        with patch.object(c.sys.stdin,'isatty',return_value=False),patch('builtins.input',return_value='film.mkv'),patch.object(c,'windows_input') as editor:
            self.assertEqual(c.path_input('Datei: ',Path.cwd()),'film.mkv');editor.assert_not_called()
    def test_cli_passes_collected_fields(self):
        data={'reference':'a','encoded':'b','percent':'25','ref-color':'bt709','enc-color':'bt709'}
        with patch.object(c,'collect_inputs',return_value=data),patch.object(l,'build_command',return_value=['fake']) as build,patch.object(l.subprocess,'call',return_value=0),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(l.cli(),0);build.assert_called_once_with(data)

if __name__=='__main__':unittest.main()
