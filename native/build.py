"""Build Linux and Windows x64 HDR workers on Linux; no publication.

Requires gcc/g++, mingw-w64 POSIX compilers, make, autoconf/automake/libtool,
meson, ninja, nasm, pkg-config, xxd and Python 3.12+. Sources are SHA256 pinned.
"""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tarfile
import urllib.request

root=Path(__file__).resolve().parent
work=root/'build'
work.mkdir(exist_ok=True)
spec=json.loads((root/'sources.json').read_text())
archives={}
for name in ('zimg','graphengine','vmaf'):
    item=spec[name];archive=work/(name+'.tar.gz')
    if not archive.exists():
        with urllib.request.urlopen(item['url'],timeout=120) as r:archive.write_bytes(r.read())
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=item['sha256']:raise ValueError(name+' source checksum')
    archives[name]=archive
for target in ('linux-x86_64','windows-x86_64'):
    folder=work/target;folder.mkdir(exist_ok=True)
    prefix=folder/'install';sources={}
    for name,archive in archives.items():
        dest=folder/name
        if not dest.exists():
            dest.mkdir()
            with tarfile.open(archive) as t:t.extractall(dest,filter='data')
        sources[name]=next(dest.iterdir())
    win=target.startswith('windows');cc='x86_64-w64-mingw32-gcc-posix' if win else 'gcc'
    cxx='x86_64-w64-mingw32-g++-posix' if win else 'g++'
    env=dict(os.environ,CC=cc,CXX=cxx,PKG_CONFIG_PATH=str(prefix/'lib/pkgconfig'))
    def run(cmd,cwd):subprocess.run(list(map(str,cmd)),cwd=cwd,env=env,check=True)
    z=sources['zimg'];shutil.copytree(sources['graphengine'],z/'graphengine',dirs_exist_ok=True)
    if not (prefix/'lib/libzimg.a').exists():
        run(['./autogen.sh'],z)
        run(['./configure','--prefix='+str(prefix),'--disable-shared','--enable-static']+
            (['--host=x86_64-w64-mingw32'] if win else []),z)
        run(['make','-j4'],z);run(['make','install'],z)
    v=sources['vmaf']/'libvmaf';cross=[]
    if win:
        ini=folder/'cross.ini'
        ini.write_text("[binaries]\nc = '"+cc+"'\ncpp = '"+cxx+"'\nar = 'x86_64-w64-mingw32-ar'\nstrip = 'x86_64-w64-mingw32-strip'\nwindres = 'x86_64-w64-mingw32-windres'\npkg-config = 'pkg-config'\n[host_machine]\nsystem = 'windows'\ncpu_family = 'x86_64'\ncpu = 'x86_64'\nendian = 'little'\n[properties]\nneeds_exe_wrapper = true\npkg_config_libdir = ['"+str(prefix/'lib/pkgconfig')+"']\n")
        cross=['--cross-file',ini]
    if not (v/'build').exists():
        run(['meson','setup','build','--prefix='+str(prefix),'--libdir=lib','--buildtype=release',
            '--default-library=static','-Denable_tests=false','-Denable_docs=false',
            '-Denable_tools=false','-Denable_zimg=true',*cross],v)
    run(['ninja','-C','build','install'],v)
    dest=root.parent/'bin'/target;dest.mkdir(parents=True,exist_ok=True)
    flags=shlex.split(subprocess.check_output(['pkg-config','--cflags','--libs','--static','libvmaf'],env=env,text=True))
    binary=dest/('xelavie-hdr-worker.exe' if win else 'xelavie-hdr-worker')
    run([cc,'-O2','-std=c11','-static','-I'+str(v/'src'),root/'hdr_worker.c','-o',binary,*flags,'-lstdc++','-lm','-lpthread'],root)
    run(['x86_64-w64-mingw32-strip' if win else 'strip',binary],root)
    licenses=dest/'licenses';licenses.mkdir(exist_ok=True)
    for name,filename in [('vmaf','LICENSE'),('zimg','COPYING'),('graphengine','COPYING')]:
        shutil.copy2(sources[name]/filename,licenses/(name+'-LICENSE'))
    shutil.copy2(root/'sources.json',licenses/'sources.json')
    for label,path in [('gcc-runtime','/usr/share/doc/gcc-13-base/copyright'),
                       ('mingw-runtime' if win else 'glibc','/usr/share/doc/mingw-w64-common/copyright' if win else '/usr/share/doc/libc6/copyright'),
                       ('GPL-3','/usr/share/common-licenses/GPL-3'),
                       ('LGPL-2.1','/usr/share/common-licenses/LGPL-2.1')]:
        if Path(path).is_file():shutil.copy2(path,licenses/(label+'-LICENSE'))
    (dest/'SHA256SUMS.txt').write_text(hashlib.sha256(binary.read_bytes()).hexdigest()+'  '+binary.name+'\n')
    print('BUILT',binary,flush=True)
