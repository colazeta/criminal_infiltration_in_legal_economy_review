import test from 'node:test';
import assert from 'node:assert/strict';
import {EnrichmentStoreCore, serviceSignature} from '../src/enrichment-store.js';

const secret='test-only-secret-never-used-in-production-0123456789';

async function signedRequest(body, now=Date.now(), key=secret) {
  const timestamp=String(now), nonce=crypto.randomUUID();
  return {
    request:new Request('https://enrichment.internal/machine', {
      method:'POST', body,
      headers:{
        'Content-Type':'application/json',
        'X-Enrichment-Timestamp':timestamp,
        'X-Enrichment-Nonce':nonce,
        'X-Enrichment-Signature':await serviceSignature(key,timestamp,nonce,body),
      },
    }),
    nonce,
  };
}

test('valid HMAC authentication is distinct from anti-replay persistence', async()=>{
  const core=Object.create(EnrichmentStoreCore.prototype);
  core.env={SESSION_SECRET:secret};
  const body=JSON.stringify({operation:'verify',expected_commit:'abc'});
  const {request,nonce}=await signedRequest(body);
  assert.equal(await core.authorise(request,body,Date.now()),nonce);
});

test('signed request with unavailable nonce storage gets a closed service-state error', async()=>{
  const core=Object.create(EnrichmentStoreCore.prototype);
  core.ctx={storage:{
    async transaction(){throw Error('private storage implementation detail')},
    async list(){return new Map()},
    async delete(){},
  }};
  await assert.rejects(core.recordNonce(crypto.randomUUID(),Date.now()), error=>
    error?.code==='service_auth_state_unavailable'&&error?.status===503&&error?.message==='service_auth_state_unavailable');
});

test('replay remains an authentication failure rather than a storage diagnostic', async()=>{
  const core=Object.create(EnrichmentStoreCore.prototype);
  core.ctx={storage:{
    async transaction(fn){return fn({async get(){return 1},async put(){}})},
    async list(){return new Map()},
    async delete(){},
  }};
  await assert.rejects(core.recordNonce(crypto.randomUUID(),Date.now()),/service_replay/);
});
