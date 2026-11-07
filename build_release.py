"""Build platform-specific source distributions; no downloaded binaries included."""
import argparse
import hashlib
from pathlib import Path
import tarfile
import zipfile
from vmaf_check import __version__


def build(destination):
    root=Path(__file__).resolve().parent
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    common=[p for p in root.iterdir() if p.is_file() and (p.suffix in ('.py','.html','.js','.png','.md','.txt') or p.name=='LICENSE')]
    common+=sorted((root/'docs').rglob('*.png'))
    windows=common+[root/name for name in ('vmaf-check.cmd','vmaf-check.ps1','download_windows.ps1')]
    linux=common+[root/'vmaf-check.sh',root/'download_windows.ps1']
    # The Windows helper is referenced by a cross-platform unit test; harmless on Linux.
    prefix='Xelavie-VMAF-Check'
    win=destination/f'{prefix}-{__version__}-Windows.zip'
    lin=destination/f'{prefix}-{__version__}-Linux.tar.gz'
    with zipfile.ZipFile(win,'w',zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(set(windows)):
            archive.write(file,prefix+'/'+file.relative_to(root).as_posix())
    with tarfile.open(lin,'w:gz',format=tarfile.PAX_FORMAT) as archive:
        for file in sorted(set(linux)):
            name=prefix+'/'+file.relative_to(root).as_posix()
            info=archive.gettarinfo(str(file),arcname=name)
            info.uid=info.gid=0;info.uname=info.gname=''
            info.mode=0o755 if file.suffix=='.sh' else 0o644
            with file.open('rb') as stream:archive.addfile(info,stream)
    with zipfile.ZipFile(win) as archive:assert archive.testzip() is None
    with tarfile.open(lin) as archive:
        assert archive.getmember(prefix+'/vmaf-check.sh').mode==0o755
        for member in archive:
            assert member.isfile() and member.name.startswith(prefix+'/') and '..' not in Path(member.name).parts
    checksums=''.join(hashlib.sha256(file.read_bytes()).hexdigest()+'  '+file.name+'\n' for file in (win,lin))
    (destination/'SHA256SUMS.txt').write_text(checksums,encoding='utf-8')
    print(checksums,end='')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent/'dist')
    build(parser.parse_args().output)
