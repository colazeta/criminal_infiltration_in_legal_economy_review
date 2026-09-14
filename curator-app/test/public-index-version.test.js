import test from 'node:test';
import assert from 'node:assert/strict';
import policy from '../../ontology/modules/completion-policy.json' with {type:'json'};
import {publicIndexSnapshot,readPublicIndex} from '../src/public-paper-research.js';

function env(commit) {
  return {DEPLOY_COMMIT:commit,REVIEW_DB:{prepare(){return{bind(){return this},async all(){return{results:[]}},async first(){return{n:0,last:null}}}}}};
}
test('an unchanged database cannot preserve an index revision across deployment changes',async()=>{
  const oldEnv=env('a'.repeat(40)),newEnv=env('b'.repeat(40));
  const old=await publicIndexSnapshot(oldEnv),next=await publicIndexSnapshot(newEnv);
  assert.notEqual(old.revision,next.revision);
  await assert.rejects(readPublicIndex(newEnv,0,old.revision),e=>e.status===409&&e.message==='index_changed');
  assert.equal((await publicIndexSnapshot(newEnv)).revision,next.revision);
});
test('the index revision also binds the complete projection and completion-policy contract',async()=>{
  const context=env('a'.repeat(40)),previous=policy.version;
  const old=await publicIndexSnapshot(context);
  try{
    policy.version='SYNTHETIC-POLICY-CHANGE';
    assert.notEqual((await publicIndexSnapshot(context)).revision,old.revision);
    await assert.rejects(readPublicIndex(context,0,old.revision),/index_changed/);
  }finally{policy.version=previous}
  assert.equal((await publicIndexSnapshot(context)).revision,old.revision);
});
