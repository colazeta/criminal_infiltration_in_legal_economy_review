/* Counts describe research records; loading describes only this page. */
(() => {
  'use strict';
  const status=document.getElementById('enrichment-statistics-status'),button=document.getElementById('enrichment-statistics-refresh');
  if(!status||!button||!globalThis.CILEPaperProcessing)return;
  const P=globalThis.CILEPaperProcessing;
  const counts=document.createElement('p');counts.id='enrichment-statistics-counts';counts.hidden=true;status.after(counts);
  let busy=false;
  function display(index){
    const view=P.analysisSummary(index);status.textContent=view.text;
    counts.hidden=!view.counts;counts.textContent='';
    if(view.counts){const c=view.counts;
      counts.textContent=`Analisi dettagliate: ${c.analyses}. Basate sul testo completo: ${c.fullText}. Completamento registrato: ${c.completed} su ${view.denominator} paper con dati caricati.`;
      if(view.percentage!==null)counts.textContent+=` Quota con completamento registrato: ${new Intl.NumberFormat('it-IT',{maximumFractionDigits:1}).format(view.percentage)}%.`;
    }
  }
  async function refresh(){
    if(busy)return;busy=true;button.disabled=true;status.textContent='Caricamento dello stato delle analisi…';
    counts.hidden=true;counts.textContent='';status.setAttribute('aria-busy','true');
    try{
      const register=await P.readJSON('./data/paper-register.json');
      if(register.schemaVersion!==1||!Array.isArray(register.records))throw Error('invalid_register');
      let index;index=P.createIndex(register.records,{selectSupport:()=>({readingAid:null}),onUpdate:()=>{if(index)display(index);}});
      await index.scan();display(index);
    }catch{status.textContent='Impossibile caricare lo stato delle analisi. Riprova.';counts.hidden=true;counts.textContent='';}
    finally{busy=false;button.disabled=false;button.textContent='Aggiorna dati delle analisi';status.setAttribute('aria-busy','false');}
  }
  button.addEventListener('click',refresh);refresh();
})();
