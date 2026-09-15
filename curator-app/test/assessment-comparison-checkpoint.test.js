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
const referenceIdentity={protocol:ASSESSMENT_REFERENCE_PROTOCOL,candidate_id:candidate,input_sha256:hex('a'),source_snapshot_sha256:hex('b'),request_sha256:hex('c'),stage:'reference'};
const reference={...referenceIdentity,output:{assessment:{schema_version:1,marker:'private-reference'}}};
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
  await assert.rejects(writeDevelopmentCheckpoint(s,{...reference,output:{assessment:{schema_version:1,marker:'changed'}}}),/development_checkpoint_conflict/);
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
