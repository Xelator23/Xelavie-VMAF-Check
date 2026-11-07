/* Local navigation and persistent queue/library views. */
(()=>{
 const title={dashboard:'Dashboard',files:'Dateiauswahl',queue:'Warteschlange',results:'Ergebnisse'};
 $('queue-active').append(document.querySelector('.monitor'));
 const number=(n,d=0)=>new Intl.NumberFormat('de-DE',{minimumFractionDigits:d,maximumFractionDigits:d}).format(n);
 const filename=p=>String(p||'').split(/[\\/]/).pop();
 function page(name){document.querySelectorAll('[data-view]').forEach(v=>v.hidden=v.dataset.view!==name);document.querySelectorAll('[data-page]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.page===name)));$('page-title').textContent=title[name];}
 document.querySelectorAll('[data-page]').forEach(b=>b.onclick=()=>page(b.dataset.page));
 document.querySelectorAll('[data-goto]').forEach(b=>b.onclick=()=>page(b.dataset.goto));
 const element=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
 const button=(text,action,cls)=>{const b=element('button',text,cls);b.type='button';b.onclick=async()=>{b.disabled=true;try{await action();$('global-error').textContent='';}catch(e){$('global-error').textContent=e.message;}finally{b.disabled=false;}};return b;};
 let queueKey='',libraryKey='',busy=false,counter=0,activeId=null;
 $('enqueue').onclick=async()=>{if(!$('form').reportValidity())return;try{await api('enqueue',formData());queueKey='';await refresh();page('queue');}catch(e){$('error').textContent=e.message;}};
 async function queueAction(action,id){await api('queue',{action,id});queueKey='';await refresh();}
 $('queue-resume').onclick=()=>queueAction('resume').catch(e=>$('global-error').textContent=e.message);
 $('queue-pause').onclick=()=>queueAction('pause').catch(e=>$('global-error').textContent=e.message);
 function drawQueue(data){
  const waiting=data.items.filter(x=>x.state==='pending').length;
  const active=data.items.filter(x=>x.state==='running').length;
  const failed=data.items.filter(x=>['failed','interrupted'].includes(x.state)).length;
  $('queue-count').textContent=waiting+active;$('stats-waiting').textContent=waiting+' Filme warten';
  $('queue-overview').textContent=active+' läuft · '+waiting+' warten · '+failed+' Fehler / unterbrochen';
  $('queue-state').textContent=data.error|| (data.paused?'Warteschlange angehalten. Ein laufender Auftrag wird noch beendet.':'Aktiv · Bei Fehlern startet der nächste Auftrag automatisch.');
  $('queue-resume').hidden=!data.paused;$('queue-pause').hidden=data.paused;
  const current=data.items.find(x=>x.state==='running');$('current-film').textContent=current?filename(current.data.encoded):'';
  $('current-source').textContent=current?'Referenz: '+filename(current.data.reference)+' · '+(current.data.percent||100)+' % Prüfanteil':'';
  if(current&&current.id!==activeId){$('protocol').open=false;activeId=current.id;}
  const key=JSON.stringify(data);if(key===queueKey)return;queueKey=key;
  $('queue-items').replaceChildren();
  if(!data.items.length)$('queue-items').append(element('p','Noch keine Aufträge. Unter Dateiauswahl einen Vergleich hinzufügen.','muted'));
  const states={pending:'Wartet',running:'Läuft',done:'Abgeschlossen',failed:'Fehler / abgebrochen',interrupted:'Unterbrochen'};
  const ordered=[...data.items.filter(x=>x.state==='pending'),...data.items.filter(x=>x.state!=='pending'&&x.state!=='running')];
  for(const item of ordered){
   const card=element('section',undefined,'panel library-item');
   card.append(element('h2',filename(item.data.encoded)),element('p',states[item.state]||item.state),element('p','Original: '+item.data.reference,'muted'),element('p',(item.data.percent||100)+' % · Arbeitsordner: '+item.data['work-dir'],'muted'));
   if(item.error){const log=element('details');log.append(element('summary','Fehlerprotokoll'),element('pre',item.error));card.append(log);}
   if(item.state!=='running'){
    const actions=element('div',undefined,'actions');
    if(item.state==='pending'){
     const pending=data.items.filter(x=>x.state==='pending');const position=pending.findIndex(x=>x.id===item.id);
     const up=button('↑ Nach oben',()=>queueAction('up',item.id));up.disabled=position===0;
     const down=button('↓ Nach unten',()=>queueAction('down',item.id));down.disabled=position===pending.length-1;
     actions.append(up,down);
    }
    if(item.state==='failed'||item.state==='interrupted')actions.append(button('Erneut einreihen',()=>queueAction('retry',item.id)));
    actions.append(button('Aus Liste entfernen',()=>queueAction('remove',item.id)));card.append(actions);
   }
   $('queue-items').append(card);
  }
 }
 function drawLibrary(data){
  const key=JSON.stringify([data,running]);if(key===libraryKey)return;libraryKey=key;
  const stats=data.stats;$('results-count').textContent=stats.jobs;$('stats-files').textContent=number(stats.files);
  $('stats-jobs').textContent=number(stats.jobs)+' erfolgreiche Prüfungen';$('stats-time').textContent=clock(stats.times.job_seconds);
  $('stats-timed').textContent=stats.timed_jobs+' Prüfungen mit Zeitangaben';
  for(const [id,key,label] of [['stats-measurement','measurement_seconds','Messzeit'],['stats-preparation','preparation_seconds','Vorbereitung'],['stats-finalization','finalization_seconds','Nachbereitung']])$(id).textContent=label+': '+clock(stats.times[key]);
  $('stats-groups').replaceChildren();
  if(!stats.groups.length)$('stats-groups').append(element('p','Noch keine Ergebnisse.','muted'));
  for(const group of stats.groups){const row=element('div',undefined,'group-stat');row.append(element('strong',number(group.mean,2)),element('p',group.type.toUpperCase()+' · '+group.percent+' % · '+group.count+' Prüfungen · Modell '+group.model+' · '+group.display+' · Raster '+group.raster,'muted'),element('p',group.scope,'muted'));$('stats-groups').append(row);}
  const expanded=new Set([...$('library-items').querySelectorAll('details[open]')].map(d=>d.dataset.reportId));
  $('library-items').replaceChildren();
  if(running&&data.entries.length)$('library-items').append(element('p','Löschen ist nach Abschluss der laufenden Prüfung möglich.','muted result-hint'));
  if(!data.entries.length)$('library-items').append(element('p','Noch keine gespeicherten Ergebnisberichte.','muted'));
  for(const entry of data.entries){
   const r=entry.report,t=r.timing||{},card=element('section',undefined,'panel library-item result-row');
   const head=element('div',undefined,'result-head'),info=element('div',undefined,'result-info');
   info.append(element('h2',filename(r.encoded)),element('p',(r.completed_at?new Date(r.completed_at).toLocaleString('de-DE'):'Älterer Bericht')+' · '+r.percent+' % · '+String(r.type||'').toUpperCase()+(t.job_seconds!==undefined?' · Job '+clock(t.job_seconds):''),'muted'));
   const score=element('div',undefined,'result-score');score.append(element('span','VMAF','muted'),element('strong',number(r.mean,6)));
   head.append(info,score);card.append(head);
   const details=element('details'),summary=element('summary','Prüfbericht');details.dataset.reportId=entry.id;details.open=expanded.has(entry.id);details.append(summary,element('pre',[
    'Vergleich: '+(r.dv_comparison?.scope||r.type),'Original: '+r.reference,'Encode: '+r.encoded,'Frames verarbeitet: '+number(r.total_frames),'Frames bewertet: '+number(r.scored_frames),
    'Durchsatz (nur Messung): '+(Number.isFinite(t.measurement_fps)?number(t.measurement_fps,2)+' FPS':'nicht erfasst'),
    'Messzeit: '+(t.measurement_seconds!==undefined?clock(t.measurement_seconds):'nicht erfasst'),
    'Vorbereitung: '+(t.preparation_seconds!==undefined?clock(t.preparation_seconds):'nicht erfasst'),
    'Laufzeit (Job): '+(t.job_seconds!==undefined?clock(t.job_seconds):'nicht erfasst'),
    'Ergebnisordner: '+entry.path].join('\n')));card.append(details);
   const remove=button('Ergebnis löschen',async()=>{
    if(!confirm('Ergebnisbericht für „'+filename(r.encoded)+'“ und seine JSON-/CSV-/Protokolldateien endgültig löschen? Original und Encode bleiben erhalten.'))return;
    await api('delete-result',{id:entry.id});libraryKey='';counter=0;await refresh();
   },'danger');remove.disabled=running;head.append(remove);$('library-items').append(card);
  }
 }
 async function refresh(){if(closed||busy)return;busy=true;try{
  const queue=await api('queue');drawQueue(queue);$('sidebar-path').textContent='Arbeitsordner: '+$('work-dir').value;
  if(counter++%5===0){const library=await api('library');drawLibrary(library);}
 }catch(e){$('global-error').textContent=e.message;}finally{busy=false;}}
 refresh();setInterval(refresh,1000);
})();
