"""Pinned CPU DV renderer. Activation and ROI are local to each decoder child."""
import hashlib
import json
import os
from pathlib import Path
import platform

HERE = Path(__file__).resolve().parent


def bundle_path():
    machine = {'AMD64': 'x86_64', 'amd64': 'x86_64'}.get(platform.machine(), platform.machine())
    return HERE / 'bin' / (('windows' if os.name == 'nt' else 'linux') + '-' + machine) / 'dv'


def verified_bundle():
    folder = bundle_path()
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['sha256'].items():
        path = folder / name
        if Path(name).name != name or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError('DV-Renderer-Pruefsumme stimmt nicht: ' + name)
    return folder, manifest


def decoder(path, info, crop, policy='optimized'):
    """Only audited 10-bit 4:2:0 MKV decoder families use the new renderer.

    Unsupported formats retain the conventional path without reducing precision.
    Missing/damaged components on a supported platform are errors, not silent
    changes of measurement method.
    """
    if policy == 'classic' or info.get('pix_fmt') != 'yuv420p10le':
        return None
    if info.get('codec_name') not in ('hevc', 'av1', 'ffv1') or Path(path).suffix.lower() != '.mkv':
        return None
    if platform.machine().lower() not in ('x86_64', 'amd64'):
        return None
    w, h = info.get('width'), info.get('height')
    if not all(isinstance(x, int) for x in (w, h, *crop)):
        return None
    cw, ch, x, y = crop
    if not (0 < w <= 16384 and 0 < h <= 16384 and 0 < cw <= w-x and 0 < ch <= h-y and x >= 0 and y >= 0):
        raise ValueError('Ungueltige DV-ROI')
    folder, manifest = verified_bundle()
    env = {k: v for k, v in os.environ.items() if not k.startswith('XELAVIE_')}
    env.update(VK_LAYER_PATH=str(folder), VK_INSTANCE_LAYERS='VK_LAYER_Xelavie_ROI',
               XELAVIE_GUARDED_MAP='0.15', XELAVIE_ROI=f'{w}:{h}:{x}:{y}:{cw}:{ch}:32')
    if os.name != 'nt':
        env['LD_LIBRARY_PATH'] = str(folder) + (os.pathsep + env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
    filters = ('format=p010le,libplacebo=apply_dolbyvision=1:colorspace=bt2020nc:'
               'color_primaries=bt2020:color_trc=smpte2084:range=tv:'
               'format=p016le:peak_detect=0:tonemapping=clip:dithering=none,')
    audit = {'mode': 'optimized-cpu-dv-v1', 'guard_threshold': 0.15, 'roi_halo': 32,
             'bit_identical_to_classic': False, 'sha256': manifest['sha256']}
    return str(folder / manifest['executable']), filters, env, audit
