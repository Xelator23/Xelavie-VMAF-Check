"""Private Linux FFmpeg build: original configuration plus upload/download filters."""
import os,shlex,subprocess,shutil
from pathlib import Path
old=next(Path('/build/ffmpeg-matched/ffmpeg').iterdir())
root=Path('/experiment/ffmpeg-transfer');root.mkdir(exist_ok=True)
source=root/'source'
if not source.exists():shutil.copytree(old,source)
config=(old/'ffbuild/config.mak').read_text()
line=next(x for x in config.splitlines() if x.startswith('FFMPEG_CONFIGURATION='))
args=shlex.split(line.split('=',1)[1])
args=[x for x in args if not x.startswith('--prefix=')]
args+=['--prefix='+str(root/'install'),'--enable-filter=hwupload,hwdownload']
env=dict(os.environ,PKG_CONFIG_PATH='/build/ffmpeg-matched/install/lib/pkgconfig:/build/native/build/linux-x86_64/install/lib/pkgconfig')
print('CONFIG',args,flush=True)
subprocess.run(['./configure',*args],cwd=source,env=env,check=True)
subprocess.run(['make','-j4','ffmpeg'],cwd=source,env=env,check=True)
shutil.copy2(source/'ffmpeg',root/'ffmpeg')
print('TRANSFER BUILD READY',flush=True)
