"""Persistent sequential queue and constrained report library."""
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import threading
import uuid
if __package__:
    from .vmaf_settings import config_path, work_directory
else:
    from vmaf_settings import config_path, work_directory


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


class Queue:
    def __init__(self, job, validate, state_path=None, autostart=True):
        self.job, self.validate = job, validate
        self.path = state_path or config_path().with_name('queue.json')
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.items = []; self.roots = []; self.paused = True; self.active = None
        self.error = ''
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding='utf-8'))
            self.items = [item for item in data.get('items', []) if item.get('state') != 'done']
            self.roots = data.get('roots', [])
            for item in self.items:
                if item['state'] == 'running':
                    item['state'] = 'interrupted'
                    item['error'] = 'Vorheriger UI-Lauf unterbrochen. Bei Bedarf erneut einreihen.'
            self.save()
        self.thread = threading.Thread(target=self.loop, daemon=True)
        if autostart: self.thread.start()

    def save(self):
        atomic_json(self.path, {'items': self.items, 'roots': self.roots})

    def add(self, data, resume=False):
        data = dict(data)
        data['work-dir'] = str(Path(data.get('work-dir') or work_directory()).expanduser().resolve())
        for key in ('reference','encoded','output','temp-dir'):
            if data.get(key): data[key] = str(Path(data[key]).expanduser().resolve())
        self.validate(data)
        with self.lock:
            item = {'id': uuid.uuid4().hex, 'data': data, 'state': 'pending', 'error': ''}
            self.items.append(item)
            root = str(Path(data.get('output') or Path(data['work-dir'])/'Ergebnisse').resolve())
            if root not in self.roots: self.roots.append(root)
            self.save()
            if resume: self.paused = False
            return item['id']

    def action(self, action, identifier=None):
        with self.lock:
            if action == 'resume': self.paused = False
            elif action == 'pause': self.paused = True
            else:
                item = next((x for x in self.items if x['id']==identifier), None)
                if not item or item['state']=='running': raise ValueError('Auftrag nicht aenderbar.')
                if action == 'remove': self.items.remove(item)
                elif action == 'retry': item['state']='pending'; item['error']=''
                elif action in ('up','down'):
                    if item['state']!='pending': raise ValueError('Nur wartende Auftraege koennen verschoben werden.')
                    pending=[index for index,value in enumerate(self.items) if value['state']=='pending']
                    index=self.items.index(item); position=pending.index(index)
                    destination=position+(-1 if action=='up' else 1)
                    if 0<=destination<len(pending):
                        other=pending[destination]
                        self.items[index],self.items[other]=self.items[other],self.items[index]
                else: raise ValueError('Unbekannte Wartelistenaktion.')
            self.save()

    def tick(self):
        with self.lock:
            if self.active:
                snapshot = self.job.snapshot()
                if snapshot['running']: return
                item = next(x for x in self.items if x['id']==self.active)
                item['state'] = 'done' if snapshot['phase']=='Fertig' else 'failed'
                item['error'] = '' if item['state']=='done' else '\n'.join(snapshot['logs'][-8:]) or snapshot['phase']
                item['result'] = snapshot['result']
                self.active = None
                if snapshot['phase']=='Abgebrochen': self.paused=True
                if item['state']=='done': self.items.remove(item)
                self.save()
            if self.paused or self.stop.is_set() or self.job.snapshot()['running']: return
            item = next((x for x in self.items if x['state']=='pending'), None)
            if item is None: return
            item['state']='running'; self.active=item['id']; self.save()
            try: self.job.start(item['data'])
            except Exception as exc:
                item['state']='failed'; item['error']=str(exc)
                self.active=None; self.save()

    def loop(self):
        while not self.stop.wait(.3):
            try: self.tick()
            except Exception as exc:
                with self.lock: self.error=str(exc); self.paused=True

    def snapshot(self):
        with self.lock:
            return json.loads(json.dumps({'items':self.items,'paused':self.paused,'active':self.active,'error':self.error}))

    def close(self):
        self.stop.set()
        if self.thread.is_alive(): self.thread.join(timeout=3)
        with self.lock: self.paused=True

    def library(self):
        with self.lock: roots = set(self.roots)
        roots.add(str((work_directory()/'Ergebnisse').resolve()))
        reports = []
        seen = set()
        for value in roots:
            root = Path(value).resolve()
            if not root.is_dir(): continue
            for path in root.rglob('summary.json'):
                try:
                    resolved = path.resolve()
                    if resolved in seen or not resolved.is_relative_to(root) or path.is_symlink(): continue
                    seen.add(resolved)
                    if path.stat().st_size > 2_000_000: continue
                    report = json.loads(path.read_text(encoding='utf-8'))
                    if not isinstance(report,dict) or not math.isfinite(float(report['mean'])): continue
                    if not all(k in report for k in ('reference','encoded','total_frames','scored_frames','percent')): continue
                    reports.append({'id':hashlib.sha256(str(resolved).encode()).hexdigest(),
                                    'path':str(path.parent.resolve()),'report':report})
                except (OSError,ValueError,KeyError,TypeError): continue
        reports.sort(key=lambda x:x['report'].get('completed_at',''), reverse=True)
        return reports

    def delete_report(self, identifier):
        with self.lock:
            entry = next((x for x in self.library() if x['id']==identifier), None)
            if entry is None: raise ValueError('Ergebnis nicht gefunden.')
            folder = Path(entry['path']).resolve(strict=True)
            if self.job.snapshot()['running']: raise ValueError('Ergebnisse nach der laufenden Pruefung loeschen.')
            protected = {Path(entry['report'][key]).resolve() for key in ('reference','encoded')}
            names = ('frames.json','frames.csv','ffmpeg.log','preflight.log','summary.json')
            names += ('vulkan.log','hdr-probe-pq.log','hdr-probe-unknown.log')
            names += tuple(base+suffix for base in ('ffmpeg.log','preflight.log')
                           for suffix in ('.decoder0.log','.decoder1.log','.commands.json',
                                          '.decoder0.progress','.decoder1.progress','.sampling.json'))
            names += tuple(side+'-'+operation+'.log' for side in ('reference','encoded')
                           for operation in ('extract','convert','remux','base-layer'))
            targets = [folder/name for name in names if (folder/name).exists()]
            for target in targets:
                if target.is_symlink() or target.resolve().parent != folder or target.resolve() in protected:
                    raise ValueError('Ergebnisdatei liegt ausserhalb des erlaubten Bereichs.')
            for target in targets: target.unlink()
            # Never recursively delete user files or nested directories.
            try: folder.rmdir()
            except OSError: pass
            with self.job.lock:
                if self.job.result and Path(self.job.result).resolve()==folder:
                    self.job.report=None; self.job.result=None
            return True


def statistics(entries):
    reports=[x['report'] for x in entries]
    groups={}
    times={key:0 for key in ('job_seconds','measurement_seconds','preparation_seconds','finalization_seconds')}
    timed=0
    for report in reports:
        timing=report.get('timing',{})
        if timing: timed+=1
        for key in times:
            value=timing.get(key,0)
            if isinstance(value,(int,float)) and math.isfinite(value) and value>=0: times[key]+=value
        crop=report.get('crop',{})
        group=(report.get('type','?'),report.get('model_sha256','unbekannt'),report.get('display','?'),
               json.dumps(crop.get('alignment',{}).get('target',crop.get('target',{})),sort_keys=True),
               report.get('dv_comparison',{}).get('scope','?'), report.get('percent'))
        groups.setdefault(group,[]).append(report['mean'])
    return {'jobs':len(reports),'files':len({os.path.normcase(x['encoded']) for x in reports}),
            'timed_jobs':timed,'times':times,
            'groups':[{'type':g[0],'model':g[1][:12],'display':g[2],'raster':g[3],'scope':g[4],
                       'percent':g[5],'count':len(values),'mean':sum(values)/len(values)} for g,values in groups.items()]}
