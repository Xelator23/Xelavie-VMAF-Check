"""Interactive CLI prompts and native path completion without dependencies."""
import json
from contextlib import contextmanager
import os
import re
from pathlib import Path
import shutil
import sys
from vmaf_settings import config_path
from vmaf_library import atomic_json


def clean_path(value):
    value=value.strip()
    if len(value)>=2 and value[0]==value[-1] and value[0] in ('"', "'"):
        value=value[1:-1]
    return value


def navigation_path(value):
    raw=clean_path(value)
    match=re.match(r'^cd(?:\s+/d)?\s+(.*)$',raw,re.IGNORECASE)
    directory_only=bool(match)
    if match: raw=clean_path(match.group(1))
    if os.name=='nt' and re.fullmatch(r'[A-Za-z]:',raw): raw+=os.sep
    return raw,directory_only


def completions(value, base):
    raw,directory_only=navigation_path(value)
    path=Path(raw).expanduser() if raw else Path(base)
    if not path.is_absolute(): path=Path(base)/path
    directory=path if not raw or raw.endswith(('/',os.sep)) else path.parent
    prefix='' if directory==path else path.name
    try:
        items=sorted(directory.iterdir(),key=lambda p:p.name.casefold())
        matches=[]
        for item in items:
            name=item.name.casefold() if os.name=='nt' else item.name
            start=prefix.casefold() if os.name=='nt' else prefix
            is_directory=item.is_dir()
            if directory_only and not is_directory:continue
            if name.startswith(start): matches.append(('cd ' if directory_only else '')+str(item)+(os.sep if is_directory else ''))
        return matches
    except OSError: return []


def preview_rows(value, base, limit=6):
    """Compact suggestions; never interpret filenames as terminal commands."""
    matches=completions(value,base)
    rows=[]
    for candidate in matches[:limit]:
        raw,_=navigation_path(candidate)
        directory=raw.endswith(('/',os.sep))
        name=Path(raw).name or raw
        name=''.join(ch if ch.isprintable() else '?' for ch in name)
        rows.append(('  [Ordner] ' if directory else '  [Datei]  ')+name)
    if len(matches)>limit: rows.append(f'  ... {len(matches)-limit} weitere Treffer - weiter tippen')
    if not rows: rows=['  Keine passenden Eintraege (oder Ordner nicht lesbar).']
    return ['Vorschau - Tab ergaenzt, Enter oeffnet/waehlt:']+rows


@contextmanager
def console_preview():
    """Enable Windows VT output for this prompt, restoring the console mode."""
    kernel=None;handle=None;previous=None
    try:
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetStdHandle.argtypes=[wintypes.DWORD];kernel.GetStdHandle.restype=wintypes.HANDLE
        kernel.GetConsoleMode.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
        kernel.SetConsoleMode.argtypes=[wintypes.HANDLE,wintypes.DWORD]
        handle=kernel.GetStdHandle(-11)
        mode=wintypes.DWORD()
        if kernel.GetConsoleMode(handle,ctypes.byref(mode)):
            previous=mode.value
            enabled=bool(kernel.SetConsoleMode(handle,previous|4))
        else: enabled=False
    except (ImportError,AttributeError,OSError): enabled=False
    try: yield enabled
    finally:
        if previous is not None: kernel.SetConsoleMode(handle,previous)


def windows_input(prompt, initial, base, getch=None, preview=False):
    if getch is None:
        import msvcrt
        getch=msvcrt.getwch
    text=initial; position=len(text); previous=0; matches=[]; match_index=-1
    def draw():
        nonlocal previous
        size=shutil.get_terminal_size((100,24))
        width=max(1,size.columns-len(prompt)-2)
        start=max(0,position-width+1)
        visible=text[start:start+width]
        shown=prompt+visible
        if preview:
            rows=preview_rows(text,base,limit=max(1,min(6,size.lines-5)))
            sys.stdout.write('\r\x1b[J'+shown+'\n')
            for row in rows: sys.stdout.write(row[:max(1,size.columns-2)]+'\n')
            sys.stdout.write(f'\x1b[{len(rows)+1}A')
        else: sys.stdout.write('\r'+shown+' '*max(0,previous-len(shown)))
        sys.stdout.write('\r'+prompt+text[start:position]);sys.stdout.flush()
        previous=len(shown)
    draw()
    while True:
        char=getch()
        if char in ('\r','\n'):
            if preview:sys.stdout.write('\r\x1b[J'+prompt+text[-max(1,shutil.get_terminal_size((100,24)).columns-len(prompt)-2):])
            sys.stdout.write('\n');sys.stdout.flush();return text
        if char=='\x03' or (char in ('\x04','\x1a') and not text):
            if preview:sys.stdout.write('\r\x1b[J');sys.stdout.flush()
            if char=='\x03':raise KeyboardInterrupt
            raise EOFError
        if char=='\t':
            if not matches: matches=completions(text,base);match_index=-1
            if matches:
                match_index=(match_index+1)%len(matches);text=matches[match_index];position=len(text)
                if len(matches)==1: matches=[]
            draw();continue
        matches=[]
        if char in ('\x00','\xe0'):
            key=getch()
            if key=='K': position=max(0,position-1)
            elif key=='M': position=min(len(text),position+1)
            elif key=='G': position=0
            elif key=='O': position=len(text)
            elif key=='S': text=text[:position]+text[position+1:]
        elif char=='\x15': text='';position=0
        elif char=='\x01': position=0
        elif char=='\x05': position=len(text)
        elif char in ('\b','\x7f'):
            if position: text=text[:position-1]+text[position:];position-=1
        elif char.isprintable(): text=text[:position]+char+text[position:];position+=len(char)
        draw()


