// Independent, hand-authored policy examples. No SUT import or output-derived oracle.
export function addStarvationCases(cases) {
  for (const c of cases) {
    if (c.id.endsWith('-starvation-over-complete')) {
      c.classification = 'underspecified_historical';
    } else if (c.expected.route === 'COMPLETE') {
      // Explicit synthetic evidence added for this scenario, not inferred from F3.
      c.input.identity_preflight_evidence = {
        pending_observation_count: 1, oldest_pending_age_seconds: 3600,
        activity_kind: 'new_research', evidence_ref: `synthetic:${c.id}`,
      };
    }
  }
  const evidence = {
    pending_observation_count: 19, oldest_pending_age_seconds: 86399,
    activity_kind: 'new_research', evidence_ref: 'synthetic:threshold-matrix',
  };
  // [name, evidence patch (null = missing object), route, tri-state, input patch]
  const rows = [
    ['below-both', {}, 'COMPLETE', 'not_required'],
    ['fraction-below-24h', {oldest_pending_age_seconds:86399.999}, 'COMPLETE', 'not_required'],
    ['exact-24h', {oldest_pending_age_seconds:86400}, 'RESOLVE', 'required'],
    ['exact-20', {pending_observation_count:20}, 'RESOLVE', 'required'],
    ['above-both', {pending_observation_count:21,oldest_pending_age_seconds:86401}, 'RESOLVE', 'required'],
    ['ongoing-at-both', {pending_observation_count:20,oldest_pending_age_seconds:86400,activity_kind:'in_progress'}, 'COMPLETE', 'not_required'],
    ['non-research-at-both', {pending_observation_count:20,oldest_pending_age_seconds:86400,activity_kind:'non_research'}, 'COMPLETE', 'not_required'],
    ['no-evidence', null, 'BLOCKED', 'undetermined'],
    ['missing-age', {oldest_pending_age_seconds:undefined}, 'BLOCKED', 'undetermined'],
    ['missing-count', {pending_observation_count:undefined}, 'BLOCKED', 'undetermined'],
    ['missing-both', {pending_observation_count:undefined,oldest_pending_age_seconds:undefined}, 'BLOCKED', 'undetermined'],
    ['missing-activity', {activity_kind:undefined}, 'BLOCKED', 'undetermined'],
    ['unknown-activity', {activity_kind:'unknown'}, 'BLOCKED', 'undetermined'],
    ['missing-reference', {evidence_ref:undefined}, 'BLOCKED', 'undetermined'],
    ['null-age', {oldest_pending_age_seconds:null}, 'BLOCKED', 'undetermined'],
    ['null-count', {pending_observation_count:null}, 'BLOCKED', 'undetermined'],
    ['count-sufficient-without-age', {pending_observation_count:20,oldest_pending_age_seconds:undefined}, 'RESOLVE', 'required'],
    ['age-sufficient-without-count', {pending_observation_count:undefined,oldest_pending_age_seconds:86400}, 'RESOLVE', 'required'],
    ['empty-queue-no-age', {pending_observation_count:0,oldest_pending_age_seconds:undefined}, 'COMPLETE', 'not_required'],
    ['empty-queue-contradiction', {pending_observation_count:0,oldest_pending_age_seconds:86400}, 'BLOCKED', 'undetermined'],
    ['ongoing-without-queue', {pending_observation_count:undefined,oldest_pending_age_seconds:undefined,activity_kind:'in_progress'}, 'COMPLETE', 'not_required'],
    ['scout-before-guard', {oldest_pending_age_seconds:86400}, 'SCOUT', 'required', {scouting_due:true}],
    ['persist-before-guard', {oldest_pending_age_seconds:86400}, 'PERSIST', 'required', {unfinished_safe_write:true}],
    ['wip-before-guard', {oldest_pending_age_seconds:86400}, 'BLOCKED', 'required', {active_wip_count:7}],
    ['frontier-before-guard', {oldest_pending_age_seconds:86400}, 'BLOCKED', 'required', {fulltext_ready:false}],
    ['unknown-scout', null, 'SCOUT', 'undetermined', {scouting_due:true}],
    ['unknown-persist', null, 'PERSIST', 'undetermined', {unfinished_safe_write:true}],
    ['independent-scout', {oldest_pending_age_seconds:86400}, 'SCOUT', 'required', {scouting_due:true,active_wip_count:7,scout_independent_of_frontier_and_wip:true}],
    ['independent-persist', {oldest_pending_age_seconds:86400}, 'PERSIST', 'required', {unfinished_safe_write:true,active_wip_count:7,persist_independent_of_frontier_and_wip:true}],
    ['repeat-still-blocks-complete', {oldest_pending_age_seconds:86400}, 'NOOP', 'required', {repeat_without_changed_prerequisite:true,identity_debt_due:false}],
    ['age-independent-of-debt-boolean', {oldest_pending_age_seconds:86400}, 'RESOLVE', 'required', {identity_debt_due:false}],
  ];
  for (const lane of ['A','B']) {
    const original = cases.find(c=>c.id===`${lane}-starvation-over-complete`);
    for (const [name, patch, route, state, inputPatch={}] of rows) {
      const id=`${lane}-starvation-${name}`;
      const input={...original.input,...inputPatch,activation_id:`synthetic-${id}`};
      if (patch!==null) input.identity_preflight_evidence={...evidence,...patch};
      cases.push({id,origin:'synthetic',classification:'contract_assertion',kind:'pipeline',input,
        expected:{route,identity_starvation_status:state,side_effect_authorized:false,pilot_mode:'observe_only'},
        frontierInput:name==='frontier-before-guard'?{
          frontier_gate:'F0_METADATA_SOURCE',next_gate:'F1_FULLTEXT_READY',frontier_consistent:false,
          assessment_completed:false,validation_accepted:false,assessment_distance_to_f5:5,
          inconsistency_code:'proposal_without_fulltext',
        }:{...original.frontierInput},
        contract:'hourly-hybrid-v4.md:37; owner clarification: new research only, evidence-based tri-state',
        note:'Synthetic explicit evidence; activity classification is supplied independently of frontier F2/F3. One second and one observation below thresholds.'});
    }
  }
  const template=cases.find(c=>c.id==='A-starvation-over-complete');
  for (const [id, patch] of [
    ['negative-age',{identity_preflight_evidence:{...evidence,oldest_pending_age_seconds:-1}}],
    ['negative-count',{identity_preflight_evidence:{...evidence,pending_observation_count:-1}}],
    ['fractional-count',{identity_preflight_evidence:{...evidence,pending_observation_count:19.5}}],
    ['string-age',{identity_preflight_evidence:{...evidence,oldest_pending_age_seconds:'86400'}}],
    ['invalid-activity',{identity_preflight_evidence:{...evidence,activity_kind:'F3'}}],
    ['caller-forged-status',{identity_starvation_status:'not_required'}],
  ]) cases.push({id:`starvation-schema-${id}`,origin:'synthetic',kind:'schema-rejection',
    input:{...template.input,...patch},expected:{valid:false},contract:'ActivationInput schema: typed raw evidence only; no caller-supplied guard result'});
}
