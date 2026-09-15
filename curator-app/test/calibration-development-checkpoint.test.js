import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEVELOPMENT_CHECKPOINT_PROTOCOL,developmentCheckpointKey,readDevelopmentCheckpoint,
  validateDevelopmentCheckpoint,writeDevelopmentCheckpoint,
} from '../src/calibration-development-checkpoint.js';

function identity(overrides={}){
  return {
    protocol:DEVELOPMENT_CHECKPOINT_PROTOCOL,
    candidate_id:'CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-002',
    extractor_fingerprint:'a'.repeat(64),request_sha256:'b'.repeat(64),chunk_id:'chunk-1',...overrides,
  };
}
function output(label='one'){
  return {atoms:[{entity_type:'global',entity_key:'paper',field:'summary',value:label,evidence:'literal evidence'}]};
}
function store(){
  const values=new Map();
  return {
    async get(key){const text=values.get(key);return text===undefined?null:{async text(){return text}}},
    async put(key,text){const prior=values.get(key);if(prior!==undefined&&prior!==text)throw Error('immutable_content_conflict');values.set(key,text)},
    values,
  };
}

test('missing, write and exact replay are durable without exposing output in write receipt',async()=>{
  const s=store(),id=identity();
  assert.equal((await readDevelopmentCheckpoint(s,id)).status,'missing');
  const first=await writeDevelopmentCheckpoint(s,{...id,output:output()});
  assert.equal(first.status,'stored');
  assert.equal(first.chunk_id,'chunk-1');
  assert.match(first.output_sha256,/^[0-9a-f]{64}$/);
  assert.equal(Object.hasOwn(first,'output'),false);
  const found=await readDevelopmentCheckpoint(s,id);
  assert.equal(found.status,'found');
  assert.deepEqual(found.checkpoint.output,output());
  const replay=await writeDevelopmentCheckpoint(s,{...id,output:output()});
  assert.equal(replay.output_sha256,first.output_sha256);
});

test('same immutable request cannot be replaced with different output',async()=>{
  const s=store(),id=identity();
  await writeDevelopmentCheckpoint(s,{...id,output:output('first')});
  await assert.rejects(()=>writeDevelopmentCheckpoint(s,{...id,output:output('different')}),error=>{
    assert.equal(error.code,'development_checkpoint_conflict');
    assert.equal(error.status,409);
    return true;
  });
});

test('request, source-bound request hash and extractor changes use distinct keys',async()=>{
  const base=identity();
  const keys=await Promise.all([
    developmentCheckpointKey(base),
    developmentCheckpointKey(identity({request_sha256:'c'.repeat(64)})),
    developmentCheckpointKey(identity({extractor_fingerprint:'d'.repeat(64)})),
    developmentCheckpointKey(identity({chunk_id:'chunk-2'})),
  ]);
  assert.equal(new Set(keys).size,4);
});

test('malformed or oversized checkpoint envelopes fail closed',async()=>{
  assert.throws(()=>validateDevelopmentCheckpoint({...identity(),extra:true}),/development_checkpoint_invalid/);
  assert.throws(()=>validateDevelopmentCheckpoint(identity({request_sha256:'no'})),/development_checkpoint_invalid/);
  const s=store(),huge='x'.repeat(510000);
  await assert.rejects(()=>writeDevelopmentCheckpoint(s,{...identity(),output:{atoms:[{entity_type:'global',entity_key:'paper',field:'summary',value:huge,evidence:'e'}]}}),/development_checkpoint_too_large/);
});
