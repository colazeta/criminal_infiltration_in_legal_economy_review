import {addStarvationCases} from './starvation-cases.mjs';
// The oracle below is authored from the pinned prose contracts, never from the SUT.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url), YAML=require('yaml');
const root=path.dirname(fileURLToPath(import.meta.url));
const pilot=fs.existsSync(path.join(root,'pilot'))?path.join(root,'pilot'):path.join(root,'../control-plane');
const base={activation_id:'synthetic',lane:'A',scheduled_at:'2026-09-19T09:10:00+02:00',scouting_due:false,unfinished_safe_write:false,active_wip_count:3,candidate_present:false,metadata_source_ready:false,fulltext_ready:false,proposal_persisted:false,mandatory_fields_accounted:false,framework_assessed:false,independent_comparison_ready:false,references_ready:false,limitations_caveats_ready:false,version_guards_match:false,validation_ready:false,validated:false,writer_ready:false,calibration_case_ready:false,identity_debt_due:false,engineering_blocker:false,repeat_without_changed_prerequisite:false};
const f0={candidate_present:true,metadata_source_ready:true};
const f1={...f0,fulltext_ready:true};
const f2={...f1,proposal_persisted:true};
const f3={...f2,independent_comparison_ready:true};
const f4={...f3,references_ready:true};
const f5={...f4,mandatory_fields_accounted:true,framework_assessed:true,limitations_caveats_ready:true,version_guards_match:true};
const f6={...f5,validation_ready:true}, f7={...f6,validated:true};
const status=(frontier_gate,next_gate,assessment_completed=false,validation_accepted=false,assessment_distance_to_f5)=>({frontier_gate,next_gate,frontier_consistent:true,assessment_completed,validation_accepted,...(assessment_distance_to_f5===undefined?{}:{assessment_distance_to_f5})});
const statuses={none:status('NONE','F0_METADATA_SOURCE'),f0:status('F0_METADATA_SOURCE','F1_FULLTEXT_READY',false,false,5),f1:status('F1_FULLTEXT_READY','F2_PROPOSAL_PERSISTED',false,false,4),f2:status('F2_PROPOSAL_PERSISTED','F3_INDEPENDENT_COMPARISON',false,false,3),f3:status('F3_INDEPENDENT_COMPARISON','F4_REFERENCES_READY',false,false,2),f4:status('F4_REFERENCES_READY','F5_ASSESSMENT_COMPLETE',false,false,1),f5:status('F5_ASSESSMENT_COMPLETE','F6_VALIDATION_READY',true,false,0),f6:status('F6_VALIDATION_READY','F7_VALIDATED',true,false,0),f7:status('F7_VALIDATED','NONE',true,true,0)};
const cases=[];
function add(id,kind,patch,expected,contract,note='',frontierInput){cases.push({id,origin:'synthetic',kind,input:{...base,...patch,activation_id:`synthetic-${id}`},expected,contract,note,...(frontierInput?{frontierInput}:{})});}
function route(id,patch,expectedRoute,profile='none',contract='completion-first-v5.md: Lane routing',note='') {add(id,'pipeline',patch,{route:expectedRoute,side_effect_authorized:false,pilot_mode:'observe_only'},contract,note,statuses[profile]);}
for(const lane of ['A','B']) {
 const x={lane,scheduled_at:lane==='A'?'2026-09-19T09:10:00+02:00':'2026-09-19T21:40:00+02:00'};
 route(`${lane}-scout`,{...x,scouting_due:true},'SCOUT');
 route(`${lane}-persist`,{...x,unfinished_safe_write:true},'PERSIST');
 route(`${lane}-complete`,{...x,...f2,writer_ready:true},'COMPLETE','f2');
 route(`${lane}-calibration`,{...x,...f5,calibration_case_ready:true},'CALIBRATION_CASE','f5');
 route(`${lane}-resolve`,{...x,identity_debt_due:true},'RESOLVE');
 route(`${lane}-engineering`,{...x,engineering_blocker:true},lane==='B'?'ENGINEER':'NOOP');
 route(`${lane}-noop`,x,'NOOP');
 for(const wip of [0,5,6,7])route(`${lane}-wip-${wip}`,{...x,...f2,writer_ready:true,active_wip_count:wip},wip===7?'BLOCKED':'COMPLETE','f2','completion-first-v5.md: WIP limit; integration-contract.md: Side-effect boundary');
 route(`${lane}-writer-unavailable`,{...x,...f2},'NOOP','f2','completion-first-v5.md: Persistence prerequisite');
 route(`${lane}-repeat-blocked`,{...x,...f2,writer_ready:true,repeat_without_changed_prerequisite:true},'NOOP','f2','hourly-hybrid-v4.md: Anti-repeat rule');
 route(`${lane}-changed-prerequisite`,{...x,...f2,writer_ready:true,repeat_without_changed_prerequisite:false},'COMPLETE','f2','hourly-hybrid-v4.md: Anti-repeat rule','Paired synthetic state after a changed prerequisite; no persisted history is claimed.');
 route(`${lane}-repeat-other-route`,{...x,...f2,writer_ready:true,repeat_without_changed_prerequisite:true,calibration_case_ready:true},'CALIBRATION_CASE','f2','integration-contract.md: Routing contract','The repeated COMPLETE strategy is blocked; this synthetic calibration activity is a different safe strategy.');
 route(`${lane}-scout-priority`,{...x,...f2,writer_ready:true,scouting_due:true,unfinished_safe_write:true,calibration_case_ready:true,engineering_blocker:true},'SCOUT','f2');
 route(`${lane}-persist-priority`,{...x,...f2,writer_ready:true,unfinished_safe_write:true,calibration_case_ready:true,identity_debt_due:true,engineering_blocker:true},'PERSIST','f2');
 route(`${lane}-complete-priority`,{...x,...f2,writer_ready:true,calibration_case_ready:true,engineering_blocker:true},'COMPLETE','f2');
 route(`${lane}-calibration-priority`,{...x,...f5,calibration_case_ready:true,engineering_blocker:true},'CALIBRATION_CASE','f5');
 route(`${lane}-resolve-priority`,{...x,identity_debt_due:true,engineering_blocker:true},'RESOLVE');
 route(`${lane}-starvation-over-complete`,{...x,...f2,writer_ready:true,identity_debt_due:true},'RESOLVE','f2','hourly-hybrid-v4.md: RESOLVE starvation guard','Conditional mapping: identity_debt_due=true denotes the mandatory 24h/20-observation starvation guard. The schema lacks age/count and new-versus-in-flight research.');
 route(`${lane}-scout-wip-collision`,{...x,scouting_due:true,active_wip_count:7},'BLOCKED','none','integration-contract.md: explicit WIP fail-closed guarantee','Pilot guarantee probe. Review gives SCOUT priority; scope of the guard requires clarification, not an automatic fix.');
 route(`${lane}-persist-wip-collision`,{...x,unfinished_safe_write:true,active_wip_count:7},'BLOCKED','none','integration-contract.md: explicit WIP fail-closed guarantee','Pilot guarantee probe. Review requires finishing safe in-flight writes; do not change this precedence without resolving the contract.');
 for(const first of ['none','scout','persist']){
  const invalid={...x,candidate_present:false,fulltext_ready:true,...(first==='scout'?{scouting_due:true}:first==='persist'?{unfinished_safe_write:true}:{})};
  add(`${lane}-inconsistent-${first}`,'pipeline',invalid,{route:'BLOCKED',side_effect_authorized:false,pilot_mode:'observe_only'},'integration-contract.md: inconsistent states fail closed',first==='none'?'':'Pilot guard collision with a higher-priority route.',{...statuses.none,frontier_consistent:false,inconsistency_code:'candidate_absent_with_frontier_state'});
 }
}
// Owner clarification, 2026-09-19: SCOUT/PERSIST may bypass a blocker only
// if independent of both the incoherent frontier and ordinary assessment WIP.
for(const lane of ['A','B'])for(const activity of ['scout','persist'])for(const hazard of ['wip','inconsistent','both']){
 const patch={lane,scheduled_at:lane==='A'?'2026-09-19T09:10:00+02:00':'2026-09-19T21:40:00+02:00',[activity==='scout'?'scouting_due':'unfinished_safe_write']:true,[`${activity}_independent_of_frontier_and_wip`]:true,...(hazard!=='inconsistent'?{active_wip_count:7}:{}),...(hazard!=='wip'?{fulltext_ready:true}: {})};
 const frontier=hazard==='wip'?statuses.none:{...statuses.none,frontier_consistent:false,inconsistency_code:'candidate_absent_with_frontier_state'};
 add(`${lane}-${activity}-independent-${hazard}`,'pipeline',patch,{route:activity==='scout'?'SCOUT':'PERSIST',side_effect_authorized:false,pilot_mode:'observe_only'},'Owner decision 2026-09-19; integration-contract.md: independent SCOUT/PERSIST exception','Synthetic explicit attestation; no real preflight or external action is claimed.',frontier);
}
for(const lane of ['A','B'])for(const activity of ['scout','persist']){
 const other=activity==='scout'?'persist':'scout';
 add(`${lane}-${activity}-wrong-attestation`,'pipeline',{lane,fulltext_ready:true,active_wip_count:7,[activity==='scout'?'scouting_due':'unfinished_safe_write']:true,[`${activity}_independent_of_frontier_and_wip`]:false,[`${other}_independent_of_frontier_and_wip`]:true},{route:'BLOCKED',side_effect_authorized:false,pilot_mode:'observe_only'},'Owner decision 2026-09-19; attestation is route-specific','False or a flag for a different activity cannot bypass the guard.',{...statuses.none,frontier_consistent:false,inconsistency_code:'candidate_absent_with_frontier_state'});
}
for(const [name,flags] of Object.entries({none:{},f0,f1,f2,f3,f4,f5,f6,f7}))add(`frontier-${name}`,'frontier',flags,statuses[name],'completion-first-v5.md: Assessment-completion frontier and predicate');
for(const flag of ['mandatory_fields_accounted','framework_assessed','limitations_caveats_ready','version_guards_match'])add(`missing-${flag}`,'frontier',{...f5,[flag]:false},statuses.f4,'completion-first-v5.md: eight-part assessment-complete predicate');
for(const [id,flags] of Object.entries({absent_dirty:{fulltext_ready:true},fulltext_without_metadata:{candidate_present:true,fulltext_ready:true},proposal_without_fulltext:{...f0,proposal_persisted:true},comparison_without_proposal:{...f1,independent_comparison_ready:true},references_without_comparison:{...f2,references_ready:true},validation_before_completion:{...f2,validation_ready:true}}))add(id,'frontier',flags,{frontier_consistent:false,assessment_completed:false,validation_accepted:false},'integration-contract.md: inconsistent states fail closed');
add('validated-without-ready','frontier',{...f5,validated:true},{frontier_consistent:false,validation_accepted:false},'completion-first-v5.md: F7 requires current accepted prerequisites','Fail-closed output probe: accepted must not be true for an incoherent validation state.');
add('validated-stale-versions','frontier',{...f7,version_guards_match:false},{frontier_consistent:false,assessment_completed:false,validation_accepted:false},'completion-first-v5.md: F7 remains current and version guards match');
const invalid=[['negative-wip',{active_wip_count:-1}],['fractional-wip',{active_wip_count:6.5}],['invalid-lane',{lane:'C'}],['timestamp-object',{scheduled_at:{date:'2026-09-19'}}],['string-boolean',{writer_ready:'true'}],['unknown-property',{extra:true}],['missing-writer',{}]];
for(const [id,patch]of invalid){const input={...base,...patch};if(id==='missing-writer')delete input.writer_ready;cases.push({id,origin:'synthetic',kind:'schema-rejection',input,expected:{valid:false},contract:'Release Process: ActivationInput JSON schema'});}
addStarvationCases(cases);
// Retire only the two byte-identical archived native fixtures, never arbitrary tests.
for(const lane of ['A','B']) {
 const name=`replay-${lane}-starvation-over-complete.yaml`;
 const stale=path.join(pilot,'tests',name);
 if(fs.existsSync(stale)) {
  const archived=path.join(root,'history/native-original',name);
  if(!fs.readFileSync(stale).equals(fs.readFileSync(archived)))throw Error(`Historical fixture changed: ${name}`);
  fs.unlinkSync(stale);
 }
}
fs.writeFileSync(path.join(root,'cases.json'),JSON.stringify(cases,null,2)+'\n');
// Native router inputs use the independently authored frontier table, never evaluateFrontier output.
for(const c of cases.filter(c=>c.kind!=='schema-rejection')){
 const node=c.kind==='frontier'?'evaluate-frontier':'route-activation';
 const input=c.kind==='frontier'?c.input:{...c.input,...c.frontierInput};
 const doc={apiVersion:'kora/v1',kind:'Test',metadata:{name:`replay-${c.id}`},spec:{target:{workflow:'cile-hourly-control-plane',node},input:{inline:input},checks:[{type:'schema',gate:true},...Object.entries(c.expected).map(([key,expected])=>({type:'exact',gate:true,path:`$.${key}`,expected}))]}};
 fs.writeFileSync(path.join(pilot,'tests',`replay-${c.id}.yaml`),YAML.stringify(doc,{defaultStringType:'QUOTE_DOUBLE'}));
}
console.log(JSON.stringify({cases:cases.length,nativeAdded:cases.filter(c=>c.kind!=='schema-rejection').length}));
