/* Same archive reader as MCP; source text is always rendered as data. */
(() => {
 'use strict';
 const ORIGIN='https://criminal-infiltration-curator.colazeta-research.workers.dev';
 const API=ORIGIN+'/api/public-document-library',PDF=ORIGIN+'/api/public-paper-assets';
 const $=id=>document.getElementById(id),el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n};
 const params=new URLSearchParams(location.search);let cursor=null,record=null,documentId=null,pageCount=null,generation=0,pageGeneration=0;
 const rights={public_rehost_allowed:'Copia pubblica autorizzata',private_analysis_only:'Copia riservata',rights_unresolved:'Redistribuzione non verificata'};
 async function read(args){const response=await fetch(API+'?'+new URLSearchParams(args),{credentials:'omit',cache:'no-store',signal:AbortSignal.timeout(15000)});if(!response.ok)throw Error(response.status===404?'Documento non disponibile per la consultazione pubblica.':'Dati temporaneamente non disponibili. Riprova: questo errore non indica che il documento sia assente.');return response.json()}
 async function search(append=false){const serial=++generation;$('document-status').textContent='Ricerca in corso…';if(!append){cursor=null;$('document-results').replaceChildren()}
  try{const result=await read({query:$('document-query').value,...(cursor?{cursor}:{})});if(serial!==generation)return;
   for(const r of result.records){const item=el('article'),button=el('button',r.title);button.type='button';button.onclick=()=>openPaper(r.candidate_id);item.append(button,el('p',[r.authors,r.year,r.venue].filter(Boolean).join(' · ')));$('document-results').append(item)}
   cursor=result.next_cursor;$('document-more').hidden=!cursor;$('document-status').textContent=result.records.length?'Seleziona un paper per vedere le versioni disponibili.':'Nessun risultato per questa ricerca.';
  }catch(e){if(serial===generation)$('document-status').textContent=e.message}
 }
 async function showPage(page){const serial=++pageGeneration;if(!record||!documentId||!Number.isInteger(page)||page<1||page>(pageCount||500))return;
  $('document-page').value=page;$('document-prev').disabled=page<=1;$('document-next').disabled=pageCount!==null&&page>=pageCount;
  const src=PDF+'?'+new URLSearchParams({id:record.candidate_id,document:documentId})+'#page='+page;
  let frame=$('document-viewer').querySelector('iframe');if(!frame){frame=el('iframe');frame.title='PDF originale conservato';$('document-viewer').append(frame)}frame.src=src;
  $('document-text').textContent='';$('document-text-status').textContent='Caricamento del testo della pagina…';
  try{const p=await read({id:record.candidate_id,document:documentId,page});if(serial!==pageGeneration)return;
   $('document-text').textContent=p.text;$('document-text-status').textContent='Pagina '+p.page+' · '+(p.extraction_method==='ocr'?'Testo ottenuto mediante OCR':'Estrazione nativa dal PDF');
  }catch(e){if(serial===pageGeneration)$('document-text-status').textContent='Testo della pagina non disponibile o non ancora verificato. Il PDF può essere consultato nel lettore.'}
 }
 async function openPaper(id){const serial=++generation;++pageGeneration;documentId=null;record=null;$('document-status').textContent='Caricamento del documento…';$('document-viewer').replaceChildren();$('document-text').textContent='';$('document-navigation').hidden=true;$('document-detail').hidden=true;
  try{const r=await read({id});if(serial!==generation)return;record=r;$('document-detail').hidden=false;$('document-title').textContent=r.title;$('document-bibliography').textContent=[r.authors,r.publication_year,r.venue,r.doi].filter(Boolean).join(' · ');$('document-versions').replaceChildren();
   for(const d of r.documents){const box=el('article');box.append(el('strong',d.version),el('p',rights[d.rights_status]||'Diritti non verificati'));
    if(d.public_downloadable&&d.document_id){const b=el('button','Leggi questa versione');b.type='button';b.onclick=()=>{documentId=d.document_id;pageCount=d.page_count;$('document-navigation').hidden=false;$('document-page-count').textContent=pageCount?'di '+pageCount:'— numero di pagine non verificato';showPage(1)};box.append(b)}
    if(d.source_url){const a=el('a',' Apri la fonte originale');a.href=d.source_url;a.target='_blank';a.rel='noopener noreferrer';box.append(a)}
    if(d.attribution)box.append(el('p',d.attribution));$('document-versions').append(box);
   }
   if(!r.documents.length){$('document-versions').append(el('p','Nessun full text conservato è verificato per questa versione del record.'));for(const url of r.source_urls){const a=el('a','Consulta la fonte esterna');a.href=url;a.rel='noopener noreferrer';a.target='_blank';$('document-versions').append(a)}}
   const curator=el('a','Consulta le copie riservate nella console');curator.href=ORIGIN+'/enrichment.html?candidate='+encodeURIComponent(id);curator.rel='noopener noreferrer';$('document-versions').append(curator);
   $('document-status').textContent='Disponibilità e diritti verificati sullo stato corrente dell’archivio.';
   if(globalThis.CILEPaperResearch)globalThis.CILEPaperResearch.load($('document-research'),{id,title:r.title,doi:r.doi,sourceLinks:r.source_urls},()=>serial===generation);
   const sameSelection=params.get('candidate')===id;const evidence=sameSelection?params.get('evidence'):null,revision=sameSelection?params.get('revision'):null;
   if(evidence&&revision){const resolved=await read({id,evidence,revision});if(serial!==generation)return;const hit=resolved.evidence?.[0];if(hit?.document_id){documentId=hit.document_id;pageCount=r.documents.find(d=>d.document_id===documentId)?.page_count||null;$('document-navigation').hidden=false;$('document-page-count').textContent=pageCount?'di '+pageCount:'';showPage(hit.pages[0])}else $('document-status').textContent='Il passaggio non è disponibile pubblicamente: '+(hit?.blocker||'localizzazione non verificata')}
   else {const wanted=sameSelection?params.get('document'):null,d=r.documents.find(d=>d.document_id===wanted&&d.public_downloadable)||r.documents.find(d=>d.public_downloadable);if(d){documentId=d.document_id;pageCount=d.page_count;$('document-navigation').hidden=false;$('document-page-count').textContent=pageCount?'di '+pageCount:'';showPage(sameSelection?(Number(params.get('page'))||1):1)}}
  }catch(e){if(serial===generation)$('document-status').textContent=e.message}
 }
 $('document-search').addEventListener('submit',e=>{e.preventDefault();search()});$('document-more').onclick=()=>search(true);
 $('document-prev').onclick=()=>showPage(Number($('document-page').value)-1);$('document-next').onclick=()=>showPage(Number($('document-page').value)+1);$('document-page').onchange=()=>showPage(Number($('document-page').value));
 if(params.get('candidate'))openPaper(params.get('candidate'));else search();
})();
