import hashlib,json,os,subprocess,tarfile,urllib.request,shutil
from pathlib import Path
root=Path('/build/ffmpeg-matched');root.mkdir(exist_ok=True)
sources={}
for name,url in [('ffmpeg','https://codeload.github.com/FFmpeg/FFmpeg/tar.gz/5d85b7bfb2b024fd367ae3a938b4ac46a39e3a26'),
                 ('libplacebo','https://codeload.github.com/haasn/libplacebo/tar.gz/refs/tags/v7.387.0'),
                 ('Vulkan-Headers','https://codeload.github.com/KhronosGroup/Vulkan-Headers/tar.gz/74d8a6cb930c68ef617b202c3ff3c59d919e086b'),
                 ('fast_float','https://codeload.github.com/fastfloat/fast_float/tar.gz/97b54ca9e75f5303507699d27c6b4f4efe4641a1')]:
    archive=root/(name+'.tar.gz')
    if not archive.exists():
        with urllib.request.urlopen(url,timeout=90) as r:archive.write_bytes(r.read())
    directory=root/name
    if not directory.exists():
        directory.mkdir()
        with tarfile.open(archive) as t:t.extractall(directory,filter='data')
    sources[name]=next(directory.iterdir())
    print(name,url,hashlib.sha256(archive.read_bytes()).hexdigest(),flush=True)
prefix=root/'install';native=Path('/build/native/build/linux-x86_64/install')
env=dict(os.environ,PKG_CONFIG_PATH=str(prefix/'lib/pkgconfig')+':'+str(native/'lib/pkgconfig'))
def run(cmd,cwd):subprocess.run(list(map(str,cmd)),cwd=cwd,env=env,check=True)
placebo=sources['libplacebo']
for name in ('Vulkan-Headers','fast_float'):shutil.copytree(sources[name],placebo/'3rdparty'/name,dirs_exist_ok=True)
run(['cmake','-S',sources['Vulkan-Headers'],'-B',root/'headers-build','-DCMAKE_INSTALL_PREFIX='+str(prefix)],root)
run(['cmake','--install',root/'headers-build'],root)
if not (placebo/'build/build.ninja').exists():
    run(['meson','setup','build','--prefix='+str(prefix),'--libdir=lib','--buildtype=release','--default-library=static',
         '-Dvulkan=enabled','-Dvk-proc-addr=disabled','-Ddovi=enabled','-Dlibdovi=disabled','-Dopengl=disabled',
         '-Dd3d11=disabled','-Dlcms=disabled','-Dshaderc=disabled','-Dglslang=enabled','-Ddemos=false','-Dtests=false',
         '-Dbench=false','-Dunwind=disabled','-Dxxhash=disabled'],placebo)
run(['ninja','-C','build','install'],placebo)
ff=sources['ffmpeg']
run(['./configure','--prefix='+str(prefix),'--disable-everything','--disable-autodetect','--disable-doc','--disable-debug',
     '--disable-shared','--enable-static','--disable-ffplay','--enable-ffmpeg','--enable-ffprobe','--enable-gpl',
     '--enable-libplacebo','--enable-libzimg','--enable-libdav1d','--enable-libvmaf','--pkg-config-flags=--static',
     '--extra-libs=-lSPIRV -lglslang -lMachineIndependent -lOSDependent -lGenericCodeGen -lSPIRV-Tools-opt -lSPIRV-Tools -lstdc++ -lpthread -lm','--enable-protocol=file,pipe',
     '--enable-demuxer=matroska,hevc,rawvideo','--enable-decoder=hevc,libdav1d,rawvideo,ffv1,wrapped_avframe',
     '--enable-parser=hevc,av1','--enable-encoder=rawvideo,wrapped_avframe,ffv1',
     '--enable-muxer=null,rawvideo,hevc,matroska,framemd5,hash','--enable-indev=lavfi',
     '--enable-bsf=hevc_mp4toannexb,dovi_rpu,filter_units,extract_extradata',
     '--enable-filter=libplacebo,zscale,scale,crop,cropdetect,trim,setpts,settb,setparams,setsar,format,null,color,testsrc2,fps,libvmaf,split,select',
     '--enable-vulkan'],ff)
run(['make','-j4','ffmpeg','ffprobe'],ff)
run(['make','install'],ff)
print('MATCHED FFMPEG BUILT',flush=True)
