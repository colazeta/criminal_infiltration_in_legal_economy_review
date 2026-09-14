/* Same current-receipt predicate as archive filter and sheet; no private API. */
(() => {
  const status=document.getElementById('enrichment-statistics-status'),button=document.getElementById('enrichment-statistics-refresh');
  if(!status||!button||!globalThis.CILEPaperProcessing)return;
  const P=globalThis.CILEPaperProcessing;let busy=false;
  async function refresh(){if(busy)return;busy=true;button.disabled=true;status.textContent='Verifica dell’indice pubblico in corso.';
    try{const register=await P.readJSON('./data/paper-register.json');if(register.schemaVersion!==1||!Array.isArray(register.records))throw Error('invalid_register');
      const index=P.createIndex(register.records,{selectSupport:()=>({readingAid:null}),onUpdate:()=>{}});await index.scan();
      const rows=[...index.rows.values()],p=index.progress,completed=rows.filter(P.isCompleted).length,proposed=rows.filter(r=>r.research==='available').length,full=rows.filter(r=>r.research==='available'&&r.coverage==='full_text').length;
      const verified=p.checked===p.total&&!p.errors;
      status.textContent=`${completed} arricchimenti validati / ${p.total} record registrati. ${verified?(p.total?('Percentuale: '+(100*completed/p.total).toFixed(1)+'%.'):'Percentuale non applicabile: registro vuoto.'):'Verifica incompleta: nessuna percentuale finale.'} Proposte disponibili: ${proposed}; proposte sul testo integrale: ${full}. Stati verificati: ${p.checked}/${p.total}. Osservazione: ${new Date().toISOString()}. I conteggi degli stadi sono indipendenti.`;
    }catch{status.textContent='Avanzamento non verificabile in questo momento. Non equivale a zero analisi.'}finally{busy=false;button.disabled=false}
  }
  button.addEventListener('click',refresh);refresh();
})();
