/* Counts describe research records; loading describes only this page. */
(() => {
  'use strict';
  const status=document.getElementById('enrichment-statistics-status'),button=document.getElementById('enrichment-statistics-refresh');
  if(!status||!button||!globalThis.CILEPaperProcessing)return;
  const P=globalThis.CILEPaperProcessing;
  const counts=document.createElement('p');counts.id='enrichment-statistics-counts';counts.hidden=true;status.after(counts);
  button.hidden=true;
  let busy=false;
  function display(index){
    const view=P.analysisSummary(index);status.textContent=view.text;
    button.hidden=!['error','partial'].includes(view.phase);
    counts.hidden=!view.counts;counts.textContent='';
    if(view.counts){const c=view.counts;
      counts.textContent=`Analisi dettagliate: ${c.analyses}. Basate sul testo completo: ${c.fullText}. Completamento registrato: ${c.completed} su ${view.denominator} paper con dati caricati.`;
      if(view.percentage!==null)counts.textContent+=` Quota con completamento registrato: ${new Intl.NumberFormat('it-IT',{maximumFractionDigits:1}).format(view.percentage)}%.`;
    }
  }
  async function refresh(){
    if(busy)return;busy=true;button.disabled=true;button.hidden=true;status.textContent='Caricamento dello stato delle analisi…';
    counts.hidden=true;counts.textContent='';status.setAttribute('aria-busy','true');
    try{
      const register=await P.readJSON('./data/paper-register.json');
      if(register.schemaVersion!==1||!Array.isArray(register.records))throw Error('invalid_register');
      let index;index=P.createIndex(register.records,{loadSummaries:false,onUpdate:()=>{if(index)display(index);}});
      await index.scan();display(index);
    }catch{status.textContent='Impossibile caricare lo stato delle analisi. Riprova.';counts.hidden=true;counts.textContent='';button.hidden=false;}
    finally{busy=false;button.disabled=false;button.textContent='Riprova caricamento';status.setAttribute('aria-busy','false');}
  }
  button.addEventListener('click',refresh);refresh();
})();
