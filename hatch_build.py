"""Keep native Linux workers executable even when the wheel is built on Windows."""
from pathlib import Path
import os
import tempfile
import zipfile
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def finalize(self,version,build_data,artifact_path):
        if self.target_name!='wheel':return
        artifact=Path(artifact_path)
        with tempfile.TemporaryDirectory(dir=artifact.parent) as temporary:
            rebuilt=Path(temporary)/artifact.name
            with zipfile.ZipFile(artifact) as source,zipfile.ZipFile(rebuilt,'w') as target:
                for info in source.infolist():
                    if '/bin/linux-' in info.filename and info.filename.endswith('/xelavie-hdr-worker'):
                        info.create_system=3
                        info.external_attr=0o100755<<16
                    target.writestr(info,source.read(info.filename))
            os.replace(rebuilt,artifact)
