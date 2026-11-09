"""Isolated Windows CPU-Vulkan FFmpeg, same pinned FFmpeg/libplacebo sources."""
import hashlib,json,os,shutil,subprocess,tarfile,urllib.request
from pathlib import Path
root=Path('/experiment/neutral-validation');prefix=root/'deps';out=root/'windows';out.mkdir(exist_ok=True)
wrapper=Path('/usr/local/bin/dlltool')
if wrapper.is_symlink():wrapper.unlink()
wrapper.write_text('#!/bin/sh\nexec /usr/bin/x86_64-w64-mingw32-dlltool --as /usr/bin/x86_64-w64-mingw32-as "$@"\n');wrapper.chmod(0o755)
def run(cmd,cwd=root,env=None):
 print('RUN '+' '.join(map(str,cmd)),flush=True);subprocess.run(list(map(str,cmd)),cwd=cwd,env=env,check=True)
archive=root/'glslang-15.1.0.tar.gz'
if not archive.exists():
 with urllib.request.urlopen('https://codeload.github.com/KhronosGroup/glslang/tar.gz/refs/tags/15.1.0',timeout=90) as r:archive.write_bytes(r.read())
print('GLSLANG SHA256',hashlib.sha256(archive.read_bytes()).hexdigest(),flush=True)
if not (root/'glslang-15.1.0').exists():
 with tarfile.open(archive) as t:t.extractall(root,filter='data')
toolchain=root/'mingw.cmake'
toolchain.write_text('''set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR x86_64)
set(CMAKE_C_COMPILER x86_64-w64-mingw32-gcc-posix)
set(CMAKE_CXX_COMPILER x86_64-w64-mingw32-g++-posix)
set(CMAKE_RC_COMPILER x86_64-w64-mingw32-windres)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
''')
if not (prefix/'lib/libglslang.a').exists():
 run(['cmake','-S',root/'glslang-15.1.0','-B',root/'glslang-build','-G','Ninja',
      '-DCMAKE_TOOLCHAIN_FILE='+str(toolchain),'-DCMAKE_INSTALL_PREFIX='+str(prefix),'-DCMAKE_INSTALL_LIBDIR=lib',
      '-DCMAKE_BUILD_TYPE=Release','-DENABLE_OPT=OFF','-DENABLE_PCH=OFF','-DENABLE_GLSLANG_BINARIES=OFF',
      '-DGLSLANG_TESTS=OFF','-DBUILD_EXTERNAL=OFF','-DBUILD_SHARED_LIBS=OFF'])
 run(['cmake','--build',root/'glslang-build','-j','4']);run(['cmake','--install',root/'glslang-build'])
plsrc=root/'libplacebo'
if not plsrc.exists():
 shutil.copytree('/build/ffmpeg-matched/libplacebo/libplacebo-7.387.0',plsrc,ignore=shutil.ignore_patterns('build','.git'))
# Meson's MinGW static-library lookup needs explicit directories; link flags
# alone do not populate find_library's search path. Build-system-only change.
meson_glsl=plsrc/'src/glsl/meson.build';meson_text=meson_glsl.read_text()
meson_text=meson_text.replace("cxx.find_library('glslang-default-resource-limits', required: false)",
 "cxx.find_library('glslang-default-resource-limits', required: false, dirs: ['"+str(prefix/"lib")+"'])")
meson_text=meson_text.replace("cxx.find_library('glslang', required: required, static: static)",
 "cxx.find_library('glslang', required: required, static: static, dirs: ['"+str(prefix/"lib")+"'])")
meson_glsl.write_text(meson_text)
headers=Path('/build/ffmpeg-matched/install/include/vulkan')
shutil.copytree(headers,prefix/'include/vulkan',dirs_exist_ok=True)
shutil.copytree(headers.parent/'vk_video',prefix/'include/vk_video',dirs_exist_ok=True)
(prefix/'lib/pkgconfig/vulkan.pc').write_text(f'''prefix={prefix}
includedir=${{prefix}}/include
Name: Vulkan
Description: Vulkan headers (dynamic loader supplied by FFmpeg)
Version: 1.4.0
Libs:
Cflags: -I${{includedir}}
''')
cross=root/'cross.ini'
cross.write_text(f'''[binaries]
c = 'x86_64-w64-mingw32-gcc-posix'
cpp = 'x86_64-w64-mingw32-g++-posix'
ar = 'x86_64-w64-mingw32-ar'
strip = 'x86_64-w64-mingw32-strip'
windres = 'x86_64-w64-mingw32-windres'
pkg-config = 'pkg-config'
cmake = 'cmake'
[host_machine]
system = 'windows'
cpu_family = 'x86_64'
cpu = 'x86_64'
endian = 'little'
[properties]
needs_exe_wrapper = true
pkg_config_libdir = ['{prefix}/lib/pkgconfig']
cmake_prefix_path = ['{prefix}']
[built-in options]
c_args = ['-I{prefix}/include']
cpp_args = ['-I{prefix}/include']
c_link_args = ['-L{prefix}/lib']
cpp_link_args = ['-L{prefix}/lib']
''')
env=dict(os.environ,PKG_CONFIG_PATH=str(prefix/'lib/pkgconfig')+':/build/native/build/windows-x86_64/install/lib/pkgconfig',
 PKG_CONFIG_LIBDIR=str(prefix/'lib/pkgconfig')+':/build/native/build/windows-x86_64/install/lib/pkgconfig')
