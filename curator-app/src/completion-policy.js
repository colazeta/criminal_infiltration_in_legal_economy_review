/* Explicit assessed-field policy; never a scientific decision. */
import policy from '../../ontology/modules/completion-policy.json' with {type:'json'};
export const COMPLETION_POLICY=policy.version;
export function inspectCompletionFacts(input) {
  const out={total:0,unresolved:0,optional_unresolved:0,unresolved_paths:[],optional_unresolved_paths:[]};
  for(const group of Object.keys(policy.mandatory)) {
    const records=group==='root'?[input]:input[group];
    if(!Array.isArray(records))throw Error('completion_group_missing');
    for(const [index,record] of records.entries()) {
      for(const kind of ['mandatory','optional'])for(const name of policy[kind][group]) {
        const fact=record[name],path=group==='root'?name:`${group}[${index}].${name}`;
        if(!fact||!['reported','not_reported','not_applicable','not_verifiable','ambiguous'].includes(fact.status))throw Error('completion_fact_missing:'+path);
        out.total++;
        if(['not_verifiable','ambiguous'].includes(fact.status)) {
          if(kind==='mandatory'){out.unresolved++;out.unresolved_paths.push(path)}
          else{out.optional_unresolved++;out.optional_unresolved_paths.push(path)}
        }
      }
    }
  }
  return out;
}
export function validateFrameworkAssessment(framework) {
  if(!framework||!policy.framework_outcomes.includes(framework.status))throw Error('framework_assessment_required');
  const rationale=framework.rationale;
  if(!rationale||rationale.status!=='reported'||rationale.origin!=='analyst'||!rationale.value?.trim()||!rationale.evidence_span_ids?.length)throw Error('framework_grounded_rationale_required');
  if(framework.status==='outside_framework'&&(framework.primary!==null||framework.secondary?.length||framework.alternative!==null))throw Error('outside_framework_cannot_assign_categories');
  return framework.status;
}

export function groupReviewTemplate(input) {
  return Object.fromEntries(Object.entries(policy.group_assessment_fields).map(([group,key])=>{
    if(!Array.isArray(input[group]))throw Error('completion_group_missing');
    return [key,input[group].length?'recorded':null];
  }));
}
export function validateGroupReview(template,checklist) {
  for(const [key,value]of Object.entries(template)) {
    const accepted=value==='recorded'?checklist[key]==='recorded':policy.group_missingness_outcomes.includes(checklist[key]);
    if(!accepted)throw Error('empty_group_assessment_required:'+key);
  }
}
// A finite set (at most 32) permits validation of the retained checklist hash
// without exposing or re-fetching the private human decision manifest.
export function possibleGroupReviews(input) {
  let choices=[{}];
  for(const [key,value]of Object.entries(groupReviewTemplate(input))) {
    const values=value==='recorded'?['recorded']:policy.group_missingness_outcomes;
    choices=choices.flatMap(row=>values.map(item=>({...row,[key]:item})));
  }
  return choices;
}
