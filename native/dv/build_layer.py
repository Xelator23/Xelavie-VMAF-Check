from pathlib import Path
import json,subprocess
root=Path('/experiment/roi-layer');root.mkdir(exist_ok=True)
headers='/build/ffmpeg-matched/install/include'
for platform,cc,extension,flags in [('linux','gcc','.so',['-fPIC']),('windows','x86_64-w64-mingw32-gcc','.dll',[])]:
    binary=root/('xelavie-roi'+extension)
    subprocess.run([cc,'-std=c11','-O2','-shared',*flags,'-I'+headers,str(root/'roi_layer.c'),'-o',str(binary)],check=True)
    data={'file_format_version':'1.2.0','layer':{'name':'VK_LAYER_Xelavie_ROI','type':'GLOBAL',
         'library_path':'./'+binary.name,'api_version':'1.3.0','implementation_version':'1',
         'description':'Private single-device cropped-output timing experiment'}}
    (root/(platform+'.json')).write_text(json.dumps(data,indent=2))
print('ROI layer builds ready',flush=True)
