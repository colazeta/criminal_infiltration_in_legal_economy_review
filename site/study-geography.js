/* Read-only geography of the analysis, from current source-linked research facts. */
(() => {
  'use strict';
  const ENDPOINT = 'https://criminal-infiltration-curator.colazeta-research.workers.dev/api/public-paper-research';
  const CODES = 'AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW'.split(' ');
  const normal = value => String(value || '').normalize('NFKC').toLowerCase().replace(/[’']/g, "'").replace(/\s+/g, ' ').trim().replace(/[.]$/, '');
  const names = new Map(), labels = new Map();
  const en = new Intl.DisplayNames(['en'], {type:'region'}), it = new Intl.DisplayNames(['it'], {type:'region'});
  for (const code of CODES) {
    labels.set(code, it.of(code));
    names.set(normal(en.of(code)), code); names.set(normal(it.of(code)), code);
    names.set(normal(en.of(code).replace(/ & /g,' and ')),code); names.set(normal(it.of(code).replace(/ & /g,' e ')),code);
  }
  for (const [alias, code] of Object.entries({'uk':'GB','u.k.':'GB','united states of america':'US','usa':'US','u.s.a.':'US','u.s.':'US','the united states':'US','the united kingdom':'GB','the netherlands':'NL','czech republic':'CZ','russian federation':'RU','south korea':'KR','republic of korea':'KR','north korea':'KP','viet nam':'VN','turkiye':'TR','türkiye':'TR','ivory coast':'CI','republic of the congo':'CG','democratic republic of the congo':'CD'})) names.set(normal(alias),code);
  // Ambiguous bare place names must not select a sovereign state by accident.
  for (const name of ['georgia','congo','korea','america']) names.delete(name);
  const broad = new Set(['global','worldwide','international','cross-national','transnational','europe','europa','european union','unione europea','eu','africa','asia','latin america','america latina','north america','south america','central america','western europe','eastern europe','european countries','oecd countries','multiple countries','paesi diversi']);
  const orderedNames = [...names.keys()].sort((a,b) => b.length-a.length);
  const forbidden = /\b(?:not|except|excluding|outside|origin|origins|mafia|mafias|ndrangheta|camorra|affiliation|affiliations|publisher|authors?|headquarters?|citizenship|nationality|versus|vs|comparison|background)\b/i;

  function normaliseGeography(value) {
    const raw = typeof value === 'string' ? value.trim() : '';
    if (!raw || raw.length > 6000) return {countries:[],kind:'unresolved'};
    if (CODES.includes(raw)) return {countries:[raw],kind:'countries'};
    let text = normal(raw);
    if (['northern ireland','northern cyprus'].includes(text)) return {countries:[],kind:'unresolved'};
    if (broad.has(text)) return {countries:[],kind:'supranational'};
    if (forbidden.test(text)) return {countries:[],kind:'unresolved'};
    // Only an entire list of recognised countries is codable. Never keyword-scan an abstract.
    // A parenthetical territorial qualifier is kept in the visible raw value, not a new country.
    const parentheses = [...text.matchAll(/\(([^()]*)\)/g)];
    for (const [,inside] of parentheses) {
      if (orderedNames.some(name => new RegExp('(?:^|[^a-z])'+name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'(?:$|[^a-z])','i').test(inside))) return {countries:[],kind:'unresolved'};
    }
    text = text.replace(/\([^()]*\)/g,'').trim();
    const countries = new Set();
    const matchCountry = text => orderedNames.find(key => text === key || (text.startsWith(key) && /^(?:\s*(?:[,;|&]|and\b|e\b))/.test(text.slice(key.length))));
    while (text) {
      // South Africa and North Macedonia are whole country names, not directional qualifiers.
      if (!matchCountry(text)) text = text.replace(/^(?:(?:north(?:ern)?|south(?:ern)?|east(?:ern)?|west(?:ern)?|central)\s+)+/,'');
      const name = matchCountry(text);
      if (!name) return {countries:[],kind:'unresolved'};
      countries.add(names.get(name)); text = text.slice(name.length).trim();
      if (text) {
        const delimiter = text.match(/^(?:[,;|&]\s*(?:(?:and|e)\s+)?|(?:and|e)\s+)/);
        if (!delimiter) return {countries:[],kind:'unresolved'};
        text = text.slice(delimiter[0].length).trim();
        if (!text) return {countries:[],kind:'unresolved'};
      }
    }
    return countries.size ? {countries:[...countries].sort(),kind:'countries'} : {countries:[],kind:'unresolved'};
  }

  function extract(data) {
    if (!['available','not_assessed','not_registered','stale','withheld'].includes(data?.availability)) throw Error('invalid_availability');
    if (data.availability !== 'available') {
      if (data.research !== null) throw Error('invalid_unavailable_research');
      return {state:data.availability,countries:[],studies:[]};
    }
    const r = data.research;
    if (!r || r.assessment_state !== 'unreviewed_proposal' || !['abstract_only','partial_text','full_text'].includes(r.source_coverage) || !Array.isArray(r.studies) || !Array.isArray(r.spans) || !Array.isArray(r.sources)) throw Error('invalid_research');
    const sources = new Map(r.sources.map(s => [s.id,s]));
    const spans = new Map(r.spans.map(s => [s.id,s]));
    const countries = new Set(), studies=[];
    for (const study of r.studies) {
      const fact = study.geography;
      if (!fact || !['reported','not_reported','not_verifiable','not_applicable','ambiguous'].includes(fact.status)) throw Error('invalid_geography_fact');
      const row = {id:study.id,raw:fact.value,status:fact.status,origin:fact.origin,countries:[],kind:'missing',evidence:[]};
      if (fact.status === 'reported' && fact.origin === 'source' && typeof fact.value === 'string' && fact.value.trim()) {
        if (!Array.isArray(fact.evidence_span_ids) || !fact.evidence_span_ids.length) throw Error('unsupported_geography');
        for (const id of fact.evidence_span_ids) {
          const span=spans.get(id), source=sources.get(span?.source_id);
          if (!span || !source || typeof source.url !== 'string') throw Error('broken_geography_evidence');
          row.evidence.push({url:source.url,locator:span.locator || ''});
        }
        Object.assign(row,normaliseGeography(fact.value));
        row.countries.forEach(code => countries.add(code));
      } else if (fact.status === 'ambiguous' || fact.origin === 'analyst') row.kind='unresolved';
      studies.push(row);
    }
    const state = countries.size ? 'countries' : studies.some(s=>s.kind==='unresolved') ? 'unresolved' : studies.some(s=>s.kind==='supranational') ? 'supranational' : !studies.length ? 'no_studies' : studies.some(s=>s.status==='not_verifiable') ? 'not_verifiable' : studies.length && studies.every(s=>s.status==='not_applicable') ? 'not_applicable' : 'not_reported';
    return {state,countries:[...countries].sort(),studies,coverage:r.source_coverage,updatedAt:r.updated_at,automated:r.generation_kind==='automated',partial:studies.some(s=>s.kind!=='countries')};
  }

  function aggregate(records, rows) {
    const ids=new Set(), counts=new Map(), states=new Map(); let withCountries=0,multinational=0,partiallyCoded=0;
    for (const record of records) {
      if (!record?.id || ids.has(record.id)) throw Error('duplicate_or_missing_record_id');
      ids.add(record.id);
      const item=rows.get(record.id) || {state:'pending',countries:[]};
      states.set(item.state,(states.get(item.state)||0)+1);
      const countries=new Set(item.countries);
      if (countries.size) withCountries++;
      if (countries.size>1) multinational++;
      if (countries.size && item.partial) partiallyCoded++;
      for (const code of countries) { if (!labels.has(code)) throw Error('invalid_country_code'); counts.set(code,(counts.get(code)||0)+1); }
    }
    return {total:records.length,withCountries,multinational,partiallyCoded,states,ranking:[...counts].sort((a,b)=>b[1]-a[1]||labels.get(a[0]).localeCompare(labels.get(b[0]),'it'))};
  }

  async function readJSON(url,fetcher=globalThis.fetch) {
    const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),12000);
    try { const response=await fetcher(url,{cache:'no-store',credentials:'omit',signal:controller.signal}); if(!response.ok)throw Error('public_data_unavailable'); return await response.json(); }
    finally {clearTimeout(timer);}
  }

  function createIndex(records,{read=readJSON,selectResearch,onUpdate=()=>{}}) {
    aggregate(records,new Map());
    const rows=new Map(records.map(r=>[r.id,{state:'pending',countries:[],studies:[]} ]));
    const progress={running:false,attempted:0,checked:0,errors:0,total:records.length}; let active=null;
    function scan() {
      if(active)return active;
      Object.assign(progress,{running:true,attempted:0,checked:0,errors:0});
      for(const record of records)rows.set(record.id,{state:'pending',countries:[],studies:[]});
      active=(async()=>{
        let next=0,failures=0;
        async function worker(){while(next<records.length&&failures<4){const record=records[next++];
          try{const data=selectResearch(await read(ENDPOINT+'?id='+encodeURIComponent(record.id)),record);rows.set(record.id,extract(data));progress.checked++;failures=0;}
          catch{rows.set(record.id,{state:'error',countries:[],studies:[]});progress.errors++;failures++;}
          progress.attempted++;if(progress.attempted%12===0)onUpdate();
        }}
        try{await Promise.all(Array.from({length:Math.min(4,records.length)},worker));}
        finally{progress.running=false;active=null;onUpdate();}
      })();onUpdate();return active;
    }
    return {rows,progress,scan};
  }

  function mount({host,records,selectResearch}) {
    const el=(tag,text)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;return node;};
    const panel=el('article');panel.className='bibliometric-panel';panel.id='study-geography';
    const title=el('h3','Paesi e territori oggetto dell’analisi');title.id='study-geography-title';panel.setAttribute('aria-labelledby',title.id);
    const note=el('p','La geografia riguarda l’oggetto dello studio, non gli autori o la provenienza dei gruppi criminali. Sono usate soltanto localizzazioni attribuite alle fonti nelle estrazioni preliminari correnti, non validate scientificamente.');
    const countNote=el('p','Ogni record contribuisce al massimo una volta per paese, anche con più studi. Un lavoro multinazionale compare in più barre: i conteggi non sono additivi. Le percentuali usano tutti i record della vista. Le barre descrivono la copertura della letteratura, non la diffusione dell’infiltrazione.');
    const button=el('button','Carica / aggiorna la geografia');button.type='button';
    const status=el('p');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
    const chart=el('div'),quality=el('div'),detail=el('details');detail.append(el('summary','Entità geografiche e fonti per paper'));const detailBody=el('div');detail.append(detailBody);
    panel.append(title,note,countNote,button,status,chart,quality,detail);host.append(panel);
    let selected=[],index=null;
    const coverageLabels={abstract_only:'solo abstract',partial_text:'testo parziale',full_text:'testo completo'};
    const stateLabels={countries:'Almeno un paese codificabile',supranational:'Solo ambito sovranazionale, senza elenco di paesi',unresolved:'Territorio riportato ma non normalizzabile con sicurezza',no_studies:'Nessuno studio strutturato estratto',not_verifiable:'Paese non verificabile dalla fonte consultata',not_applicable:'Non applicabile nella fonte consultata',not_reported:'Paese non riportato nella fonte consultata',not_assessed:'Nessuna estrazione disponibile',not_registered:'Non presente nell’indice analitico',stale:'Estrazione non aggiornata',withheld:'Estrazione non pubblicabile',error:'Richiesta non riuscita',pending:'Non ancora verificato'};
    function render(){
      if(!index)return;
      const p=index.progress,a=aggregate(selected,index.rows),fmt=new Intl.NumberFormat('it-IT',{maximumFractionDigits:1});
      button.disabled=p.running||!selected.length;panel.setAttribute('aria-busy',String(p.running));
      status.textContent=`${a.withCountries}/${a.total} record con almeno un paese identificato · ${a.multinational} multinazionali · ${p.checked}/${p.total} stati verificati nel registro consultabile. `+(p.running?'Verifica in corso: conteggi parziali. ':p.checked<p.total?'Verifica incompleta: i mancanti non valgono zero. ':'')+(a.partiallyCoded?`${a.partiallyCoded} record hanno anche studi senza paese codificabile. `:'');
      chart.replaceChildren();quality.replaceChildren();detailBody.replaceChildren();
      if(!a.total){chart.append(el('p','Il corpus valutato è vuoto. Attiva “Includi record ancora da analizzare” per consultare il registro operativo.'));}
      else if(!a.ranking.length){chart.append(el('p','Non sono ancora disponibili conteggi nazionali verificabili nella vista. Non è un’assenza di studi in quei paesi.'));}
      else{
        const table=el('table');const head=el('thead'),header=el('tr');['Paese / territorio','Record','Quota della vista','Volume relativo'].forEach(t=>header.append(el('th',t)));head.append(header);table.append(head);
        const body=el('tbody'),max=a.ranking[0][1];
        for(const[code,n]of a.ranking){const row=el('tr'),name=el('th',labels.get(code));name.scope='row';const mark=el('td'),track=el('span'),fill=el('span');track.className='bibliometric-bar-track';fill.className='bibliometric-bar-fill';fill.style.width=`${100*n/max}%`;track.setAttribute('aria-hidden','true');track.append(fill);mark.append(track);row.append(name,el('td',String(n)),el('td',`${fmt.format(100*n/a.total)}%`),mark);body.append(row);}
        table.append(body);const scroll=el('div');scroll.className='table-scroll';scroll.append(table);chart.append(scroll);
      }
      const coverage=el('p','Copertura e dati mancanti: '+[...a.states].map(([key,n])=>`${stateLabels[key]||key}: ${n}`).join(' · '));quality.append(coverage);
      for(const record of selected){const entry=index.rows.get(record.id);if(!entry?.studies?.length)continue;const block=el('details');block.append(el('summary',record.title));block.append(el('p',`Fonte consultata: ${coverageLabels[entry.coverage]||entry.coverage} · aggiornamento: ${entry.updatedAt||'non riportato'}`));entry.studies.forEach((study,i)=>{block.append(el('p',`Studio ${i+1} · Entità geografica: ${study.raw||stateLabels[study.status]||study.status}${study.origin==='analyst'?' (interpretazione analitica, esclusa dai conteggi)':''} · Paesi: ${study.countries.map(c=>labels.get(c)).join(', ')||'non codificati'}`));for(const evidence of study.evidence){const href=globalThis.CILEPaperResearch?.safeUrl(evidence.url);if(href){const a=el('a','Fonte · '+evidence.locator);a.href=href;a.rel='noreferrer noopener';const line=el('p');line.append(a);block.append(line);}}});detailBody.append(block);}
    }
    index=createIndex(records,{selectResearch,onUpdate:render});
    function setRecords(records){selected=records;render();if(selected.length&&!index.progress.running&&!index.progress.attempted)index.scan();}
    button.addEventListener('click',()=>index?.scan());
    return {setRecords};
  }
  globalThis.CILEStudyGeography={normaliseGeography,extract,aggregate,readJSON,createIndex,mount};
})();