if not (root/'placebo-build/build.ninja').exists():
 run(['meson','setup',root/'placebo-build',plsrc,'--cross-file='+str(cross),'--prefix='+str(prefix),'--libdir=lib',
 '--buildtype=release','--default-library=static','-Dvulkan-sdk='+str(prefix),'-Dvulkan=enabled','-Dvk-proc-addr=disabled','-Ddovi=enabled',
 '-Dlibdovi=disabled','-Dopengl=disabled','-Dd3d11=disabled','-Dlcms=disabled','-Dshaderc=disabled','-Dglslang=enabled',
 '-Ddemos=false','-Dtests=false','-Dbench=false','-Dunwind=disabled','-Dxxhash=disabled'],env=env)
run(['meson','compile','-C',root/'placebo-build','-j','4'],env=env);run(['meson','install','-C',root/'placebo-build'],env=env)
# FFmpeg treats absolute archives as compiler flags; keep dependencies after
# libplacebo for static linking by spelling them as ordinary -l arguments.
pc=prefix/'lib/pkgconfig/libplacebo.pc'
import re
pc.write_text(re.sub(re.escape(str(prefix))+r'/lib/lib([^ /]+)\.a',r'-l\1',pc.read_text()))
src=root/'ffmpeg-source'
if not src.exists():
 src.mkdir()
 with tarfile.open('/build/ffmpeg-matched/ffmpeg.tar.gz') as t:
  members=t.getmembers();top=members[0].name.split('/')[0]
  t.extractall(root/'ffmpeg-extract',filter='data')
 shutil.copytree(root/'ffmpeg-extract'/top,src,dirs_exist_ok=True)
target=src/'libavfilter/vf_libplacebo.c'
patch=json.loads((root/'patch.json').read_text())
original=target.read_text()
if 'XELAVIE_NEUTRAL_TARGET' not in original:
 for anchor,value in patch:
  assert original.count(anchor)==1,anchor
  original=original.replace(anchor,value)
 target.write_text(original)
build=root/'ffmpeg-build';build.mkdir(exist_ok=True)
if not (build/'ffbuild/config.mak').exists():
 run([src/'configure','--prefix='+str(out),'--target-os=mingw32','--arch=x86_64','--enable-cross-compile',
 '--cross-prefix=x86_64-w64-mingw32-','--cc=x86_64-w64-mingw32-gcc-posix','--cxx=x86_64-w64-mingw32-g++-posix',
 '--pkg-config=pkg-config','--pkg-config-flags=--static','--disable-everything','--disable-autodetect','--disable-doc',
 '--disable-debug','--disable-network','--disable-shared','--enable-static','--disable-ffplay','--enable-ffmpeg',
 '--enable-ffprobe','--enable-gpl','--enable-libplacebo','--enable-libzimg','--enable-libdav1d',
 '--extra-ldflags=-static','--extra-libs=-lstdc++ -lpthread -lm',
 '--enable-protocol=file,pipe','--enable-demuxer=matroska,hevc,rawvideo',
 '--enable-decoder=hevc,libdav1d,rawvideo,ffv1,wrapped_avframe','--enable-parser=hevc,av1',
 '--enable-encoder=rawvideo,wrapped_avframe,ffv1','--enable-muxer=null,rawvideo,hevc,matroska,framemd5,hash',
 '--enable-indev=lavfi','--enable-bsf=hevc_mp4toannexb,dovi_rpu,filter_units,extract_extradata',
 '--enable-filter=libplacebo,zscale,scale,crop,trim,setpts,settb,setparams,setsar,format,null,color,testsrc2,fps,split,select',
 '--enable-vulkan'],cwd=build,env=env)
run(['make','-j4','ffmpeg.exe','ffprobe.exe'],cwd=build,env=env)
for name in ('ffmpeg.exe','ffprobe.exe'):shutil.copy2(build/name,out/name)
(out/'build.json').write_text(json.dumps({'ffmpeg_source_sha256':hashlib.sha256(Path('/build/ffmpeg-matched/ffmpeg.tar.gz').read_bytes()).hexdigest(),
 'libplacebo':'7.387.0','glslang':'15.1.0','glslang_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
 'ffmpeg_sha256':hashlib.sha256((out/'ffmpeg.exe').read_bytes()).hexdigest()},indent=2))
run(['x86_64-w64-mingw32-objdump','-p',out/'ffmpeg.exe'])
print('WINDOWS NEUTRAL VALIDATION BUILD READY',flush=True)
