/* The legacy receipt counts validation, not F5 assessment completion. */
(() => {
  'use strict';
  const status=document.getElementById('enrichment-statistics-status'),button=document.getElementById('enrichment-statistics-refresh');
  if(!status||!button||!globalThis.CILEPaperProcessing)return;
  const P=globalThis.CILEPaperProcessing;let busy=false;
  const totals=document.createElement('p');totals.id='enrichment-statistics-totals';totals.hidden=true;
  const validation=document.createElement('p');validation.id='enrichment-statistics-validation';validation.hidden=true;
  status.after(totals,validation);status.setAttribute('aria-atomic','true');
  function clear(){totals.hidden=validation.hidden=true;totals.textContent=validation.textContent='';}
  async function refresh(){
    if(busy)return;
    busy=true;button.disabled=true;button.textContent='Caricamento…';clear();
    status.textContent='Caricamento del riepilogo delle analisi…';
    try{
      const register=await P.readJSON('./data/paper-register.json');
      if(register.schemaVersion!==1||!Array.isArray(register.records))throw Error('invalid_register');
      const index=P.createIndex(register.records,{loadSummaries:false,onUpdate:()=>{}});
      await index.scan();const view=P.overview(index);
      status.textContent=view.message;
      if(view.ready){
        totals.textContent=P.overviewBreakdown(view);
        validation.textContent=`Validazione finale registrata per ${view.validated} di ${view.total} paper. Il numero di analisi completate non è disponibile in questa fonte.`;
        totals.hidden=validation.hidden=false;
      }
      button.textContent=view.action;
    }catch{
      clear();status.textContent='Non è stato possibile caricare il riepilogo delle analisi. Riprova.';
      button.textContent='Riprova caricamento';
    }finally{busy=false;button.disabled=false;}
  }
  button.addEventListener('click',refresh);refresh();
})();
