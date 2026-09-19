/* One immutable public reading edition. No research is generated in the browser. */
(() => {
  'use strict';
  const VERSION='CILE-READING-SNAPSHOT-1';
  const CLASSES=['aetiology','diagnosis','screening','therapy','prognosis','prevention'];
  const LABELS={aetiology:'Eziologia',diagnosis:'Diagnosi',screening:'Screening',therapy:'Terapia',prognosis:'Prognosi',prevention:'Prevenzione'};
  const FIELDS=['id','title','authors','year','venue','doi','sourceLinks','metadataStatus','reviewStatus','accessStatus','registeredAt','topicCode'];
  const STATES=['available','absent','unavailable','withheld','identity_mismatch'];
  const canonical=value=>JSON.stringify(sort(value));
  function sort(value){
    if(Array.isArray(value))return value.map(sort);
    if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().map(key=>[key,sort(value[key])]));
    return value;
  }
  function sameCandidate(a,b){
    return Boolean(a&&b&&FIELDS.every(key=>key==='sourceLinks'?
      Array.isArray(a[key])&&Array.isArray(b[key])&&canonical([...a[key]].sort())===canonical([...b[key]].sort()):a[key]===b[key]));
  }
  function assert(condition,message){if(!condition)throw Error(message);}
  function exact(object,keys){assert(object&&typeof object==='object'&&!Array.isArray(object)&&Object.keys(object).length===keys.length&&keys.every(k=>Object.hasOwn(object,k)),'snapshot_shape');}
  function validate(snapshot){
    exact(snapshot,['schemaVersion','projectionVersion','generatedAt','sourceCommit','digest','records']);
    assert(snapshot.schemaVersion===1&&snapshot.projectionVersion===VERSION,'snapshot_version');
    assert(/^[a-f0-9]{64}$/.test(snapshot.digest)&&/^[a-f0-9]{40}$/.test(snapshot.sourceCommit),'snapshot_revision');
    assert(Number.isFinite(Date.parse(snapshot.generatedAt)),'snapshot_date');
    assert(Array.isArray(snapshot.records)&&snapshot.records.length<=10000,'snapshot_records');
    const ids=new Set();
    for(const row of snapshot.records){
      exact(row,['candidate','support','manualStatus','manual','researchStatus','research','validationStatus','validation']);
      exact(row.candidate,FIELDS);
      const id=row.candidate.id;
      assert(typeof id==='string'&&/^CAND-[A-Za-z0-9-]{1,100}$/.test(id)&&!ids.has(id),'snapshot_identity');ids.add(id);
      assert(typeof row.candidate.title==='string'&&Array.isArray(row.candidate.sourceLinks),'snapshot_bibliography');
      assert(STATES.includes(row.manualStatus)&&STATES.includes(row.researchStatus)&&STATES.includes(row.validationStatus),'snapshot_state');
      assert((row.manualStatus==='available')===(row.manual!==null),'snapshot_manual_state');
      assert((row.validationStatus==='available')===(row.validation!==null),'snapshot_validation_state');
      if(row.support){assert(row.support.id===id,'snapshot_support_identity');for(const k of ['title','authors','year','venue','doi'])assert(row.support.bibliography[k]===row.candidate[k],'snapshot_support_revision');}
      if(row.manual){
        exact(row.manual,['schema_version','assessment_state','candidate_id','issue_number','comment_url','updated_at','classes','structured','roles','provenance']);
        exact(row.manual.roles,['primary','secondary']);
        exact(row.manual.provenance,['sha256','comment_id','identity_basis']);
        exact(row.manual.structured,['overview','framework','studies','datasets','methods','variables','findings','sources']);
        for(const key of ['overview','framework','findings']){assert(Array.isArray(row.manual.structured[key]),'manual_fields');for(const pair of row.manual.structured[key])assert(Array.isArray(pair)&&pair.length===2&&pair.every(v=>typeof v==='string'),'manual_fields');}
        for(const key of ['datasets','variables','sources'])assert(Array.isArray(row.manual.structured[key])&&row.manual.structured[key].every(v=>typeof v==='string'),'manual_fields');
        for(const key of ['studies','methods']){assert(Array.isArray(row.manual.structured[key]),'manual_groups');for(const group of row.manual.structured[key]){exact(group,['title','rows']);assert(typeof group.title==='string'&&Array.isArray(group.rows)&&group.rows.every(pair=>Array.isArray(pair)&&pair.length===2&&pair.every(v=>typeof v==='string')),'manual_groups');}}
        assert(row.manual.candidate_id===id&&row.manual.assessment_state==='unreviewed_manual_support','snapshot_manual_identity');
        assert(row.manual.roles&&[null,...CLASSES].includes(row.manual.roles.primary)&&Array.isArray(row.manual.roles.secondary)&&row.manual.roles.secondary.every(k=>CLASSES.includes(k)),'snapshot_manual_roles');
        assert(row.manual.provenance&&/^[a-f0-9]{64}$/.test(row.manual.provenance.sha256),'snapshot_manual_provenance');
      }
      if(row.research){
        const c=row.research.candidate;
        assert(row.research.projection_version==='CILE-PUBLIC-RESEARCH-1','snapshot_research_version');
        assert(row.research.availability==='not_registered'&&c===null||c&&c.id===id&&c.title===row.candidate.title&&String(c.doi||'').toLowerCase()===String(row.candidate.doi||'').toLowerCase()&&canonical([...c.sourceLinks].sort())===canonical([...row.candidate.sourceLinks].sort()),'snapshot_research_identity');
        assert((row.researchStatus==='available')===(row.research.availability==='available'),'snapshot_research_state');
      }else assert(row.researchStatus!=='available','snapshot_missing_research');
      if(row.validation)assert(row.validation.candidate_id===id&&(!row.validation.completed||row.researchStatus==='available'&&row.validation.research_revision===row.research.revision),'snapshot_validation_identity');
    }
    return snapshot;
  }
  function freeze(value){if(value&&typeof value==='object'&&!Object.isFrozen(value)){Object.values(value).forEach(freeze);Object.freeze(value);}return value;}
  async function verify(snapshot){
    validate(snapshot);const {digest,...body}=snapshot;
    const actual=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonical(body)))),b=>b.toString(16).padStart(2,'0')).join('');
    assert(actual===digest,'snapshot_digest');return snapshot;
  }
  function classification(row){
    const r=row.researchStatus==='available'?row.research.research:null;
    const s=r?.framework,m=row.manual?.roles;
    const structured=s?.status==='proposed'?{primary:s.primary,secondary:s.secondary.map(x=>x.category),origin:'structured'}:null;
    const manual=m?.primary?{primary:m.primary,secondary:m.secondary,origin:'annotation'}:null;
    if(structured&&manual&&structured.primary!==manual.primary)return {state:'conflicting_proposals',primary:null,secondary:[],origin:null};
    if(s&&s.status!=='proposed')return {state:s.status,primary:null,secondary:[],origin:'structured'};
    const selected=structured||manual;
    return selected?{state:'classified',...selected}:{state:'not_assessed',primary:null,secondary:[],origin:null};
  }
  function summary(snapshot,records=snapshot.records.map(r=>r.candidate)){
    const byId=new Map(snapshot.records.map(row=>[row.candidate.id,row]));
    const result={total:records.length,synopses:0,annotations:0,structured:0,researchContent:0,anyContent:0,classified:0,conflicts:0,fullText:0,validated:0,unknown:0,unknownValidation:0,generatedAt:snapshot.generatedAt,digest:snapshot.digest};
    for(const record of records){
      const row=byId.get(record.id);if(!sameCandidate(row?.candidate,record)){result.unknown++;continue;}
      const synopsis=Boolean(row.support?.readingAid?.synopsis&&row.support.readingAid.kind!=='metadata_warning');
      const manual=row.manualStatus==='available',research=row.researchStatus==='available';
      result.synopses+=Number(synopsis);result.annotations+=Number(manual);result.structured+=Number(research);
      result.researchContent+=Number(manual||research);result.anyContent+=Number(synopsis||manual||research);
      result.fullText+=Number(research&&row.research.research.source_coverage==='full_text');
      result.validated+=Number(row.validationStatus==='available'&&row.validation.completed===true);
      const c=classification(row);result.classified+=Number(c.state==='classified');result.conflicts+=Number(c.state==='conflicting_proposals');
      if(['unavailable','identity_mismatch'].includes(row.validationStatus))result.unknownValidation++;
      if([row.manualStatus,row.researchStatus,row.validationStatus].some(s=>['unavailable','identity_mismatch'].includes(s)))result.unknown++;
    }
    return result;
  }
  let current=null,promise=null;
  async function load(){
    if(current)return current;if(promise)return promise;
    promise=(async()=>{
      const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),20000);
      try{
        const response=await fetch('./reading-snapshot.json',{cache:'no-cache',credentials:'omit',signal:controller.signal});
        if(!response.ok)throw Error('snapshot_unavailable');
        const raw=await response.text();assert(raw.length<=30000000,'snapshot_size');
        current=freeze(await verify(JSON.parse(raw)));return current;
      }finally{clearTimeout(timer);promise=null;}
    })();return promise;
  }
  async function record(candidate){
    const snapshot=await load(),row=snapshot.records.find(r=>r.candidate.id===candidate.id);
    assert(sameCandidate(row?.candidate,candidate),'snapshot_candidate_changed');return row;
  }
  function date(value){return new Intl.DateTimeFormat('it-IT',{dateStyle:'short',timeStyle:'short'}).format(new Date(value));}
  function describeEdition(snapshot){const s=summary(snapshot);return `Contenuti pubblicati il ${date(snapshot.generatedAt)}.${s.unknown?' Alcune fonti non sono state acquisite: i conteggi disponibili sono parziali.':''}`;}
  function index(records,onUpdate){
    const rows=new Map(records.map(r=>[r.id,{support:'pending',summary:false,research:'pending',manual:false,classes:[],completionVerified:false}]));
    const progress={total:records.length,checked:0,errors:0,running:false,scanned:false};
    const out={rows,progress,records,snapshot:null,loadSupport:()=>scan(),scan};let pending=null;
    function scan(){
      if(pending)return pending;
      progress.running=true;progress.scanned=false;progress.checked=0;progress.errors=0;out.snapshot=null;onUpdate();
      pending=load().then(snapshot=>{
        const byId=new Map(snapshot.records.map(r=>[r.candidate.id,r]));
        for(const candidate of records){
          const row=byId.get(candidate.id);if(!sameCandidate(row?.candidate,candidate)){progress.errors++;continue;}
          const r=row.research?.research,c=classification(row),completion=row.validation;
          rows.set(candidate.id,{support:row.support?'checked':'error',summary:Boolean(row.support?.readingAid?.synopsis&&row.support.readingAid.kind!=='metadata_warning'),
            research:row.research?.availability||(row.researchStatus==='absent'?'not_assessed':row.researchStatus==='withheld'?'withheld':'error'),manual:row.manualStatus==='available',manualStatus:row.manualStatus,
            automated:r?.generation_kind==='automated',coverage:r?.source_coverage||null,classes:c.primary?[c.primary,...c.secondary]:[],classificationState:c.state,
            researchRevision:row.research?.revision||null,completion,completionVerified:row.validationStatus==='available',referenceCoverage:completion?.reference_coverage||[]});
          progress.checked++;
        }
        out.snapshot=snapshot;
      }).catch(()=>{progress.errors++;}).finally(()=>{progress.running=false;progress.scanned=true;pending=null;onUpdate();});return pending;
    }
    return out;
  }
  async function categoryRows(){
    const snapshot=await load(),rows=new Map();
    for(const row of snapshot.records){const c=classification(row);rows.set(row.candidate.id,{id:row.candidate.id,candidate:row.candidate,
      availability:c.primary||['outside_framework','insufficient_evidence'].includes(c.state)?'available':c.state==='conflicting_proposals'?'withheld':'not_assessed',
      frameworkStatus:c.primary?'proposed':c.state,primary:c.primary,secondary:c.secondary,origin:c.origin});}return rows;
  }
  globalThis.CILEArchiveSnapshot={VERSION,canonical,sameCandidate,validate,verify,classification,summary,load,record,index,categoryRows,date,describeEdition,LABELS};
})();
