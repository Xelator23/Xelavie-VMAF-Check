import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import vmaf_settings as s


class SettingsTests(unittest.TestCase):
    def test_persistence_and_separate_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.dict(os.environ,{'VMAF_SETTINGS_FILE':str(root/'config'/'settings.json')}):
                chosen=s.save_work_directory(str(root/'Arbeitsordner'))
                self.assertEqual(s.work_directory(),chosen)
                self.assertTrue((chosen/'Temp').is_dir())
                self.assertTrue((chosen/'Ergebnisse').is_dir())
                (chosen/'Ergebnisse'/'keep.txt').write_text('keep')
                s.save_work_directory(str(chosen))
                self.assertTrue((chosen/'Ergebnisse'/'keep.txt').exists())
                self.assertEqual(list((root/'config').glob('*.tmp')),[])

    def test_empty_path_rejected(self):
        with self.assertRaises(ValueError): s.save_work_directory(' ')

    def test_default_is_working_directory_not_system_temp(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'VMAF_SETTINGS_FILE':str(Path(tmp)/'missing.json')}):
            self.assertEqual(s.work_directory(),Path.cwd()/'VMAF-Arbeit')
