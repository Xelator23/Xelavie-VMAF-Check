#!/usr/bin/env python3
"""Argument-based CLI and opt-in local browser UI; Python standard library only."""
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs
import webbrowser
if __package__:
    from .vmaf_settings import work_directory, save_work_directory
    from .vmaf_library import Queue, statistics
else:
    from vmaf_settings import work_directory, save_work_directory
    from vmaf_library import Queue, statistics

HERE = Path(__file__).resolve().parent
ENGINE = HERE / 'vmaf_check.py'
ENUMS = {
    'percent': ('100','50','25'), 'display': ('auto','1080','2160'),
    'dv-mode': ('auto','compatible','base-layer','rendered'),
    'ref-color': ('','bt709','hdr10','hlg'), 'enc-color': ('','bt709','hdr10','hlg'),
}
for side in ('ref','enc'):
    ENUMS.update({side+'-primaries':('','bt709','bt2020'),
                  side+'-transfer':('','bt709','smpte2084','arib-std-b67'),
                  side+'-matrix':('','bt709','bt2020nc'),side+'-range':('','limited','full')})


def build_command(data):
    if not isinstance(data,dict): raise ValueError('Ungueltige Eingabe.')
    paths = []
    for key in ('reference','encoded'):
        value = str(data.get(key,'')).strip()
        if not value: raise ValueError('Original und Encode auswaehlen.')
        p = Path(value).expanduser().resolve(strict=True)
        if not p.is_file(): raise ValueError('Keine Videodatei: '+str(p))
        paths.append(str(p))
    cmd = [sys.executable,'-u',str(ENGINE),*paths]
    allowed = {'reference','encoded','crop','crop-encode','threads','output','temp-dir','work-dir',
               'no-download','download-tools',*ENUMS.keys()}
    if set(data)-allowed: raise ValueError('Unbekannte Optionen.')
    for key,values in ENUMS.items():
        value = str(data.get(key,''))
        if not value: continue
        if value not in values: raise ValueError('Ungueltige Option: '+key)
        cmd += ['--'+key,value]
    crop = str(data.get('crop','auto')).strip()
    import re
    for key,value in (('crop',crop),('crop-encode',str(data.get('crop-encode','')).strip())):
        if not value: continue
        if not (key=='crop' and value in ('auto','none')) and not re.fullmatch(r'\d+:\d+:\d+:\d+',value):
            raise ValueError('Crop: auto, none oder Breite:Hoehe:X:Y.')
        cmd += ['--'+key,value]
    if data.get('threads'):
        count = int(data['threads'])
        if not 1 <= count <= 256: raise ValueError('Threads: 1 bis 256.')
        cmd += ['--threads',str(count)]
    for key in ('output','temp-dir','work-dir'):
        value = str(data.get(key,'')).strip()
        if value: cmd += ['--'+key,str(Path(value).expanduser().resolve())]
    if data.get('no-download') and data.get('download-tools'):
        raise ValueError('Offline und erzwungener Download widersprechen sich.')
    for key in ('no-download','download-tools'):
        if data.get(key) is True: cmd += ['--'+key]
    return cmd


def browse(path):
    p = Path(path or os.getcwd()).expanduser().resolve(strict=True)
    if p.is_file(): p=p.parent
    directories, files = [], []
    with os.scandir(p) as entries:
        for entry in entries:
            if entry.name.startswith('.'): continue
            try:
                item={'name':entry.name,'path':str(p/entry.name)}
                if entry.is_dir(): directories.append(item)
                elif entry.is_file(): files.append(item)
            except OSError: continue
    directories.sort(key=lambda x:x['name'].casefold())
    files.sort(key=lambda x:x['name'].casefold())
    drives=[]
    if os.name=='nt':
        for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            try:
                if Path(f'{c}:\\').is_dir(): drives.append(f'{c}:\\')
            except OSError: continue
    else: drives=['/']
    return {'path':str(p),'parent':str(p.parent),'directories':directories[:1000],
            'files':files[:1000],'truncated':len(directories)>1000 or len(files)>1000,'drives':drives}