def path_input(prompt, base):
    if not sys.stdin.isatty() or not sys.stdout.isatty(): return input(prompt)
    initial=''
    if os.name=='nt':
        with console_preview() as enabled:
            return windows_input(prompt,initial,base,preview=enabled)
    try: import readline
    except ImportError:
        print('Tab-Vervollstaendigung ist in diesem Terminal nicht verfuegbar.')
        return input(prompt)
    old_completer=readline.get_completer();old_delimiters=readline.get_completer_delims()
    candidates=[]
    def complete(text,state):
        nonlocal candidates
        if state==0: candidates=completions(text,base)
        return candidates[state] if state<len(candidates) else None
    try:
        readline.set_completer_delims('');readline.set_completer(complete)
        readline.parse_and_bind('bind ^I rl_complete' if 'libedit' in (readline.__doc__ or '') else 'tab: complete')
        readline.set_startup_hook(lambda:readline.insert_text(initial))
        return input(prompt)
    finally:
        readline.set_startup_hook(None);readline.set_completer(old_completer);readline.set_completer_delims(old_delimiters)


def choose_file(label, base):
    base=Path(base)
    while True:
        print(f'{label} - Aktueller Ordner: {base}')
        entered=clean_path(path_input(label+': ',base))
        if entered.lower()=='cd':continue
        if entered.lower() in ('dir','ls'):
            try:
                entries=sorted(base.iterdir(),key=lambda p:(not p.is_dir(),p.name.casefold()))
                for item in entries[:100]:print(('Ordner  ' if item.is_dir() else 'Datei   ')+item.name)
                if len(entries)>100:print('Weitere Eintraege vorhanden. Namen mit Tab vervollstaendigen.')
            except OSError as exc:print('Ordner nicht lesbar:',exc)
            continue
        raw,directory_only=navigation_path(entered)
        if not raw: print('Bitte eine Datei angeben.');continue
        path=Path(raw).expanduser()
        if not path.is_absolute(): path=Path(base)/path
        try:
            path=path.resolve(strict=True)
            if path.is_file() and not directory_only: return str(path)
            if path.is_dir(): base=path;print('Ordner geoeffnet. Dateinamen eingeben oder Tab verwenden.');continue
        except (OSError,ValueError): pass
        print('Datei nicht gefunden. Pfad korrigieren oder Strg+C zum Abbrechen.')


def choice(prompt, options, default):
    while True:
        value=input(prompt).strip() or default
        if value in options:return value
        print('Bitte eine der angegebenen Optionen waehlen.')


def collect_inputs():
    settings_file=config_path().with_name('cli.json')
    try: saved=json.loads(settings_file.read_text(encoding='utf-8'))
    except (OSError,ValueError): saved={}
    if not isinstance(saved,dict):saved={}
    def base(key):
        value=saved.get(key)
        path=Path(value) if isinstance(value,str) else Path.cwd()
        return path if path.is_dir() else Path.cwd()
    print('Dateipfade: Tab ergaenzt Namen; Windows: wiederholt Tab fuer weitere Treffer.')
    print('Windows: Live-Vorschau unter der Eingabe. Linux: zweimal Tab zeigt passende Pfade.')
    print('Ordner wechseln: cd .. oder absoluten Pfad eingeben, z.B. D:\\Filme\\. dir/ls zeigt den Inhalt.')
    print('Strg+U leert die Eingabe. Original- und Encode-Ordner werden getrennt gemerkt.')
    reference=choose_file('Original-Datei',base('reference_dir'))
    encoded=choose_file('Encode-Datei',base('encoded_dir'))
    percent=choice('Pruefanteil 100/50/25 [100]: ',('100','50','25'),'100')
    print('\nFarbangaben: 0 = Automatisch, 1 = BT.709 / SDR Limited, 2 = HDR10 / PQ Limited, 3 = HLG Limited')
    print('Presets ueberschreiben Farbangaben. Nur bekannte Quellwerte setzen.')
    presets={'0':'','1':'bt709','2':'hdr10','3':'hlg'}
    ref_color=choice('Original - Farbmodus [0]: ',presets,'0')
    enc_color=choice('Encode - Farbmodus [0]: ',presets,'0')
    data={'reference':reference,'encoded':encoded,'percent':percent,
          'ref-color':presets[ref_color],'enc-color':presets[enc_color]}
    for side,label in (('ref','Original'),('enc','Encode')):
        if data[side+'-color']:
            value=choice(label+' - Wertebereich: 1 = Limited, 2 = Full [1]: ',('1','2'),'1')
            if value=='2':data[side+'-range']='full'
    try:
        atomic_json(settings_file,{'reference_dir':str(Path(reference).parent),'encoded_dir':str(Path(encoded).parent)})
    except OSError as exc: print('Ordner konnten nicht gespeichert werden:',exc)
    return data
