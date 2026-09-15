import test from 'node:test';
import assert from 'node:assert/strict';
import {sha256} from '../src/review-v2.js';
import {
  DEVELOPMENT_CHECKPOINT_PROTOCOL,ASSESSMENT_REFERENCE_PROTOCOL,ASSESSMENT_COMPARISON_PROTOCOL,
  developmentCheckpointKey,readDevelopmentCheckpoint,writeDevelopmentCheckpoint,validateDevelopmentCheckpoint,
} from '../src/calibration-development-checkpoint.js';

function store(){
  const data=new Map();
  return {
    async put(key,text){const prior=data.get(key);if(prior!==undefined&&prior!==text)throw Error('immutable_content_conflict');data.set(key,text)},
    async get(key){return data.has(key)?{async text(){return data.get(key)}}:null},
    data,
  };
}
const candidate='CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-002';
const hex=x=>x.repeat(64);
const missing=()=>({status:'not_reported',value:null,evidence_span_ids:[],origin:'source'});
const reported=(value,origin='source')=>({status:'reported',value,evidence_span_ids:['span-1'],origin});
const assessment={
  schema_version:1,protocol_version:'CILE-ENRICH-1',codebook_version:'1.0.0',target_id:'target-1',input_sha256:hex('a'),
  generated_by:{agent:'independent-reference:test',model:'reference-model',prompt_sha256:hex('1')},
  source_ids:['source-1'],source_coverage:'full_text',
  spans:[{id:'span-1',source_id:'source-1',start_offset:0,end_offset:1,locator:'evidence 1'}],
  summary:reported('Independent grounded summary'),contribution:missing(),research_question:missing(),infiltration_definition:missing(),
  infiltration_operationalisation:missing(),authors_limitations:missing(),analyst_limitations:missing(),
  studies:[],datasets:[],analyses:[],variable_uses:[],findings:[],
  framework:{status:'proposed',primary:'diagnosis',rationale:reported('Grounded independent classification','analyst'),secondary:[],alternative:null},
};
const referenceIdentity={protocol:ASSESSMENT_REFERENCE_PROTOCOL,candidate_id:candidate,input_sha256:hex('a'),source_snapshot_sha256:hex('b'),request_sha256:hex('c'),stage:'reference'};
const reference={...referenceIdentity,output:{assessment}};
const comparisonIdentity={protocol:ASSESSMENT_COMPARISON_PROTOCOL,candidate_id:candidate,input_sha256:hex('a'),source_snapshot_sha256:hex('b'),proposal_revision:hex('d'),reference_sha256:hex('e'),request_sha256:hex('f'),stage:'comparison'};
const comparison={...comparisonIdentity,output:{comparison:{protocol:ASSESSMENT_COMPARISON_PROTOCOL,candidate_id:candidate,input_sha256:hex('a'),source_snapshot_sha256:hex('b'),proposal_revision:hex('d'),reference_sha256:hex('e'),assessor:{agent:'independent-reference:test',model:'test-model',prompt_sha256:hex('1')},source_fidelity:'pass',omissions:'none',classification_agreement:'agree',field_accuracy:'pass',mandatory_disagreement_paths:[],optional_disagreement_paths:[],compared_at:'2026-09-15T17:45:00Z'}}};

test('legacy chunk checkpoint key and round-trip remain supported',async()=>{
  const s=store(),identity={protocol:DEVELOPMENT_CHECKPOINT_PROTOCOL,candidate_id:candidate,extractor_fingerprint:hex('1'),request_sha256:hex('2'),chunk_id:'chunk-1'};
  const expected='calibration-development:'+await sha256(JSON.stringify([identity.protocol,identity.candidate_id,identity.extractor_fingerprint,identity.request_sha256,identity.chunk_id]));
  assert.equal(await developmentCheckpointKey(identity),expected);
  await writeDevelopmentCheckpoint(s,{...identity,output:{atoms:[]}});
  assert.equal((await readDevelopmentCheckpoint(s,identity)).status,'found');
});

test('reference checkpoint is immutable, private-store keyed and read back exactly',async()=>{
  const s=store(),receipt=await writeDevelopmentCheckpoint(s,reference);
  assert.equal(receipt.protocol,ASSESSMENT_REFERENCE_PROTOCOL);assert.equal(receipt.stage,'reference');
  assert.match(await developmentCheckpointKey(referenceIdentity),/^assessment-frontier:/);
  const read=await readDevelopmentCheckpoint(s,referenceIdentity);
  assert.equal(read.status,'found');assert.deepEqual(read.checkpoint,reference);
  const changed=structuredClone(reference);changed.output.assessment.summary=reported('Changed summary');
  await assert.rejects(writeDevelopmentCheckpoint(s,changed),/development_checkpoint_conflict/);
});

test('reference checkpoint rejects non-independent or mandatory unresolved assessment',()=>{
  const wrongAgent=structuredClone(reference);wrongAgent.output.assessment.generated_by.agent='automated-production';
  assert.throws(()=>validateDevelopmentCheckpoint(wrongAgent,{stored:true}),/development_checkpoint_invalid/);
  const unresolved=structuredClone(reference);unresolved.output.assessment.research_question={status:'ambiguous',value:'unclear',evidence_span_ids:['span-1'],origin:'source'};
  assert.throws(()=>validateDevelopmentCheckpoint(unresolved,{stored:true}),/development_checkpoint_invalid/);
});

test('comparison checkpoint binds candidate, source, proposal revision and reference digest',async()=>{
  const s=store();await writeDevelopmentCheckpoint(s,comparison);
  const read=await readDevelopmentCheckpoint(s,comparisonIdentity);assert.equal(read.status,'found');assert.deepEqual(read.checkpoint,comparison);
  const wrong={...comparisonIdentity,proposal_revision:hex('0')};assert.equal((await readDevelopmentCheckpoint(s,wrong)).status,'missing');
  const mismatched=structuredClone(comparison);mismatched.output.comparison.reference_sha256=hex('0');
  assert.throws(()=>validateDevelopmentCheckpoint(mismatched,{stored:true}),/development_checkpoint_identity_mismatch/);
});

test('comparison checkpoint rejects reviewer prose shape drift and uncontrolled outcomes',()=>{
  const extra=structuredClone(comparison);extra.output.comparison.notes='do not expose reviewer notes';
  assert.throws(()=>validateDevelopmentCheckpoint(extra,{stored:true}),/development_checkpoint_invalid/);
  const uncertain=structuredClone(comparison);uncertain.output.comparison.source_fidelity='invented';
  assert.throws(()=>validateDevelopmentCheckpoint(uncertain,{stored:true}),/development_checkpoint_invalid/);
});

test('reference and comparison protocols fail closed on extra identity fields',()=>{
  assert.throws(()=>validateDevelopmentCheckpoint({...referenceIdentity,proposal_revision:hex('d')}),/development_checkpoint_invalid/);
  assert.throws(()=>validateDevelopmentCheckpoint({...comparisonIdentity,reviewer:'public'}),/development_checkpoint_invalid/);
});