class Job:
    def __init__(self):
        self.lock=threading.Lock(); self.process=None; self.lines=[]
        self.phase='Bereit'; self.returncode=None; self.started=None; self.command=[]
        self.result=None; self.report=None
        self.finished=None; self.measure_started=None; self.total=None; self.frame=0
        self.step='Bereit'

    def start(self,data):
        command=build_command(data)
        with self.lock:
            if self.phase in ('Laeuft','Wird abgebrochen'): raise ValueError('Eine Pruefung laeuft bereits.')
            self.lines=[]; self.returncode=None; self.started=time.monotonic(); self.result=None
            self.finished=None; self.measure_started=None; self.total=None; self.frame=0
            self.step='Vorbereitung'; self.report=None
            self.command=command; self.phase='Laeuft'
            try:
                self.process=subprocess.Popen(command,cwd=os.getcwd(),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                    text=True,encoding='utf-8',errors='replace',
                    env={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHONUNBUFFERED':'1','VMAF_UI':'1'},
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0,
                    start_new_session=os.name!='nt')
            except BaseException:
                self.phase='Fehler'; self.finished=time.monotonic(); raise
            process=self.process
        threading.Thread(target=self.collect,args=(process,),daemon=True).start()

    def collect(self,process):
        try:
            for line in process.stdout:
                line=line.rstrip()
                with self.lock:
                    if line.startswith('VMAF_RESULT '):
                        try:
                            report=json.loads(line[len('VMAF_RESULT '):])
                            if isinstance(report,dict): self.report=report
                        except ValueError: pass
                        continue
                    if line.startswith('VMAF_PROGRESS '):
                        try:
                            data=json.loads(line[len('VMAF_PROGRESS '):])
                            if isinstance(data.get('total'),int) and data['total']>0:
                                self.total=data['total']; self.measure_started=time.monotonic()
                            if isinstance(data.get('frame'),int) and data['frame']>=0:
                                self.frame=max(self.frame,data['frame'])
                            self.step='VMAF-Messung'
                        except (ValueError,TypeError,AttributeError): pass
                        continue
                    self.lines.append(line)
                    self.lines=self.lines[-1500:]
                    if not self.measure_started and line: self.step=line[:180]
                    if line.startswith('Ergebnisse: '): self.result=line[len('Ergebnisse: '):]
        finally:
            code=process.wait()
            process.stdout.close()
            with self.lock:
                cancelled=self.phase=='Wird abgebrochen'
                self.returncode=code
                self.finished=time.monotonic()
                self.phase='Abgebrochen' if cancelled else 'Fertig' if code==0 else 'Fehler'

    def cancel(self):
        with self.lock:
            p=self.process
            if self.phase not in ('Laeuft','Wird abgebrochen') or not p or p.poll() is not None: return
            self.phase='Wird abgebrochen'
        try:
            if os.name=='nt': p.send_signal(signal.CTRL_BREAK_EVENT)
            else: os.killpg(p.pid,signal.SIGINT)
            p.wait(timeout=12)
        except (subprocess.TimeoutExpired,OSError):
            if p.poll() is not None: return
            if os.name=='nt':
                subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True)
            else:
                try: os.killpg(p.pid,signal.SIGKILL)
                except ProcessLookupError: pass
            if p.poll() is None: p.kill()
            p.wait(timeout=5)

    def snapshot(self):
        with self.lock:
            now=self.finished if self.finished is not None else time.monotonic()
            elapsed=max(0,int(now-self.started)) if self.started is not None else None
            percent=min(99.9,100*self.frame/self.total) if self.total else None
            remaining=None
            measurement=max(0,now-self.measure_started) if self.measure_started is not None else None
            live_fps=self.frame/measurement if measurement and self.frame>0 else None
            if self.phase=='Fertig': percent=100; remaining=0
            elif self.phase=='Laeuft' and self.measure_started is not None and self.total and self.frame>0:
                measurement=now-self.measure_started
                if measurement>=5 and self.frame<self.total:
                    remaining=round(measurement*(self.total-self.frame)/self.frame)
            return {'phase':self.phase,'running':self.phase in ('Laeuft','Wird abgebrochen'),
                    'logs':list(self.lines),'returncode':self.returncode,'result':self.result,
                    'command':self.command,'elapsed':elapsed,'percent':percent,'remaining':remaining,
                    'step':self.step,'frame':self.frame,'total_frames':self.total,
                    'measurement_seconds':measurement,'measurement_fps':live_fps,
                    'report':self.report if self.phase=='Fertig' else None}


