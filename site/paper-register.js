(() => {
  const list=document.querySelector('#registered-papers');
  const search=document.querySelector('#register-search');
  const count=document.querySelector('#register-count');
  const labels={pending:'Da analizzare',needs_full_text:'Testo da esaminare',screened_eligible_core:'Valutato: core',screened_eligible_contextual:'Valutato: contestuale',screened_not_eligible:'Escluso',duplicate_confirmed:'Duplicato confermato',screened_not_academic:'Non accademico',screened_not_retrievable:'Non reperibile'};
  let records=[];
  const el=(tag,text)=>{const n=document.createElement(tag);n.textContent=text;return n;};
  function render(){
    const q=search.value.trim().toLocaleLowerCase('it');
    const found=records.filter(r=>[r.title,r.authors,r.doi,r.year].join(' ').toLocaleLowerCase('it').includes(q));
    count.textContent=`${found.length} record visualizzati · ${records.length} registrati. Lavori da analizzare, non inclusioni scientifiche automatiche.`;
    list.replaceChildren();
    for(const r of found){
      const tr=document.createElement('tr');
      const citation=document.createElement('td');citation.append(el('strong',r.title),el('p',[r.authors,r.year,r.venue].filter(Boolean).join(' · ')||'Metadati da completare'));
      const status=el('td',labels[r.reviewStatus]||'Da verificare');
      status.append(el('p',r.metadataStatus==='metadata_verified'?'Metadati verificati':'Metadati da verificare'));
      const access=el('td',r.accessStatus==='verified_open'?'OA verificato all’acquisizione':'Accesso da verificare');
      const links=document.createElement('td');
      for(const [i,url] of r.sourceLinks.entries()){
        const parsed=new URL(url);if(!['https:','http:'].includes(parsed.protocol)||parsed.username||parsed.password)continue;
        const a=el('a',`Fonte ${i+1}`);a.href=url;a.rel='noreferrer';links.append(a,el('br',''));
      }
      const review=el('a','Analizza nel curatore');review.href='./curate.html';links.append(review);
      tr.append(citation,status,access,links);list.append(tr);
    }
    if(!found.length){const tr=document.createElement('tr');const td=el('td',records.length?'Nessun risultato per questa ricerca.':'Nessun lavoro ancora registrato.');td.colSpan=4;tr.append(td);list.append(tr);}
  }
  search.addEventListener('input',render);
  fetch('./data/paper-register.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('register unavailable');return r.json();}).then(p=>{records=p.records;render();}).catch(()=>{if(!list.children.length) count.textContent='Il registro non è disponibile. Consultare il pannello del curatore o riprovare.'; else search.disabled=true;});
})();
