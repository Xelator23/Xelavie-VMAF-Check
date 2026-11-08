"""Native HDR measurement, streaming two decoders through a bounded frame pair.

The worker owns the pinned libvmaf/zimg conversion. No uncompressed film files,
local TCP listeners, GPU dependency, or SDR-model fallback.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import threading
import time


def worker_path():
    explicit=os.environ.get('VMAF_HDR_WORKER')
    target=('windows' if os.name=='nt' else 'linux')+'-'+{'AMD64':'x86_64','amd64':'x86_64'}.get(platform.machine(),platform.machine())
    name='xelavie-hdr-worker'+('.exe' if os.name=='nt' else '')
    path=Path(explicit) if explicit else Path(__file__).with_name('bin')/target/name
    if not path.is_file():
        raise RuntimeError('Native HDR-Messkomponente fehlt: '+str(path)+'. Vollstaendiges Paket verwenden oder VMAF_HDR_WORKER setzen.')
    return str(path.resolve())


def worker_command(width,height,threads,step,output='scores.json',colors='pq'):
    return [worker_path(),str(width),str(height),str(min(threads or 4,64)),str(step),'model.json',output,colors]


def sparse_worker_supported(command):
    """Older/custom workers keep the compatible interleaved protocol."""
    try:
        result=subprocess.run([command[0],'--version'],capture_output=True,text=True,
                              encoding='utf-8',errors='replace',timeout=10)
        return result.returncode==0 and 'sparse25=1' in result.stdout.split()
    except (OSError,subprocess.TimeoutExpired):
        return False


def compact_model_supported(path):
    """Conversion reuse is audited for this exact HDR model, not custom models."""
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()==(
            '10c9ad02b10ebf77507cf2ba5825c9b60d0a1d95c811e5f382085bb9f26103ad')
    except OSError:
        return False


def check_conversion(root,threads):
    """Both a successful tagged frame pair AND rejection of unknown colour tags."""
    root=Path(root)
    width,height=192,108
    # Two non-uniform 16-bit PQ frames. The negative case differs only in tags.
    import array
    y=array.array('H',(4096+(x%width)*40000//width for x in range(width*height)))
    uv=array.array('H',[32768])*(width*height//2)
    if __import__('sys').byteorder!='little': y.byteswap();uv.byteswap()
    payload=(y.tobytes()+uv.tobytes())*4
    for colors in ('pq','unknown'):
        output='hdr-probe-'+colors+'.json'
        (root/output).unlink(missing_ok=True)
        p=subprocess.run(worker_command(width,height,threads,1,output,colors),cwd=root,
                         input=payload,capture_output=True,timeout=90)
        (root/('hdr-probe-'+colors+'.log')).write_bytes(p.stderr)
        if colors=='pq':
            if p.returncode:
                raise RuntimeError('HDR-Positivtest fehlgeschlagen (libvmaf/zimg): '+p.stderr.decode('utf-8','replace')[-2000:])
            data=json.loads((root/output).read_text())
            if len(data.get('frames',[]))!=2:raise RuntimeError('HDR-Positivtest: unvollstaendige Frame-Ergebnisse.')
        elif p.returncode==0:
            raise RuntimeError('HDR-Negativtest fehlgeschlagen: unbekannte Farbangaben wurden akzeptiert.')


def read_frame(stream,size):
    data=bytearray()
    while len(data)<size:
        chunk=stream.read(size-len(data))
        if not chunk:break
        data.extend(chunk)
    if data and len(data)!=size:raise RuntimeError('Decoder liefert ein unvollstaendiges Rohbild.')
    return data


def sparse_plan(model_path,step,count):
    """Only the audited HDR feature set: motion3 needs ref[n-1:n+2].

    Do not apply this to arbitrary models/temporal feature configurations.
    Unknown models retain the dense path. Original frame indices are preserved.
    """
    if step!=4 or not isinstance(count,int) or count<=0:return None
    model=json.loads(Path(model_path).read_text(encoding='utf-8')).get('model_dict',{})
    features=model.get('feature_names',[])
    allowed={'Cambi_feature_cambi_score','Speed_chroma_feature_speed_chroma_uv_score',
             'VMAF_integer_feature_adm3_score','VMAF_integer_feature_motion3_score'}
    if not isinstance(features,list) or len(features)!=4 or set(features)!=allowed:return None
    options=model.get('feature_opts_dicts',[])
    if not isinstance(options,list) or len(options)!=len(features):return None
    motion=options[features.index('VMAF_integer_feature_motion3_score')]
    # Keep the only audited configuration; e.g. five-frame motion or a moving
    # average changes the context requirement and must never silently use this.
    if not isinstance(motion,dict) or set(motion)-{'motion_max_val'}:return None
    return {'mode':'reference-neighbours-encode-samples','total_frames':count,'step':step,
            'reference_rendered':count-(count+1)//4,
            'encoded_rendered':(count+3)//4,
            'reference_select':'not(eq(mod(n,4),2))','encoded_select':'not(mod(n,4))'}


def decoded_count(path):
    values={}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        key,sep,value=line.partition('=')
        if sep:values[key]=value.strip()
    if values.get('progress')!='end' or not values.get('frame','').isdigit():
        raise RuntimeError('HDR-Decoder: vollstaendiger Framezaehler fehlt: '+str(path))
    return int(values['frame'])


def frame_pairs(reference,encoded,size,plan=None):
    if plan is None:
        while True:
            ref=read_frame(reference,size);enc=read_frame(encoded,size)
            if not ref and not enc:return
            if not ref or not enc:raise RuntimeError('HDR-Decoder liefern unterschiedlich viele Frames.')
            yield ref,enc
    else:
        ref=None
        for index in range(plan['total_frames']):
            if index%4!=2:
                ref=read_frame(reference,size)
                if not ref:raise RuntimeError('HDR-Referenz endet vor der erwarteten Frameanzahl.')
            enc=read_frame(encoded,size) if index%4==0 else ref
            if not enc:raise RuntimeError('HDR-Encode endet vor der erwarteten Frameanzahl.')
            # These placeholders never affect sampled spatial scores or their
            # immediate reference neighbours. They retain libvmaf's full index
            # sequence and EOF motion handling without changing the model.
            yield ref,enc
        if read_frame(reference,size) or read_frame(encoded,size):
            raise RuntimeError('HDR-Decoder liefern mehr Frames als erwartet.')


def evaluate(commands,width,height,threads,step,root,log,progress,plan=None):
    """commands order is reference, distorted. All children are reaped on failure."""
    worker=worker_command(width,height,threads,step)
    compact=bool(plan and step==4 and compact_model_supported(Path(root)/'model.json')
                 and sparse_worker_supported(worker))
    if compact:
        worker[-1]='pq-sparse25'
        worker.append(str(plan['total_frames']))
    children=[];logs=[];reader=None
    try:
        for index,cmd in enumerate(commands):
            error=open(str(log)+f'.decoder{index}.log','wb');logs.append(error)
            children.append(subprocess.Popen(cmd,cwd=root,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=error))
        error=open(log,'wb');logs.append(error)
        consumer=subprocess.Popen(worker,cwd=root,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=error)
        children.append(consumer)
        def report():
            last=0.0;last_frame=0;reported_frame=0
            for line in consumer.stdout:
                key,_,value=line.decode('ascii','replace').strip().partition('=')
                if progress and key=='frame' and value.isdigit():
                    last_frame=int(value);now=time.monotonic()
                    if now-last>=1:
                        print('VMAF_PROGRESS '+json.dumps({'frame':last_frame}),flush=True)
                        last=now;reported_frame=last_frame
            if progress and last_frame!=reported_frame:
                print('VMAF_PROGRESS '+json.dumps({'frame':last_frame}),flush=True)
        reader=threading.Thread(target=report,daemon=True);reader.start()
        size=width*height*3  # planar 4:2:0, sixteen bits per sample
        for index,(ref,enc) in enumerate(frame_pairs(children[0].stdout,children[1].stdout,size,plan)):
            if not compact or index%4!=2:consumer.stdin.write(ref)
            if not compact or index%4==0:consumer.stdin.write(enc)
        consumer.stdin.close()
        codes=[p.wait() for p in children]
        reader.join()
        if any(codes):raise RuntimeError('HDR-Messung oder Decoder fehlgeschlagen: '+str(codes)+'. Siehe '+str(log)+' und .decoder0/.decoder1.log')
        if plan:
            counts=[decoded_count(str(log)+f'.decoder{i}.progress') for i in (0,1)]
            if counts!=[plan['total_frames']]*2:
                raise RuntimeError('HDR-Framezaehler widersprechen Metadaten: '+str(counts))
            Path(str(log)+'.sampling.json').write_text(json.dumps({**plan,'decoded_frames':counts},indent=2),encoding='utf-8')
    except (BrokenPipeError,OSError) as exc:
        raise RuntimeError('HDR-Messkomponente/Decoder abgebrochen. Siehe '+str(log)) from exc
    finally:
        for child in children:
            if child.poll() is None:child.terminate()
        for child in children:
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.kill();child.wait()
        if reader:reader.join(timeout=10)
        for child in children:
            for stream in (child.stdin,child.stdout):
                if stream:
                    try:stream.close()
                    except OSError:pass
        for file in logs:file.close()
    Path(str(log)+'.commands.json').write_text(json.dumps({'decoders':commands,'measurement':worker,
        'transport':('bounded compact 25% frames; converted placeholders reused' if compact else
                     'bounded interleaved 16-bit frame pairs'),'sampling':plan},indent=2),encoding='utf-8')
    return worker