class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self):
        super().__init__(('127.0.0.1',0),Handler)
        self.token=secrets.token_urlsafe(32); self.job=Job()
        self.queue=Queue(self.job,build_command)
        self.origin=f'http://127.0.0.1:{self.server_port}'
        self.prefix='/'+self.token+'/'

    def server_close(self):
        self.queue.close()
        super().server_close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass

    def respond(self,data,status=200,html=False):
        payload=data.encode('utf-8') if html else json.dumps(data,ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','text/html; charset=utf-8' if html else 'application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(payload)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers(); self.wfile.write(payload)

    def route(self):
        if self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}': return None
        origin=self.headers.get('Origin')
        if origin and origin!=self.server.origin: return None
        if self.headers.get('Sec-Fetch-Site')=='cross-site': return None
        path=urlsplit(self.path).path
        if not path.startswith(self.server.prefix): return None
        return path[len(self.server.prefix):]

    def do_GET(self):
        route=self.route()
        try:
            if route=='': self.respond((HERE/'vmaf_ui.html').read_text(encoding='utf-8'),html=True)
            elif route=='status': self.respond(self.server.job.snapshot())
            elif route=='settings': self.respond({'work_dir':str(work_directory())})
            elif route=='queue': self.respond(self.server.queue.snapshot())
            elif route=='library':
                entries=self.server.queue.library()
                self.respond({'entries':entries,'stats':statistics(entries)})
            elif route=='logo.png':
                payload=(HERE/'xelavie.png').read_bytes()
                self.send_response(200); self.send_header('Content-Type','image/png')
                self.send_header('Content-Length',str(len(payload))); self.end_headers(); self.wfile.write(payload)
            elif route=='vmaf_navigation.js':
                payload=(HERE/'vmaf_navigation.js').read_bytes()
                self.send_response(200); self.send_header('Content-Type','text/javascript; charset=utf-8')
                self.send_header('Content-Length',str(len(payload))); self.end_headers(); self.wfile.write(payload)
            elif route=='browse': self.respond(browse(parse_qs(urlsplit(self.path).query).get('path',[''])[0]))
            else: self.respond({'error':'Nicht gefunden.'},404)
        except (ValueError,OSError) as exc: self.respond({'error':str(exc)},400)

    def do_POST(self):
        route=self.route()
        if route not in ('start','cancel','shutdown','settings','enqueue','queue','delete-result'):
            self.respond({'error':'Nicht erlaubt.'},403); return
        try:
            if self.headers.get('Content-Type','').split(';')[0]!='application/json': raise ValueError('JSON erforderlich.')
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=32768: raise ValueError('Ungueltige Request-Groesse.')
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict): raise ValueError('JSON-Objekt erforderlich.')
            if route in ('start','enqueue'): self.server.queue.add(data,resume=route=='start')
            elif route=='queue': self.server.queue.action(data.get('action'),data.get('id'))
            elif route=='delete-result': self.server.queue.delete_report(data.get('id'))
            elif route=='settings':
                if not isinstance(data,dict): raise ValueError('Ungueltige Einstellungen.')
                save_work_directory(data.get('work_dir'))
            elif route=='cancel':
                self.server.queue.action('pause')
                threading.Thread(target=self.server.job.cancel,daemon=True).start()
            elif route=='shutdown':
                def close():
                    self.server.queue.close()
                    self.server.job.cancel(); self.server.shutdown()
                threading.Thread(target=close,daemon=True).start()
            self.respond({'ok':True})
        except (ValueError,OSError) as exc: self.respond({'error':str(exc)},400)


def ui():
    server=Server(); url=server.origin+server.prefix
    print('Lokale UI:',url,flush=True)
    print('Beenden ueber die UI oder Strg+C. Tab schliessen beendet den Dienst nicht.',flush=True)
    try:
        webbrowser.open(url)
        server.serve_forever(poll_interval=.3)
    except KeyboardInterrupt: pass
    finally:
        server.queue.close()
        server.job.cancel(); server.server_close()
    return 0


