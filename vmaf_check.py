#!/usr/bin/env python3
"""Local SDR/PQ/HLG and DV 5/7/8/10 comparison, with explicit P7 scope."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import ssl
import subprocess
import sys
import time
from datetime import datetime
if __package__:
    from .vmaf_settings import work_directory, save_work_directory
else:
    from vmaf_settings import work_directory, save_work_directory
import tarfile
import tempfile
import urllib.request
import urllib.error
import zipfile
from fractions import Fraction

__version__ = '0.1.0-nightly.2'

COLOR_FIELDS = {'primaries':'color_primaries', 'transfer':'color_transfer',
                'matrix':'color_space', 'range':'color_range'}
COLOR_PRESETS = {
    'bt709': dict(color_primaries='bt709',color_transfer='bt709',color_space='bt709',color_range='tv'),
    'hdr10': dict(color_primaries='bt2020',color_transfer='smpte2084',color_space='bt2020nc',color_range='tv'),
    'hlg': dict(color_primaries='bt2020',color_transfer='arib-std-b67',color_space='bt2020nc',color_range='tv'),
}


def color_overrides(args, side):
    preset = getattr(args, side+'_color')
    values = dict(COLOR_PRESETS[preset]) if preset else {}
    for name, field in COLOR_FIELDS.items():
        value = getattr(args,side+'_'+name)
        if value is not None:
            values[field] = {'limited':'tv','full':'pc'}.get(value,value)
    return values


def apply_colors(stream, overrides):
    # Do not alter the original ffprobe snapshot or invent unspecified values.
    effective = dict(stream)
    effective.update(overrides)
    effective['_color_overrides'] = dict(overrides)
    return effective


def color_filter(stream):
    names = {'color_primaries':'color_primaries','color_transfer':'color_trc',
             'color_space':'colorspace','color_range':'range'}
    values = stream.get('_color_overrides',{})
    options = [names[k]+'='+({'tv':'limited','pc':'full'}.get(val,val) if k=='color_range' else val)
               for k,val in values.items()]
    result = 'setparams='+':'.join(options)+',' if options else ''
    if classify(stream) == 'sdr' and stream.get('color_range') == 'pc':
        result += 'scale=in_range=full:out_range=limited,setparams=range=limited,'
    return result


def color_audit(original, effective, overrides):
    return {'detected':{key:original.get(key) for key in COLOR_FIELDS.values()},
            'overrides':overrides,
            'effective':{key:effective.get(key) for key in COLOR_FIELDS.values()},
            'overridden_existing_fields':[key for key,val in overrides.items()
                if original.get(key) not in (None,'unknown','unspecified',val)],
            'interpretation':'User-declared source color metadata; not a color-space conversion.',
            'sdr_full_to_limited':classify(effective)=='sdr' and effective.get('color_range')=='pc'}


def run(cmd, cwd=None):
    p = subprocess.run([str(x) for x in cmd], cwd=cwd, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    if p.returncode:
        raise RuntimeError(p.stderr[-6000:] or p.stdout[-6000:] or str(cmd))
    return p.stdout


def file_sha256(path):
    digest=hashlib.sha256()
    with open(path,'rb') as file:
        for chunk in iter(lambda:file.read(1024*1024),b''): digest.update(chunk)
    return digest.hexdigest()


def certificate_error(exc):
    reason=getattr(exc,'reason',exc)
    return isinstance(reason,ssl.SSLCertVerificationError) or 'CERTIFICATE_VERIFY_FAILED' in str(reason)


def windows_fetch(url,path=None):
    """Use Windows/.NET trust, without disabling HTTPS verification."""
    helper=Path(__file__).with_name('download_windows.ps1')
    shell=shutil.which('powershell.exe')
    if not shell or not helper.is_file():
        raise RuntimeError('Windows-Downloadhilfe fehlt. Gesamtes ZIP entpacken; alternativ VMAF_CA_BUNDLE auf eine vertrauenswuerdige PEM-CA-Datei setzen.')
    download_parent = Path(path).resolve().parent if path else work_directory() / 'Temp'
    download_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='vmaf-download-', dir=download_parent) as directory:
        target=Path(path).resolve() if path else Path(directory)/'response.json'
        command=[shell,'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(helper),
                 '-Url',url,'-Destination',str(target)]
        result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace')
        if result.returncode:
            raise RuntimeError('Auch der Windows-HTTPS-Download ist fehlgeschlagen. Windows-Zertifikate/HTTPS-Proxy pruefen oder VMAF_CA_BUNDLE setzen. TLS wurde nicht deaktiviert.\n'+result.stderr[-2000:])
        if path: return file_sha256(target)
        return json.loads(target.read_text(encoding='utf-8-sig'))


def fetch(url, path=None):
    if not url.startswith('https://'): raise ValueError('Downloads erfordern HTTPS.')
    req = urllib.request.Request(url, headers={'User-Agent': 'local-vmaf-check/1.0'})
    bundle=os.environ.get('VMAF_CA_BUNDLE') or os.environ.get('SSL_CERT_FILE')
    context=ssl.create_default_context(cafile=bundle) if bundle else ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=90, context=context) as response:
            if path:
                with open(path, 'wb') as out: shutil.copyfileobj(response, out)
                return file_sha256(path)
            return json.load(response)
    except (urllib.error.URLError,ssl.SSLError) as exc:
        if not certificate_error(exc): raise
        if platform.system()=='Windows' and not bundle:
            print('Python-Zertifikatspruefung fehlgeschlagen; versuche Windows-HTTPS mit System-Zertifikaten ...',flush=True)
            return windows_fetch(url,path)
        raise RuntimeError('HTTPS-Zertifikatskette nicht vertrauenswuerdig. System-CA/Proxy pruefen oder VMAF_CA_BUNDLE auf eine vertrauenswuerdige PEM-CA-Datei setzen. Zertifikatspruefung bleibt aktiv.') from exc


def unpack(archive, destination):
    """Extract regular files only, never links or paths outside destination."""
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    def target(name):
        p = (destination / name.replace('\\', '/')).resolve()
        if not p.is_relative_to(destination):
            raise RuntimeError('Unsicherer Archivpfad: ' + name)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as z:
            for item in z.infolist():
                if item.is_dir():
                    continue
                if (item.external_attr >> 16) & 0o170000 == 0o120000:
                    raise RuntimeError('Symlink im Download-Archiv.')
                with z.open(item) as src, open(target(item.filename), 'wb') as dst:
                    shutil.copyfileobj(src, dst)
    else:
        with tarfile.open(archive) as t:
            for item in t:
                if item.isdir():
                    continue
                if not item.isfile():
                    raise RuntimeError('Nicht-regulaere Datei im Download-Archiv.')
                with t.extractfile(item) as src, open(target(item.name), 'wb') as dst:
                    shutil.copyfileobj(src, dst)


def download_tools(root, manifest):
    machine = platform.machine().lower()
    arch = '64' if machine in ('amd64', 'x86_64') else 'arm64' if machine in ('arm64', 'aarch64') else None
    system = platform.system()
    if not arch or system not in ('Windows', 'Linux'):
        raise RuntimeError('Auto-Download nur fuer Windows/Linux x64/ARM64. --ffmpeg und --ffprobe angeben.')
    tag = ('win' if system == 'Windows' else 'linux') + arch
    name = f'ffmpeg-master-latest-{tag}-gpl.' + ('zip' if system == 'Windows' else 'tar.xz')
    print('Lade temporaeres FFmpeg-Paket:', name, flush=True)
    release = fetch('https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/tags/latest')
    asset = next((a for a in release['assets'] if a['name'] == name), None)
    if not asset:
        raise RuntimeError('Kein passendes Download-Paket: ' + name)
    url = asset['browser_download_url']
    if not url.startswith('https://github.com/BtbN/FFmpeg-Builds/releases/download/'):
        raise RuntimeError('Unerwartete Download-Quelle.')
    archive = root / name
    sha = fetch(url, archive)
    digest = asset.get('digest')
    if not digest or digest != 'sha256:' + sha:
        raise RuntimeError('SHA256 fehlt in der Release-API oder stimmt nicht ueberein.')
    manifest.append({'url': url, 'sha256': sha, 'verified_release_digest': True})
    unpack(archive, root / 'tools')
    suffix = '.exe' if system == 'Windows' else ''
    result = []
    for tool in ('ffmpeg', 'ffprobe'):
        matches = list((root / 'tools').rglob(tool + suffix))
        if len(matches) != 1:
            raise RuntimeError('Programm im Archiv nicht eindeutig gefunden: ' + tool)
        matches[0].chmod(0o755)
        result.append(str(matches[0]))
    return result


def probe(exe, path):
    data = json.loads(run([exe, '-v', 'error', '-select_streams', 'V:0',
                           '-show_streams', '-show_format', '-of', 'json', path]))
    if len(data.get('streams', [])) != 1:
        raise RuntimeError('Kein Videostream: ' + str(path))
    return data['streams'][0]


def required_filters(ffmpeg, kinds):
    listing = run([ffmpeg, '-hide_banner', '-filters'])
    needed = {'libvmaf','cropdetect','scale'}
    if 'hlg' in kinds: needed.add('zscale')
    if 'dv' in kinds: needed.add('libplacebo')
    missing = [name for name in needed if not re.search(r'\b'+name+r'\b',listing)]
    if missing:
        raise RuntimeError('FFmpeg-Filter fehlen: '+', '.join(sorted(missing)))


def check_dv_frames(ffprobe, path):
    data = json.loads(run([ffprobe,'-v','error','-select_streams','V:0','-read_intervals','%+#8',
                           '-show_frames','-of','json',path]))
    text = json.dumps(data.get('frames',[])).lower()
    if 'dolby vision metadata' not in text and 'dovi metadata' not in text:
        raise RuntimeError('Decoder liefert in der DV-Vorabprobe keine dekodierten Dolby-Vision-Metadaten: '+str(path))


def dv_config(s):
    return next((d for d in s.get('side_data_list', []) if 'dv_profile' in d), None)


def dv_plan(streams, requested='auto'):
    profiles = [(dv_config(s) or {}).get('dv_profile') for s in streams]
    has7 = 7 in profiles
    mode = ('compatible' if has7 else 'rendered') if requested == 'auto' else requested
    if has7 and mode == 'rendered':
        raise RuntimeError('Profil 7: Vollstaendige EL-Rekonstruktion nicht implementiert. --dv-mode compatible oder base-layer verwenden; Ergebnis ist eingeschraenkt.')
    if mode == 'base-layer':
        for s in streams:
            c = dv_config(s)
            if c and not (c.get('dv_profile') == 7 or
                          (c.get('dv_profile') in (8,10) and c.get('dv_bl_signal_compatibility_id') == 1)):
                raise RuntimeError('HDR10-Basisschicht-Modus erfordert P7, P8.1, P10.1 oder normales HDR10 auf BEIDEN Seiten. Fuer andere Profile compatible verwenden.')
            if any(s.get(k) != val for k,val in [('color_transfer','smpte2084'),('color_primaries','bt2020'),('color_space','bt2020nc')]):
                raise RuntimeError('Basisschicht-Modus erfordert explizite PQ/BT.2020-Metadaten auf beiden Seiten.')
    return {'requested': requested, 'mode': mode, 'original_profiles': profiles,
            'scope': ('HDR10 base pictures only; no DV RPU or enhancement layer' if mode == 'base-layer' else
                      'Compatibility reconstruction: P7 converted to P8.1, enhancement layer discarded' if has7 else
                      'Single-layer DV reconstruction to PQ; not a Dolby display certification' if any(profiles) else
                      'SDR/HDR picture comparison; no Dolby Vision inputs'),
            'full_profile7_reconstruction': False,
            'profile7_conversion': has7 and mode == 'compatible'}


def profile7_sample(ffprobe, path):
    """Residual flags are diagnostic samples, never a full-film MEL certificate."""
    try:
        data = json.loads(run([ffprobe,'-v','error','-select_streams','V:0','-read_intervals','%+#32',
                               '-show_frames','-of','json',path]))
        flags = []
        def walk(value):
            if isinstance(value,dict):
                if 'disable_residual_flag' in value: flags.append(value['disable_residual_flag'])
                for child in value.values(): walk(child)
            elif isinstance(value,list):
                for child in value: walk(child)
        walk(data)
        return {'sample_packets':32,'disable_residual_flags':sorted(set(flags)),
                'full_film_mel_fel_classification':'not_determined',
                'note':'Residual enabled in a sample indicates FEL-like data; absence does not certify MEL for the whole film.'}
    except (RuntimeError,ValueError) as exc:
        return {'full_film_mel_fel_classification':'not_determined','diagnostic_error':str(exc)[-500:]}


def required_bsfs(ffmpeg, streams, mode):
    needed = set()
    for s in streams:
        c = dv_config(s)
        if not c: continue
        if mode == 'base-layer':
            needed.add('dovi_rpu')
            if s.get('codec_name') == 'hevc': needed.update(('hevc_mp4toannexb','filter_units'))
        elif c['dv_profile'] == 7:
            needed.add('hevc_mp4toannexb')
    if not needed: return
    available = run([ffmpeg,'-hide_banner','-bsfs'])
    missing = [name for name in needed if not re.search(r'\b'+name+r'\b',available)]
    if missing: raise RuntimeError('Bitstreamfilter fehlen: '+', '.join(missing))


def download_dovi(root, manifest):
    machine = platform.machine().lower()
    arch = 'x86_64' if machine in ('amd64','x86_64') else 'aarch64' if machine in ('arm64','aarch64') else None
    target = 'pc-windows-msvc.zip' if os.name == 'nt' else 'unknown-linux-musl.tar.gz'
    if not arch: raise RuntimeError('Kein dovi_tool-Download fuer diese Architektur.')
    release = fetch('https://api.github.com/repos/quietvoid/dovi_tool/releases/latest')
    asset = next((a for a in release['assets'] if a['name'].endswith(arch+'-'+target)),None)
    if not asset: raise RuntimeError('Kein passendes dovi_tool-Release-Archiv gefunden.')
    url = asset['browser_download_url']
    if not url.startswith('https://github.com/quietvoid/dovi_tool/releases/download/'):
        raise RuntimeError('Unerwartete dovi_tool-Downloadquelle.')
    archive = root / asset['name']
    sha = fetch(url,archive)
    if asset.get('digest') != 'sha256:'+sha:
        raise RuntimeError('dovi_tool SHA256 fehlt oder stimmt nicht.')
    manifest.append({'url':url,'sha256':sha,'verified_release_digest':True})
    unpack(archive,root/'dovi')
    candidates = list((root/'dovi').rglob('dovi_tool.exe' if os.name == 'nt' else 'dovi_tool'))
    if len(candidates) != 1: raise RuntimeError('dovi_tool im Archiv nicht eindeutig.')
    candidates[0].chmod(0o755)
    return str(candidates[0])


def logged(cmd, log):
    with open(log,'w',encoding='utf-8') as file:
        p = subprocess.Popen([str(x) for x in cmd],stdout=file,stderr=subprocess.STDOUT)
        try:
            code = p.wait()
        except BaseException:
            p.kill(); p.wait(); raise
    if code: raise RuntimeError('Vorbereitung fehlgeschlagen: '+str(log)+'\n'+Path(log).read_text(encoding='utf-8',errors='replace')[-3000:])


def prepare_dv(ffmpeg, ffprobe, path, stream, mode, dovi, root, output, name, fps):
    c = dv_config(stream)
    if not c or (c['dv_profile'] != 7 and mode != 'base-layer'):
        return path, stream, None
    result = root / (name+'-prepared.mkv')
    # No shell pipelines: separate argument lists and binary stdout handles.
    if mode == 'compatible':
        raw = root / (name+'-p81.hevc')
        decode = [ffmpeg,'-hide_banner','-nostdin','-v','error','-i',str(path),'-map','0:V:0',
                  '-c:v','copy','-bsf:v','hevc_mp4toannexb','-f','hevc','-']
        convert = [dovi,'-m','2','convert','--discard','-','-o',str(raw)]
        with open(output/(name+'-extract.log'),'w') as err, open(output/(name+'-convert.log'),'w') as log:
            producer = subprocess.Popen(decode,stdout=subprocess.PIPE,stderr=err)
            consumer = None
            try:
                consumer = subprocess.Popen(convert,stdin=producer.stdout,stdout=log,stderr=subprocess.STDOUT)
                producer.stdout.close()
                converted = consumer.wait()
                extracted = producer.wait()
                if converted or extracted:
                    raise RuntimeError('P7->P8.1 Vorbereitung fehlgeschlagen; siehe '+str(output))
            finally:
                for p in (consumer,producer):
                    if p and p.poll() is None: p.kill(); p.wait()
        logged([ffmpeg,'-hide_banner','-nostdin','-v','error','-r',str(fps),'-i',raw,
                '-map','0:v:0','-c:v','copy',result],output/(name+'-remux.log'))
        raw.unlink()
    else:
        filters = 'dovi_rpu=strip=1'
        if stream.get('codec_name') == 'hevc':
            filters = 'hevc_mp4toannexb,filter_units=remove_types=62|63,'+filters
        logged([ffmpeg,'-hide_banner','-nostdin','-v','error','-i',path,'-map','0:V:0',
                '-c:v','copy','-bsf:v',filters,result],output/(name+'-base-layer.log'))
    info = probe(ffprobe,result)
    new_config = dv_config(info)
    if mode == 'compatible':
        if not new_config or new_config.get('dv_profile') != 8 or new_config.get('dv_bl_signal_compatibility_id') != 1 or new_config.get('el_present_flag',0):
            raise RuntimeError('P7-Vorbereitung hat kein nachweisbares Single-Layer-Profil 8.1 erzeugt.')
    elif new_config:
        raise RuntimeError('Basisschicht-Vorbereitung enthaelt noch DV-Signalisierung.')
    if (stream['width'],stream['height']) != (info['width'],info['height']):
        raise RuntimeError('Vorbereitung hat die Bildabmessungen veraendert.')
    return result,info,{'operation': 'p7_to_p81_discard_el' if mode == 'compatible' else 'strip_dv_and_el',
                       'original':str(path),'prepared':str(result),'reencoded':False}


def classify(s):
    side = json.dumps(s.get('side_data_list', [])).lower()
    if 'dovi' in side or 'dolby vision' in side:
        config = dv_config(s) or {}
        profile = config.get('dv_profile')
        if profile not in (5,7,8,10) or (profile != 7 and config.get('el_present_flag',0)):
            raise RuntimeError('Unterstuetzte DV-Profile: 5, 7 (Vorbereitung), 8, 10. Unbekannte/weitere Mehrschicht-Profile werden abgelehnt.')
        if profile == 10 and s.get('codec_name') != 'av1':
            raise RuntimeError('DV Profil 10 erfordert einen AV1-Videostream.')
        if profile == 7 and s.get('codec_name') != 'hevc':
            raise RuntimeError('DV Profil 7 erfordert einen HEVC-Videostream.')
        if not config.get('rpu_present_flag'):
            raise RuntimeError('Dolby Vision ohne nachgewiesene RPU-Metadaten.')
        return 'dv7' if profile == 7 else 'dv'
    if s.get('color_transfer') == 'arib-std-b67':
        if s.get('color_primaries') != 'bt2020' or s.get('color_space') != 'bt2020nc' or s.get('color_range') not in ('tv','pc'):
            raise RuntimeError('HLG benoetigt vollstaendige BT.2020/BT.2020nc/Range-Metadaten.')
        return 'hlg'
    if s.get('color_transfer') == 'smpte2084':
        if (s.get('color_primaries') != 'bt2020' or s.get('color_space') != 'bt2020nc'
                or s.get('color_range') not in ('tv', 'pc')):
            raise RuntimeError('HDR benoetigt vollstaendige PQ/BT.2020/BT.2020nc/Range-Metadaten.')
        return 'hdr'
    if s.get('color_transfer') != 'bt709' or s.get('color_primaries') != 'bt709' or s.get('color_space') != 'bt709':
        raise RuntimeError('SDR benoetigt explizite BT.709-Metadaten. Fehlende Tags werden nicht geraten.')
    if s.get('color_range') not in ('tv','pc'):
        raise RuntimeError('SDR benoetigt Limited/Full-Range-Metadaten. --ref-range/--enc-range verwenden, wenn bekannt.')
    return 'sdr'


def validate_pair(ref, enc):
    kind = classify(ref)
    if (kind == 'sdr') != (classify(enc) == 'sdr'):
        raise RuntimeError('Referenz und Encode muessen beide SDR oder beide HDR sein.')
    for s in (ref, enc):
        if s['width'] % 2 or s['height'] % 2:
            raise RuntimeError('Gerade Bildabmessungen erforderlich.')
        if s.get('sample_aspect_ratio', '1:1') not in ('1:1', 'N/A'):
            raise RuntimeError('Anamorphes Material zuerst auf quadratische Pixel normalisieren.')
    if any(s.get('field_order', 'progressive') not in ('progressive', 'unknown') for s in (ref, enc)):
        raise RuntimeError('Interlaced-Video zuerst einheitlich deinterlacen.')
    fps = Fraction(ref['avg_frame_rate'])
    if fps <= 0 or fps != Fraction(enc['avg_frame_rate']):
        raise RuntimeError('Unterschiedliche/ungueltige Bildraten.')
    for s in (ref, enc):
        if Fraction(s['r_frame_rate']) != fps:
            raise RuntimeError('VFR oder uneindeutige Bildrate. Dieses Script setzt CFR voraus.')
    return 'sdr' if kind == 'sdr' else 'hdr', fps


def geometry(ref, enc, crop_ref, crop_enc=None):
    """Match active image regions, then use encoded active dimensions as target."""
    r = crop_ref or (ref['width'], ref['height'], 0, 0)
    same_canvas = abs(ref['width']/ref['height'] - enc['width']/enc['height']) < .002
    if crop_enc is not None:
        e = crop_enc
    elif same_canvas:
        sx, sy = enc['width']/ref['width'], enc['height']/ref['height']
        e = tuple(round(v * (sx if i in (0,2) else sy)/2)*2 for i,v in enumerate(r))
    else:
        e = (enc['width'], enc['height'], 0, 0)
    for rect, s in ((r,ref),(e,enc)):
        parse_crop(':'.join(map(str,rect)),s['width'],s['height'])
    if abs((r[0]/r[1])/(e[0]/e[1])-1) > .005:
        raise RuntimeError(f'Aktive Bildausschnitte passen nicht: Referenz {r[0]}x{r[1]} bei {r[2]}:{r[3]} (AR {r[0]/r[1]:.4f}), Encode {e[0]}x{e[1]} bei {e[2]}:{e[3]} (AR {e[0]/e[1]:.4f}). Auto-Erkennung unten/oben im Protokoll pruefen; bei Bedarf --crop/--crop-encode manuell setzen. Es wird nicht gestreckt.')
    return {'ref': r, 'enc': e, 'target': e[:2],
            'ref_color_filter':color_filter(ref), 'enc_color_filter':color_filter(enc),
            'ref_kind': classify(ref), 'enc_kind': classify(enc)}


def normalization(kind):
    if kind == 'dv7':
        raise RuntimeError('Profil 7 muss vor der Bewertung explizit vorbereitet werden.')
    if kind == 'hlg':
        # zimg HLG display-referred conversion, fixed nominal peak 1000 cd/m2.
        return ('zscale=t=linear:npl=1000,format=gbrpf32le,'
                'zscale=p=bt2020:t=smpte2084:m=bt2020nc:r=limited:npl=1000,'
                'format=yuv420p10le,')
    if kind == 'dv':
        return ('libplacebo=apply_dolbyvision=1:colorspace=bt2020nc:'
                'color_primaries=bt2020:color_trc=smpte2084:range=tv:'
                'format=yuv420p10le:peak_detect=0:tonemapping=clip,')
    return ''


def automatic_frame_count(exe, path, stream):
    """Use explicit video counts; duration multiplied by fps is not exact."""
    candidates = []
    raw = [('nb_frames', stream.get('nb_frames'))]
    raw.extend((key, value) for key, value in stream.get('tags', {}).items()
               if key.upper() == 'NUMBER_OF_FRAMES' or key.upper().startswith('NUMBER_OF_FRAMES-'))
    invalid = False
    for key, value in raw:
        if value is None or str(value).strip().upper() in ('', 'N/A'):
            continue
        text = str(value).strip()
        if not re.fullmatch(r'[0-9]+', text) or int(text) <= 0:
            invalid = True
        else:
            candidates.append((key, int(text)))
    if candidates and not invalid and len({n for _, n in candidates}) == 1:
        count = candidates[0][1]
        source = ', '.join(key for key, _ in candidates)
        print(f'Frameanzahl aus Videometadaten: {path.name}: {count} ({source})', flush=True)
        return count, {'method': 'metadata', 'source': source, 'count': count}
    print(f'Keine eindeutige Frameanzahl in Videometadaten: {path.name}; starte vollstaendigen Scan ...', flush=True)
    count = count_frames(exe, path)
    if count <= 0:
        raise RuntimeError('Keine Frames gefunden: ' + str(path))
    return count, {'method': 'scan', 'count': count}


def count_frames(exe, path):
    print('Pruefe vollstaendige Frameanzahl:', path.name, flush=True)
    d = json.loads(run([exe, '-v', 'error', '-select_streams', 'V:0', '-count_frames',
                       '-show_entries', 'stream=nb_read_frames', '-of', 'json', path]))
    return int(d['streams'][0]['nb_read_frames'])


def detect_crop(ffmpeg, ffprobe, ref, stream):
    width, height = stream['width'], stream['height']
    # cropdetect compares code values, not black-relative brightness. Limited
    # black is 16/255 (8 bit), so 0.06 incorrectly treats black bars as content.
    # SDR full-range, HLG and DV are normalized to limited before detection.
    full_pq = classify(stream)=='hdr' and stream.get('color_range')=='pc'
    black_limit = 8/255 if full_pq else 24/255
    try:
        duration = float(stream['duration'])
    except (KeyError, ValueError):
        duration = float(run([ffprobe,
                              '-v', 'error', '-show_entries', 'format=duration', '-of',
                              'default=noprint_wrappers=1:nokey=1', ref]).strip())
    if not math.isfinite(duration) or duration < 1:
        return None, {'reason': 'Keine verlaessliche Dauer; kein Auto-Crop.'}
    rects = []
    samples = []
    skipped = []
    positions = (.05, .20, .35, .50, .65, .80, .95, .10, .275, .425, .575, .725, .90)
    for index,part in enumerate(positions):
        if index >= 7 and len(samples) >= 3:
            break
        start = max(0, min(duration * part, duration - 1))
        cmd = [ffmpeg, '-hide_banner', '-nostdin', '-v', 'info', '-ss', str(start), '-i', str(ref),
               '-t', str(min(3, duration-start)), '-map', '0:V:0', '-an', '-sn',
               '-vf', color_filter(stream) + normalization(classify(stream)) + f'cropdetect=limit={black_limit:.9f}:round=2:reset=0', '-f', 'null', '-']
        p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        if p.returncode:
            raise RuntimeError('Crop-Erkennung fehlgeschlagen: ' + p.stderr[-2000:])
        found = re.findall(r'crop=(\d+):(\d+):(\d+):(\d+)', p.stderr)
        valid = []
        for item in found:
            w, h, x, y = map(int, item)
            # Reject black/title frames suggesting implausibly tiny content.
            if w >= width * .5 and h >= height * .5 and x+w <= width and y+h <= height:
                valid.append((w, h, x, y))
        if not valid:
            skipped.append({'seconds':start,'reason':'Keine plausible Bildflaeche in dieser Stichprobe.'})
            print(f'  Crop {ref.name}: {start:.1f}s uneindeutig, uebersprungen.',flush=True)
            continue
        rects.extend(valid)
        samples.append({'seconds': start, 'last_detected': valid[-1]})
    if len(samples) < 3:
        return None, {'reason':f'Nur {len(samples)} brauchbare Stichproben nach {len(samples)+len(skipped)} Versuchen; mindestens 3 erforderlich.',
                      'samples':samples,'skipped':skipped,'black_limit':black_limit}
    crop = union_crop(rects, width, height)
    print(f'  Crop {ref.name}: {len(samples)} brauchbare Stichproben, {len(skipped)} uebersprungen.',flush=True)
    return crop, {'samples': samples, 'skipped':skipped, 'rectangle': crop, 'black_limit':black_limit,
                  'method': 'Union plausibler Erkennungen; 7 Grundpositionen, bei Bedarf bis zu 6 Zusatzpositionen; mindestens 3 brauchbare Stichproben.'}


def union_crop(rects, width, height):
    x = min(r[2] for r in rects) // 2 * 2
    y = min(r[3] for r in rects) // 2 * 2
    right = min(width, math.ceil(max(r[2]+r[0] for r in rects)/2)*2)
    bottom = min(height, math.ceil(max(r[3]+r[1] for r in rects)/2)*2)
    return (right-x, bottom-y, x, y)


def parse_crop(value, width, height):
    try:
        w, h, x, y = map(int, value.split(':'))
    except ValueError:
        raise RuntimeError('Crop-Format: BREITE:HOEHE:X:Y, auto oder none')
    if min(w, h) <= 0 or min(x, y) < 0 or x+w > width or y+h > height or any(v % 2 for v in (w,h,x,y)):
        raise RuntimeError('Crop muss innerhalb des Bildes liegen und gerade Werte verwenden.')
    return w, h, x, y


def graph(fps, step, threads, hdr, limit=None, crop=None, display='1080'):
    if isinstance(crop, dict):
        chains = []
        for index, key, label in ((0,'enc','dist'),(1,'ref','ref')):
            pre = f'trim=end_frame={limit},' if limit else ''
            pre += crop.get(key+'_color_filter','')
            pre += normalization(crop[key+'_kind'])
            pre += 'crop=' + ':'.join(map(str,crop[key])) + ','
            w,h = crop['target']
            pre += f'scale={w}:{h}:flags=bicubic,setsar=1,settb=AVTB,setpts=N/({fps.numerator}/{fps.denominator}*TB),format=yuv420p10le'
            chains.append(f'[{index}:V:0]{pre}[{label}];')
        return ''.join(chains) + (f'[dist][ref]libvmaf=model=path=model.json:log_fmt=json:log_path=scores.json:'
                                 f'n_threads={threads}:n_subsample={step}:shortest=1:repeatlast=0[out]')
    # Reset to frame-index time only after equal CFR and frame counts were checked.
    pre = (f'trim=end_frame={limit},' if limit else '')
    if crop:
        pre += 'crop=' + ':'.join(map(str, crop)) + ','
    # Keep the cropped image at native resolution; do not stretch a letterboxed
    # scope movie to 16:9. SDR scales width to the selected landscape display.
    if not hdr:
        width = 3840 if display == '2160' else 1920
        pre += f'scale={width}:-2:flags=bicubic,'
    pre += f'settb=AVTB,setpts=N/({fps.numerator}/{fps.denominator}*TB),format=yuv420p10le'
    return (f'[0:V:0]{pre}[dist];[1:V:0]{pre}[ref];'
            f'[dist][ref]libvmaf=model=path=model.json:log_fmt=json:log_path=scores.json:'
            f'n_threads={threads}:n_subsample={step}:shortest=1:repeatlast=0[out]')


def evaluate(ffmpeg, ref, enc, fps, step, threads, hdr, root, log, limit=None, crop=None, display='1080'):
    cmd = [ffmpeg, '-hide_banner', '-nostdin', '-xerror', '-v', 'warning', '-i', str(enc), '-i', str(ref),
           '-filter_complex', graph(fps, step, threads, hdr, limit, crop, display),
           '-map', '[out]', '-an', '-sn', '-dn', '-f', 'null', '-']
    with open(log, 'w', encoding='utf-8') as out:
        if not limit:
            cmd[1:1] = ['-progress', 'pipe:1', '-stats_period', '1', '-nostats']
        p = subprocess.Popen(cmd, cwd=root, stdout=subprocess.PIPE if not limit else subprocess.DEVNULL,
                             stderr=out, text=True, encoding='utf-8', errors='replace')
        try:
            if not limit:
                for line in p.stdout:
                    key, _, value = line.strip().partition('=')
                    if key == 'frame' and value.strip().isdigit():
                        print('VMAF_PROGRESS ' + json.dumps({'frame': int(value)}), flush=True)
                p.stdout.close()
            code = p.wait()
        except BaseException:
            p.terminate()
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
            raise
    if code:
        raise RuntimeError('FFmpeg fehlgeschlagen. ' + str(log) + '\n' + Path(log).read_text(encoding='utf-8')[-4000:])
    return cmd


def check_hdr_conversion(ffmpeg, root, threads):
    # An old library must not silently interpret an HDR model as an SDR model.
    cmd = [ffmpeg, '-hide_banner', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
           'color=size=1920x1080:rate=24,format=yuv420p10le', '-filter_complex',
           f'[0:v]trim=end_frame=2,split[a][b];[a][b]libvmaf=model=path=model.json:n_threads={threads}[o]',
           '-map', '[o]', '-f', 'null', '-']
    p = subprocess.run(cmd, cwd=root, capture_output=True, text=True, encoding='utf-8', errors='replace')
    msg = p.stderr.lower()
    if p.returncode == 0 or not any(x in msg for x in ('color', 'conversion', 'zimg')):
        raise RuntimeError('HDR-Konvertierung nicht nachgewiesen. Aktuelles FFmpeg/libvmaf mit zimg erforderlich.\n' + p.stderr[-2000:])


def duration_text(seconds):
    seconds = max(0, int(seconds))
    return f'{seconds//3600:02d}:{seconds//60%60:02d}:{seconds%60:02d}'


def print_report(summary):
    timing = summary['timing']
    line = '=' * 70
    count = lambda n: f'{n:,}'.replace(',', '.')
    print('\n' + line + '\n  XELAVIE VMAF CHECK - PRUEFBERICHT\n' + line)
    for label, value in (
            ('Datum', summary['completed_at']),
            ('Ziel-Encode', Path(summary['encoded']).name),
            ('Remux-Quelle', Path(summary['reference']).name),
            ('Umfang', f"Kompletter Film - {summary['percent']} % der Frames bewertet"),
            ('Vergleich', summary['dv_comparison']['scope'])):
        print(f'  {label + ":":22s} {value}')
    print(line + '\n  ERGEBNIS DER VMAF-ANALYSE\n' + line)
    for label, value in (
            ('VMAF Score', f"{summary['mean']:.6f}"),
            ('Durchschn. FPS', f"{timing['measurement_fps']:.2f} (nur Messung)"),
            ('Messzeit', duration_text(timing['measurement_seconds'])),
            ('Vorbereitung', duration_text(timing['preparation_seconds'])),
            ('Laufzeit (Job)', duration_text(timing['job_seconds'])),
            ('Frames verarbeitet', f"{count(summary['total_frames'])} / {count(summary['total_frames'])}"),
            ('Frames bewertet', f"{count(summary['scored_frames'])} / {count(len(range(0, summary['total_frames'], summary['subsample'])))}")):
        print(f'  {label + ":":22s} {value}')
    print(line)


def main():
    job_started = time.monotonic()
    ap = argparse.ArgumentParser(description='Lokaler VMAF-Vergleich: SDR, HDR10/PQ, HLG, DV 5/7/8/10; Encode-Aufloesung automatisch.')
    ap.add_argument('--version', action='version', version='Xelavie VMAF Check '+__version__)
    ap.add_argument('reference', type=Path, help='Original/Referenz')
    ap.add_argument('encoded', type=Path, help='Zu pruefender Encode')
    ap.add_argument('--percent', type=int, choices=(100, 50, 25), default=100)
    ap.add_argument('--display', choices=('auto', '1080', '2160'), default='auto', help='Modell automatisch aus Encode-Aufloesung (Standard)')
    ap.add_argument('--threads', type=int, default=min(16, os.cpu_count() or 1))
    ap.add_argument('--ffmpeg', help='Pfad zu FFmpeg')
    ap.add_argument('--ffprobe', help='Pfad zu FFprobe')
    ap.add_argument('--dovi-tool', help='Optionaler lokaler Pfad; sonst automatischer Download bei P7-Konvertierung')
    ap.add_argument('--dv-mode', choices=('auto','compatible','rendered','base-layer'), default='auto',
                    help='auto: P7 als Kompatibilitaetsvergleich, sonst rendered; base-layer: gemeinsame HDR10-Basis')
    ap.add_argument('--model', type=Path, help='Lokales JSON-Modell, passend zu SDR/HDR')
    ap.add_argument('--crop', default='auto', help='auto (Standard), none oder Referenz-Crop BREITE:HOEHE:X:Y; proportional auf Encode uebertragen')
    ap.add_argument('--crop-encode', help='Optionaler manueller Encode-Crop BREITE:HOEHE:X:Y')
    ap.add_argument('--no-download', action='store_true', help='Keine Netzwerkzugriffe; --model notwendig')
    ap.add_argument('--download-tools', action='store_true', help='Aktuelles temporaeres FFmpeg statt lokalem Build')
    ap.add_argument('--temp-dir', type=Path, help='Elternordner fuer temporaere Downloads')
    ap.add_argument('--output', type=Path, help='Optionaler Ergebnis-Elternordner (ueberschreibt Arbeitsordner)')
    ap.add_argument('--work-dir', type=Path, help='Gemeinsamer Arbeitsordner; wird fuer CLI und UI gespeichert')
    for side, label in (('ref','Referenz'),('enc','Encode')):
        ap.add_argument('--'+side+'-color',choices=tuple(COLOR_PRESETS),help=label+': explizites Farb-Preset (Limited Range)')
        ap.add_argument('--'+side+'-primaries',choices=('bt709','bt2020'),help=label+': Quell-Primaerfarben')
        ap.add_argument('--'+side+'-transfer',choices=('bt709','smpte2084','arib-std-b67'),help=label+': Quell-Transferfunktion')
        ap.add_argument('--'+side+'-matrix',choices=('bt709','bt2020nc'),help=label+': Quell-Farbmatrix')
        ap.add_argument('--'+side+'-range',choices=('limited','full'),help=label+': Quell-Wertebereich')
    args = ap.parse_args()
    ref_colors, enc_colors = color_overrides(args,'ref'), color_overrides(args,'enc')
    if args.threads < 1:
        ap.error('--threads muss positiv sein')
    if args.no_download and args.download_tools:
        ap.error('--no-download und --download-tools widersprechen sich')
    ref, enc = args.reference.resolve(strict=True), args.encoded.resolve(strict=True)
    original_ref, original_enc = ref, enc
    if not ref.is_file() or not enc.is_file():
        ap.error('Beide Eingaben muessen Dateien sein')
    if args.work_dir:
        # A queued job retains its own directory without resetting the UI's
        # preference when an older job eventually starts.
        work = args.work_dir.expanduser().resolve() if os.environ.get('VMAF_UI')=='1' else save_work_directory(str(args.work_dir))
    else:
        work = work_directory()
    if args.output is None:
        film = re.sub(r'[^\w .-]', '_', enc.stem).strip(' .')[:100] or 'Film'
        args.output = work / 'Ergebnisse' / film
        prefix = datetime.now().strftime('%Y-%m-%d_%H-%M-%S_')
    else:
        prefix = 'run-'
    args.temp_dir = args.temp_dir or work / 'Temp'
    args.output.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix=prefix, dir=args.output.resolve()))
    args.temp_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    with tempfile.TemporaryDirectory(prefix='vmaf-check-', dir=args.temp_dir) as temp:
        root = Path(temp).resolve()
        ffmpeg = shutil.which(args.ffmpeg or 'ffmpeg')
        ffprobe = shutil.which(args.ffprobe or 'ffprobe')
        if args.download_tools or not ffmpeg or not ffprobe:
            if args.no_download:
                raise RuntimeError('FFmpeg/FFprobe fehlen und Downloads sind deaktiviert.')
            ffmpeg, ffprobe = download_tools(root, manifest)
        info_ref, info_enc = probe(ffprobe, ref), probe(ffprobe, enc)
        original_info_ref, original_info_enc = info_ref, info_enc
        info_ref, info_enc = apply_colors(info_ref,ref_colors), apply_colors(info_enc,enc_colors)
        if ref_colors or enc_colors:
            print('Manuelle Quell-Farbangaben: Referenz',ref_colors,'Encode',enc_colors,flush=True)
        colors_report = {'reference':color_audit(original_info_ref,info_ref,ref_colors),
                         'encoded':color_audit(original_info_enc,info_enc,enc_colors)}
        if args.display == 'auto':
            args.display = '2160' if info_enc['width'] > 2560 or info_enc['height'] > 1440 else '1080'
        kind, fps = validate_pair(info_ref, info_enc)
        hdr = kind == 'hdr'
        dv_comparison = dv_plan([info_ref,info_enc],args.dv_mode)
        print('Vergleich:',dv_comparison['mode'],'-',dv_comparison['scope'],flush=True)
        kinds = ['hdr','hdr'] if dv_comparison['mode'] == 'base-layer' else [
            'dv' if classify(s) == 'dv7' else classify(s) for s in (info_ref,info_enc)]
        def check_tools():
            required_filters(ffmpeg,kinds)
            required_bsfs(ffmpeg,[info_ref,info_enc],dv_comparison['mode'])
        try:
            check_tools()
        except RuntimeError:
            if args.no_download or any('BtbN/' in item['url'] for item in manifest): raise
            ffmpeg,ffprobe = download_tools(root,manifest)
            check_tools()
        dovi = None
        if dv_comparison['profile7_conversion']:
            dovi = shutil.which(args.dovi_tool or 'dovi_tool')
            if not dovi:
                if args.no_download: raise RuntimeError('Profil-7-Konvertierung benoetigt dovi_tool; Download deaktiviert.')
                dovi = download_dovi(root,manifest)
            dv_comparison['dovi_tool_version'] = run([dovi,'--version']).strip()
        preparation = []
        to_prepare = [(p,s) for p,s in ((ref,info_ref),(enc,info_enc)) if dv_config(s) and
                      (dv_comparison['mode']=='base-layer' or (dv_config(s) or {}).get('dv_profile')==7)]
        if to_prepare:
            required_space = 2*sum(p.stat().st_size for p,s in to_prepare)+1024**3
            if shutil.disk_usage(root).free < required_space:
                raise RuntimeError(f'Fuer temporaere komprimierte DV-Arbeitskopien werden konservativ {required_space/1024**3:.1f} GiB frei benoetigt. --temp-dir verwenden.')
            print('Erzeuge temporaere komprimierte DV-Arbeitskopien (keine Neukodierung) ...',flush=True)
        for label,path,s in (('reference',ref,info_ref),('encoded',enc,info_enc)):
            if (dv_config(s) or {}).get('dv_profile') == 7:
                dv_comparison[label+'_p7_sample'] = profile7_sample(ffprobe,path)
        ref,info_ref,ref_preparation = prepare_dv(ffmpeg,ffprobe,ref,info_ref,dv_comparison['mode'],dovi,root,output,'reference',fps)
        enc,info_enc,enc_preparation = prepare_dv(ffmpeg,ffprobe,enc,info_enc,dv_comparison['mode'],dovi,root,output,'encoded',fps)
        info_ref, info_enc = apply_colors(info_ref,ref_colors), apply_colors(info_enc,enc_colors)
        preparation = [p for p in (ref_preparation,enc_preparation) if p]
        kind, prepared_fps = validate_pair(info_ref,info_enc)
        if prepared_fps != fps: raise RuntimeError('DV-Vorbereitung hat die Bildrate veraendert.')
        kinds = [classify(info_ref),classify(info_enc)]
        for path, input_kind in zip((ref,enc),kinds):
            if input_kind == 'dv': check_dv_frames(ffprobe,path)
        if info_ref['width'] < info_ref['height']:
            raise RuntimeError('Diese Film-Version setzt Querformat voraus.')
        crop, crop_info = None, {'method': 'none'}
        if args.crop == 'auto':
            print('Suche schwarze Balken an 7 Stellen der Referenz (bei Bedarf bis zu 13) ...', flush=True)
            crop, crop_info = detect_crop(ffmpeg, ffprobe, ref, info_ref)
            print('Auto-Crop Referenz:',crop or 'kein sicherer Ausschnitt',crop_info.get('reason',''),flush=True)
        elif args.crop != 'none':
            crop = parse_crop(args.crop, info_ref['width'], info_ref['height'])
            crop_info = {'method': 'manual', 'rectangle': crop}
        crop_enc = None
        if args.crop_encode:
            crop_enc = parse_crop(args.crop_encode,info_enc['width'],info_enc['height'])
        elif args.crop == 'auto' and abs(info_ref['width']/info_ref['height']-info_enc['width']/info_enc['height']) >= .002:
            crop_enc, enc_crop_info = detect_crop(ffmpeg,ffprobe,enc,info_enc)
            crop_info['encode_detection'] = enc_crop_info
            print('Auto-Crop Encode:',crop_enc or 'kein sicherer Ausschnitt',enc_crop_info.get('reason',''),flush=True)
        crop = geometry(info_ref,info_enc,crop,crop_enc)
        crop_info['alignment'] = crop
        print('Referenz-Crop:', crop['ref'], 'Encode-Crop:', crop['enc'], 'Pruefraster:', crop['target'], 'Modell:', args.display, flush=True)
        if args.model:
            shutil.copyfile(args.model.resolve(strict=True), root / 'model.json')
            model_source = str(args.model.resolve())
        else:
            if args.no_download:
                raise RuntimeError('--no-download erfordert --model DATEI.json')
            if hdr:
                suffix = '1d5h_2160' if args.display == '2160' else '3d0h'
                rel = f'hdr_vmaf_v1.1.8/hdr_vmaf_v1.1.8_{suffix}.json'
            else:
                rel = 'vmaf_4k_v0.6.1.json' if args.display == '2160' else 'vmaf_v0.6.1.json'
            model_source = 'https://raw.githubusercontent.com/Netflix/vmaf/master/model/' + rel
            print('Lade temporaeres Modell:', rel, flush=True)
            sha = fetch(model_source, root / 'model.json')
            manifest.append({'url': model_source, 'sha256': sha})
        model = json.loads((root / 'model.json').read_text(encoding='utf-8'))
        # Search nested structures because model layouts differ between versions.
        is_hdr_model = '"conversion_target"' in json.dumps(model)
        if hdr != is_hdr_model:
            raise RuntimeError('Modelltyp passt nicht: HDR verlangt conversion_target; SDR ein SDR-Modell.')
        def preflight():
            if hdr:
                check_hdr_conversion(ffmpeg, root, args.threads)
            print('Teste Modell und Decoder mit den ersten 8 Frames ...', flush=True)
            evaluate(ffmpeg, ref, enc, fps, 1, args.threads, hdr, root, output / 'preflight.log', 8, crop, args.display)
        try:
            preflight()
        except RuntimeError:
            if args.no_download or any('BtbN/' in item['url'] for item in manifest):
                raise
            print('Lokaler Build besteht Vorabtest nicht. Lade aktuelles portables Paket ...',flush=True)
            ffmpeg,ffprobe = download_tools(root,manifest)
            preflight()
        pre = json.loads((root / 'scores.json').read_text())
        if not pre.get('frames'):
            raise RuntimeError('Vorabtest erzeugt keine Frame-Ergebnisse.')
        nr, ref_count_report = automatic_frame_count(ffprobe, ref, info_ref)
        ne, enc_count_report = automatic_frame_count(ffprobe, enc, info_enc)
        frame_check = {'reference': ref_count_report, 'encoded': enc_count_report}
        for label,original,working,count,stream in (
                ('original_reference',original_ref,ref,nr,original_info_ref),
                ('original_encoded',original_enc,enc,ne,original_info_enc)):
            if original != working:
                original_count, frame_check[label] = automatic_frame_count(ffprobe,original,stream)
                if original_count != count:
                    raise RuntimeError('DV-Vorbereitung hat die Frameanzahl veraendert: '+str(original))
        if nr != ne or nr <= 0:
            raise RuntimeError(f'Frameanzahl stimmt nicht ueberein: Original {nr}, Encode {ne}')
        step = 100 // args.percent
        print(f'{kind.upper()}: {nr} Frames, jedes {step}. Bild. Messung laeuft ...', flush=True)
        print('VMAF_PROGRESS ' + json.dumps({'total': nr, 'frame': 0}), flush=True)
        measurement_started = time.monotonic()
        command = evaluate(ffmpeg, ref, enc, fps, step, args.threads, hdr, root, output / 'ffmpeg.log', crop=crop, display=args.display)
        measurement_finished = time.monotonic()
        scores = json.loads((root / 'scores.json').read_text())
        frames = scores['frames']
        expected = list(range(0, nr, step))
        if [f['frameNum'] for f in frames] != expected:
            raise RuntimeError('Unerwartete Zahl/Reihenfolge bewerteter Frames; kein gueltiger Gesamtbericht.')
        values = [float(f['metrics']['vmaf']) for f in frames]
        if not all(math.isfinite(v) for v in values):
            raise RuntimeError('Ungueltige VMAF-Werte.')
        shutil.copyfile(root / 'scores.json', output / 'frames.json')
        with open(output / 'frames.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['frame', 'seconds', 'vmaf'])
            for frame, value in zip(frames, values):
                writer.writerow([frame['frameNum'], float(Fraction(frame['frameNum']) / fps), value])
        ordered = sorted(values)
        summary = {'script_version': __version__, 'reference': str(original_ref), 'encoded': str(original_enc), 'type': kind,
                   'frame_check': frame_check,
                   'color_metadata':colors_report,
                   'dv_comparison':dv_comparison, 'preparation':preparation,
                   'original_reference_stream':original_info_ref,'original_encoded_stream':original_info_enc,
                   'percent': args.percent, 'subsample': step, 'total_frames': nr,
                   'scored_frames': len(values), 'fps': str(fps), 'mean': sum(values)/len(values),
                   'crop': crop_info, 'display': args.display,
                   'min': min(values), 'max': max(values), 'p05': ordered[int((len(ordered)-1)*.05)],
                   'model_source': model_source, 'model_sha256': hashlib.sha256((root/'model.json').read_bytes()).hexdigest(),
                   'ffmpeg_version': run([ffmpeg, '-version']).splitlines()[0],
                   'downloads': manifest, 'command': command,
                   'reference_stream': info_ref, 'encoded_stream': info_enc,
                   'notes': ['Frame-index alignment; identical content/edit and CFR required.',
                             '50/25 percent are frame samples across the entire film, not duration segments.',
                             'Dynamic HDR metadata is not a separate quality metric.',
                             'HLG is converted to PQ using zimg with npl=1000; single-layer DV uses libplacebo RPU reconstruction.',
                             'Evaluation raster follows encoded active image; lower resolution loss is not evaluated at original 4K display size.']}
    finished = time.monotonic()
    measurement_seconds = measurement_finished - measurement_started
    summary['completed_at'] = datetime.now().astimezone().isoformat(timespec='seconds')
    summary['timing'] = {
        'preparation_seconds': measurement_started - job_started,
        'measurement_seconds': measurement_seconds,
        'finalization_seconds': finished - measurement_finished,
        'job_seconds': finished - job_started,
        'measurement_fps': nr / measurement_seconds if measurement_seconds > 0 else 0,
    }
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print_report(summary)
    if os.environ.get('VMAF_UI') == '1':
        print('VMAF_RESULT ' + json.dumps(summary, ensure_ascii=True), flush=True)
    print('Ergebnisse:', output)
    return 0


if __name__ == '__main__':
    if hasattr(signal,'SIGBREAK'):
        signal.signal(signal.SIGBREAK,signal.default_int_handler)
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('\nAbgebrochen. Temporaere Dateien werden bereinigt.', file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print('FEHLER:', exc, file=sys.stderr)
        sys.exit(1)
