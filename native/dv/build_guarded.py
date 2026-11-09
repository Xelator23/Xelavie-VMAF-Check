from pathlib import Path
import json,os,shutil,subprocess,sys
platform=sys.argv[1];root=Path('/experiment/neutral-fix');out=root/(platform+'-v2');out.mkdir(parents=True,exist_ok=True)
win=platform=='windows';nr=Path('/experiment/neutral-validation')
plsrc=nr/'libplacebo' if win else root/'libplacebo-linux'
if not plsrc.exists():shutil.copytree('/build/ffmpeg-matched/libplacebo/libplacebo-7.387.0',plsrc,ignore=shutil.ignore_patterns('build','.git'))
plbuild=nr/'placebo-build' if win else root/'placebo-linux-build'
installed=nr/'deps/lib/libplacebo.a' if win else root/'linux-deps/lib/libplacebo.a'
if not installed.exists():
 installed.parent.mkdir(parents=True,exist_ok=True);shutil.copy2('/build/ffmpeg-matched/install/lib/libplacebo.a',installed)
ffsrc=nr/'ffmpeg-source' if win else Path('/experiment/ffmpeg-transfer/source')
ffbuild=nr/'ffmpeg-build' if win else ffsrc
c=plsrc/'src/shaders/colorspace.c';f=ffsrc/'libavfilter/vf_libplacebo.c'
orig=c.read_bytes();fforig=f.read_bytes();liborig=installed.read_bytes()
config=ffbuild/'ffbuild/config.mak';configorig=config.read_bytes()
def run(cmd,cwd=None):subprocess.run(list(map(str,cmd)),cwd=cwd,check=True)
try:
 code=orig.decode();anchor='    bool need_gamut_map = !pl_gamut_map_params_noop(&gamut);'
 assert code.count(anchor)==1
 diag=r'''
    if (getenv("XELAVIE_MAP_DIAG")) {
        PL_WARN(sh, "XELAVIE_MAP tone=%s in=%.9g,%.9g out=%.9g,%.9g exposure=%.9g gamut=%d mastering=%d clip=%.9g film=%.9g srcpeak=%.9g space=%d->%d prelinear=%d",
            tone.function->name, tone.input_min, tone.input_max, tone.output_min, tone.output_max,
            dt_exposure, need_gamut_map, use_mast_space, params->mastering_clip, params->film_strength,
            args->src.hdr.max_luma, src.primaries, dst.primaries, args->prelinearized);
    }
'''
 code=code.replace(anchor,anchor+diag)
 patch=root/'shader-patch.json'
 if patch.exists():
  for a,b in json.loads(patch.read_text()):assert code.count(a)==1,a;code=code.replace(a,b)
 c.write_text(code)
 ffcode=fforig.decode()
 if 'XELAVIE_NEUTRAL_TARGET' not in ffcode:
  for a,b in json.loads((nr/'patch.json').read_text()):assert ffcode.count(a)==1;ffcode=ffcode.replace(a,b)
 f.write_text(ffcode)
 if not win:
  os.environ['PKG_CONFIG_PATH']='/build/ffmpeg-matched/install/lib/pkgconfig'
  if not (plbuild/'build.ninja').exists():
   run(['meson','setup',plbuild,plsrc,'--buildtype=release','--default-library=static','-Dvulkan=enabled','-Dvk-proc-addr=disabled','-Ddovi=enabled','-Dlibdovi=disabled','-Dopengl=disabled','-Dd3d11=disabled','-Dlcms=disabled','-Dshaderc=disabled','-Dglslang=enabled','-Ddemos=false','-Dtests=false','-Dbench=false','-Dunwind=disabled','-Dxxhash=disabled'])
  config.write_text(configorig.decode().replace('-L/build/ffmpeg-matched/install/lib -lplacebo','-L'+str(installed.parent)+' -lplacebo'))
 run(['meson','compile','-C',plbuild,'-j','4'])
 # Use the new archive only for this private link, restore it afterwards.
 archives=list((plbuild/'src').glob('libplacebo.a'));assert len(archives)==1,archives
 shutil.copy2(archives[0],installed)
 # Relink since static external dependencies are not tracked by make.
 target=ffbuild/('ffmpeg.exe' if win else 'ffmpeg_g')
 target.touch();os.utime(target,(1,1))
 run(['make','-j4','ffmpeg.exe' if win else 'ffmpeg'],ffbuild)
 shutil.copy2(ffbuild/('ffmpeg.exe' if win else 'ffmpeg'),out/('ffmpeg.exe' if win else 'ffmpeg'))
 (out/'colorspace.c').write_text(code)
finally:
 c.write_bytes(orig);f.write_bytes(fforig);installed.write_bytes(liborig);config.write_bytes(configorig)
print(platform+' DIAGNOSTIC READY',flush=True)