def print_banner():
    if __package__:
        from .vmaf_check import __version__
    else:
        from vmaf_check import __version__
    lettering = (
        '██╗   ██╗███╗   ███╗ █████╗ ███████╗     ██████╗██╗  ██╗███████╗ ██████╗██╗  ██╗',
        '██║   ██║████╗ ████║██╔══██╗██╔════╝    ██╔════╝██║  ██║██╔════╝██╔════╝██║ ██╔╝',
        '██║   ██║██╔████╔██║███████║█████╗      ██║     ███████║█████╗  ██║     █████╔╝',
        '╚██╗ ██╔╝██║╚██╔╝██║██╔══██║██╔══╝     ██║     ██╔══██║██╔══╝  ██║     ██╔═██╗',
        ' ╚████╔╝ ██║ ╚═╝ ██║██║  ██║██║         ╚██████╗██║  ██║███████╗╚██████╗██║  ██╗',
        '  ╚═══╝  ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝          ╚═════╝╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝',
    )
    width = max(len(line) for line in lettering)
    version_label = f'▓▓▒▒░░ [ {__version__} ] '
    border = '▓▓▒▒' + '░' * (width - 8) + '▒▒▓▓'
    footer = version_label + '░' * max(0, width - len(version_label) - 4) + '▒▒▓▓'
    banner = '\n'.join((border, '', *lettering, '',
                        'by Xelavie'.center(width).rstrip(),
                        'COMPARE · ANALYZE · QUALITY'.center(width).rstrip(), '', footer))
    compact = f'VMAF CHECK | by Xelavie | {__version__}'
    if not sys.stdout.isatty() or shutil.get_terminal_size().columns <= width:
        banner = compact
    try:
        banner.encode(sys.stdout.encoding or 'utf-8')
    except (UnicodeEncodeError, LookupError):
        banner = compact
    print(banner + '\n', flush=True)


def print_quick_start():
    print('FILME ANGEBEN\n'
          '  xelavie-vmaf-check "ORIGINAL.mkv" "ENCODE.mkv" [Optionen]\n'
          '\n'
          '  1. ORIGINAL = vollstaendiger Pfad zur Original-/Remux-Datei\n'
          '  2. ENCODE   = vollstaendiger Pfad zur zu pruefenden Datei\n'
          '  Beide Dateien duerfen in verschiedenen Ordnern liegen.\n'
          '  Beispielpfade ersetzen und jeden Pfad in Anfuehrungszeichen setzen.\n', flush=True)
    if os.name == 'nt':
        example = r'xelavie-vmaf-check "D:\Originale\Film.mkv" "E:\Encodes\Film.mkv" --percent 25'
    else:
        example = 'xelavie-vmaf-check "/mnt/originale/Film.mkv" "/mnt/encodes/Film.mkv" --percent 25'
    print('BEISPIEL: 25 % DER FRAMES UEBER DEN GANZEN FILM\n'
          f'  {example}\n'
          '\n'
          'HAEUFIGE OPTIONEN (hinter den beiden Dateipfaden)\n'
          '  --percent 100|50|25    Pruefanteil; ohne Angabe: 100 %\n'
          '  --work-dir "ORDNER"   Arbeitsordner fuer Temp und Ergebnisse\n'
          '\n'
          'HILFE UND OBERFLAECHE (ohne Dateipfade)\n'
          '  xelavie-vmaf-check --help    Alle Optionen, auch Farbangaben\n'
          '  xelavie-vmaf-check --gui     Browser-Oberflaeche starten\n', flush=True)


def main():
    args=sys.argv[1:]
    if args==['--gui']: return ui()
    if '--gui' in args:
        raise ValueError('--gui separat aufrufen. Dateien und Einstellungen in der GUI auswaehlen.')
    if '--ui' in args or '--cli' in args:
        raise ValueError('CLI: ORIGINAL ENCODE [Optionen] angeben. Browser-Oberflaeche: --gui. Hilfe: --help.')
    if '--version' not in args:
        print_banner()
    if not args or args in (['--help'], ['-h']):
        print_quick_start()
        if not args:
            return 0
        args=['--help']
    return subprocess.call([sys.executable,'-u',str(ENGINE),*args])


if __name__=='__main__':
    try: sys.exit(main())
    except (ValueError,OSError,EOFError) as exc:
        print('FEHLER:',exc,file=sys.stderr); sys.exit(1)
    except KeyboardInterrupt: sys.exit(130)
