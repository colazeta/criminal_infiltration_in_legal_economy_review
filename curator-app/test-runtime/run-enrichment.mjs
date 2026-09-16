import assert from 'node:assert/strict';
import {createHmac, randomUUID} from 'node:crypto';
import {createRequire} from 'node:module';
import {mkdtemp, rm, readFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const packageRoot = process.env.NATIVE_RUNTIME_PACKAGE_ROOT;
if (!packageRoot) throw Error('NATIVE_RUNTIME_PACKAGE_ROOT is required');
const require = createRequire(join(resolve(packageRoot), 'node_modules/wrangler/package.json'));
const {Miniflare} = require('miniflare');
const {build} = require('esbuild');
const config = JSON.parse(await readFile(new URL('../wrangler.example.jsonc', import.meta.url), 'utf8'));
const bundle = await build({
  entryPoints: [fileURLToPath(new URL('./enrichment-worker.js', import.meta.url))],
  bundle: true, write: false, format: 'esm', platform: 'neutral',
  external: ['cloudflare:workers'], target: 'es2022',
});
const secret = 'synthetic-native-test-only-' + randomUUID();
const commit = 'a'.repeat(40);
const domain = 'CILE-ENRICH-SERVICE-v1';
const persist = await mkdtemp(join(tmpdir(), 'cile-native-runtime-'));
let outbound = 0;
const options = {
  durableObjectsPersist: persist,
  workers: [{
    name: 'cile-native-runtime', modules: true, script: bundle.outputFiles[0].text,
    compatibilityDate: config.compatibility_date,
    durableObjects: {NATIVE_STORE: {className: 'NativeEnrichmentTest', useSQLite: true}},
    bindings: {SESSION_SECRET: secret, DEPLOY_COMMIT: commit, CURATOR_LOGIN: 'colazeta', PAPER_ENRICHMENT_ENABLED: 'false'},
    outboundService: () => {outbound++; return new Response('External calls disabled in native tests', {status: 503});},
  }],
};
function signed(operation = 'verify', {key = secret, timestamp = Date.now(), expectedCommit = commit} = {}) {
  const body = JSON.stringify({operation, expected_commit: expectedCommit});
  const nonce = randomUUID(), ts = String(timestamp);
  const derived = createHmac('sha256', key).update(domain).digest();
  const signature = createHmac('sha256', derived).update(`${domain}\n${ts}\n${nonce}\n${body}`).digest('hex');
  return {method: 'POST', body, headers: {
    'Content-Type': 'application/json', 'X-Enrichment-Timestamp': ts,
    'X-Enrichment-Nonce': nonce, 'X-Enrichment-Signature': signature,
  }};
}
let mf;
try {
  mf = new Miniflare(options);
  const primitive = await mf.dispatchFetch('https://native.test/primitive');
  console.log('Native storage primitives:', JSON.stringify(await primitive.json()));
  const request = signed();
  let response = await mf.dispatchFetch('https://native.test/machine', request);
  const verified = await response.json();
  assert.equal(response.status, 200, JSON.stringify(verified));
  assert.equal(verified.verified, true);
  assert.equal((await mf.dispatchFetch('https://native.test/machine', request)).status, 401, 'replay rejected');
  for (const input of [signed('verify', {key: 'wrong-key-'.repeat(8)}), signed('verify', {timestamp: Date.now() - 180000})]) {
    assert.equal((await mf.dispatchFetch('https://native.test/machine', input)).status, 401);
  }
  assert.equal((await mf.dispatchFetch('https://native.test/machine', {method: 'POST', body: '{}', headers: {'Content-Type': 'application/json'}})).status, 401);
  assert.equal((await mf.dispatchFetch('https://native.test/machine', signed('verify', {expectedCommit: 'b'.repeat(40)}))).status, 409);
  const concurrent = signed();
  const replies = await Promise.all([mf.dispatchFetch('https://native.test/machine', concurrent), mf.dispatchFetch('https://native.test/machine', concurrent)]);
  assert.deepEqual(replies.map(r => r.status).sort(), [200, 401], 'only one concurrent nonce is accepted');
  response = await mf.dispatchFetch('https://native.test/storage-roundtrip');
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {text: true, binary: true, conflict: true});
  response = await mf.dispatchFetch('https://native.test/migration-reload');
  assert.deepEqual(await response.json(), {verified: true});
  const persistedRequest = signed();
  assert.equal((await mf.dispatchFetch('https://native.test/machine', persistedRequest)).status, 200);
  await mf.dispose(); mf = new Miniflare(options);
  assert.equal((await mf.dispatchFetch('https://native.test/machine', persistedRequest)).status, 401, 'nonce survives a fresh runtime');
  assert.equal((await mf.dispatchFetch('https://native.test/machine', signed())).status, 200);
  response = await mf.dispatchFetch('https://native.test/storage-roundtrip');
  assert.deepEqual(await response.json(), {text: true, binary: true, conflict: true});
  assert.equal(outbound, 0, 'no provider or production requests');
  console.log('Native enrichment runtime passed: migrations, signed verification, replay, concurrency, retained text/binary, restart.');
} finally {
  await mf?.dispose();
  await rm(persist, {recursive: true, force: true});
}
