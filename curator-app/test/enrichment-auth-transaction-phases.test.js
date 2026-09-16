import test from 'node:test';
import assert from 'node:assert/strict';
import {EnrichmentStoreCore} from '../src/enrichment-store.js';

function coreWith(transaction) {
  const core=Object.create(EnrichmentStoreCore.prototype);
  core.ctx={storage:{
    transaction,
    async list(){return new Map()},
    async delete(){},
  }};
  return core;
}

async function codeFor(core) {
  try { await core.recordNonce(crypto.randomUUID(),Date.now()); }
  catch(error) { return error?.code; }
  return null;
}

test('transaction wrapper failure before callback remains transaction phase',async()=>{
  const core=coreWith(async()=>{throw Error('private transaction detail')});
  assert.equal(await codeFor(core),'service_auth_nonce_transaction_unavailable');
});

test('nonce read failure is isolated to get phase',async()=>{
  const core=coreWith(async fn=>fn({async get(){throw Error('private get detail')},async put(){}}));
  assert.equal(await codeFor(core),'service_auth_nonce_get_unavailable');
});

test('nonce write failure is isolated to put phase',async()=>{
  const core=coreWith(async fn=>fn({async get(){return undefined},async put(){throw Error('private put detail')}}));
  assert.equal(await codeFor(core),'service_auth_nonce_put_unavailable');
});

test('transaction rejection after callback is isolated to commit phase',async()=>{
  const core=coreWith(async fn=>{await fn({async get(){return undefined},async put(){}});throw Error('private commit detail')});
  assert.equal(await codeFor(core),'service_auth_nonce_commit_unavailable');
});
