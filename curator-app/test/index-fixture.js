// Synthetic public transport fixtures, never corpus records or scientific acceptance.
export function indexRow(record,projection={availability:'not_assessed',research:null},accepted=false) {
 const r=projection.research,revision=projection.revision||'a'.repeat(64);
 return {candidate:record,availability:projection.availability,source_coverage:r?.source_coverage||null,generation_kind:r?.generation_kind||null,
  framework_status:r?.framework.status||null,classes:r?.framework.status==='proposed'?[r.framework.primary,...(r.framework.secondary||[]).map(s=>s.category)]:[],research_revision:revision,
  completion:{status:accepted?'accepted':'not_attested',completed:accepted,completed_at:accepted?'2026-09-14T12:00:00Z':null,protocol_version:accepted?'CILE-ENRICH-1':null,codebook_version:accepted?'1.0.0':null,research_revision:r?revision:null,revision:'b'.repeat(64)},reference_coverage:[]};
}
export function indexPage(rows,{total=rows.length,next=null,revision='c'.repeat(64)}={}) {
 return {schema_version:1,projection_version:'CILE-PUBLIC-INDEX-1',index_revision:revision,total,records:rows,next_cursor:next};
}
