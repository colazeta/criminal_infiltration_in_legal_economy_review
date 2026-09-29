import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {nativeAdapter} from './sqlite-adapter-fixture.js';
import {runEnrichment, syncTargets, handlePaperEnrichment} from '../src/paper-enrichment.js';

const HOUR = 3600000, now = Date.parse('2026-09-29T10:00:00Z');
const first = {id:'CAND-SYNTHETIC-001',title:'Synthetic first paper',doi:'10.1234/first',sourceLinks:[]};
const second = {id:'CAND-SYNTHETIC-002',title:'Synthetic second paper',doi:'10.1234/second',sourceLinks:[]};
const limited = headers => new Response('', {status:429, headers});
const work = () => Response.json({id:'https://openalex.org/W1',doi:first.doi,title:first.title,referenced_works:[],cited_by_count:0});

async function setup(records=[first]) {
  const sqlite = new DatabaseSync(':memory:');
  sqlite.exec('PRAGMA foreign_keys=ON');
  for (const migration of ['0003_paper_enrichment.sql','0007_extraction_relations.sql'])
    sqlite.exec(readFileSync(new URL('../migrations/'+migration, import.meta.url),'utf8'));
  const objects = new Map(), registry = {schemaVersion:1,records};
  const env = {CURATOR_LOGIN:'owner',PAPER_ENRICHMENT_ENABLED:'true',REVIEW_DB:nativeAdapter(sqlite),
    REVIEW_EVIDENCE:{async put(key,value){objects.set(key,value)},async get(key){return objects.has(key)?{async text(){return objects.get(key)}}:null}}};
  await syncTargets(env,registry,now);
  return {env,sqlite,registry,objects,run:(hour,fetcher)=>runEnrichment(env,{now:now+hour*HOUR,registry,fetcher})};
}

test('repeated quota responses preserve retryability and append attempts without exhausting a paper', async () => {
  const {sqlite,run} = await setup();
  sqlite.exec("UPDATE enrichment_jobs SET status='blocked' WHERE kind='citations'");
  for (const hour of [0,1,2,3]) {
    const receipt = await run(hour,async()=>limited({}));
    assert.equal(receipt.error_code,'crossref_rate_limited');
  }
  const job = sqlite.prepare("SELECT * FROM enrichment_jobs WHERE kind='metadata'").get();
  assert.equal(job.status,'pending');
  assert.equal(job.failure_streak,0);
  assert.equal(job.attempts_total,4);
  assert.equal(Date.parse(job.due_at),now+4*HOUR);
  assert.equal(sqlite.prepare('SELECT COUNT(*) n FROM enrichment_attempts').get().n,4);
  assert.equal(sqlite.prepare('SELECT COUNT(*) n FROM enrichment_sources').get().n,0);
});

test('OpenAlex daily reset is respected with Retry-After, while invalid reset headers get a bounded fallback', async () => {
  for (const [headers,hours] of [
    [{'Retry-After':'3600','X-RateLimit-Remaining':'0','X-RateLimit-Reset':'18000'},5],
    [{'Retry-After':new Date(now+6*HOUR).toUTCString(),'X-RateLimit-Remaining':'0','X-RateLimit-Reset':'18000'},6],
    [{'X-RateLimit-Remaining':'1','X-RateLimit-Reset':'18000'},1],
    [{'Retry-After':'bad','X-RateLimit-Remaining':'0','X-RateLimit-Reset':'9'.repeat(100)},1],
  ]) {
    const {sqlite,run} = await setup();
    sqlite.exec("UPDATE enrichment_jobs SET status='blocked' WHERE kind='metadata'");
    assert.equal((await run(0,async()=>limited(headers))).error_code,'openalex_rate_limited');
    assert.equal(Date.parse(sqlite.prepare("SELECT due_at FROM enrichment_jobs WHERE kind='citations'").get().due_at),now+hours*HOUR);
  }
});

test('provider cooldown spares other candidates, permits another provider, and resumes after expiry', async () => {
  const {env,sqlite,registry,run} = await setup([first,second]);
  const firstTarget = sqlite.prepare('SELECT target_id FROM enrichment_targets WHERE record_id=?').get(first.id).target_id;
  // Make the selected first paper deterministic; leave metadata and both papers eligible afterwards.
  sqlite.prepare("UPDATE enrichment_jobs SET due_at=? WHERE target_id<>? OR kind='metadata'").run(new Date(now+HOUR).toISOString(),firstTarget);
  const failure = await run(0,async()=>limited({'X-RateLimit-Remaining':'0','X-RateLimit-Reset':'10800'}));
  assert.equal(failure.error_code,'openalex_rate_limited');
  const failedJob = sqlite.prepare('SELECT * FROM enrichment_jobs WHERE job_id=?').get(failure.selected_job_id);
  const attempt = sqlite.prepare('SELECT * FROM enrichment_attempts WHERE job_id=?').get(failedJob.job_id);
  assert.equal((await run(1,async url=>{
    assert.equal(new URL(url).hostname,'api.crossref.org');
    const record = decodeURIComponent(url).endsWith(first.doi)?first:second;
    return Response.json({message:{DOI:record.doi,title:[record.title]}});
  })).status,'completed');
  sqlite.exec("UPDATE enrichment_jobs SET status='blocked' WHERE kind='metadata'");
  const paused = await run(2,async()=>{throw Error('provider must remain paused')});
  assert.equal(paused.status,'empty');
  assert.equal(paused.selected_job_id,null);
  assert.equal(sqlite.prepare('SELECT attempts_total FROM enrichment_jobs WHERE job_id=?').get(failedJob.job_id).attempts_total,1);
  // Isolate the original job to verify its exact resumption and immutable failed receipt.
  sqlite.prepare("UPDATE enrichment_jobs SET due_at=? WHERE kind='citations' AND job_id<>?").run(new Date(now+10*HOUR).toISOString(),failedJob.job_id);
  const resumed = await run(3,async()=>work());
  assert.equal(resumed.selected_job_id,failedJob.job_id);
  assert.equal(resumed.status,'partial');
  assert.deepEqual(sqlite.prepare('SELECT * FROM enrichment_attempts WHERE attempt_id=?').get(attempt.attempt_id),attempt);
  assert.equal(sqlite.prepare('SELECT COUNT(*) n FROM enrichment_citation_coverage').get().n,1);
  const status = await (await handlePaperEnrichment(new Request('https://example.org/api/paper-enrichment/status'),env,{login:'owner'})).json();
  assert.equal(status.runs[0].record_id,first.id);
  assert.equal(status.runs[0].kind,'citations');
  assert.equal(registry.records.length,2);
});

test('Crossref cooldown survives target supersession and does not impose OpenAlex reset semantics', async () => {
  const {env,sqlite,run} = await setup();
  sqlite.exec("UPDATE enrichment_jobs SET status='blocked' WHERE kind='citations'");
  assert.equal((await run(0,async()=>limited({'Retry-After':'10800','X-RateLimit-Remaining':'0','X-RateLimit-Reset':'99999'}))).error_code,'crossref_rate_limited');
  const changed = {schemaVersion:1,records:[{...first,title:'Updated title'}]};
  await syncTargets(env,changed,now+HOUR);
  sqlite.exec("UPDATE enrichment_jobs SET status='blocked' WHERE kind='citations'");
  const result = await runEnrichment(env,{now:now+HOUR,registry:changed,fetcher:async()=>{throw Error('supersession cannot bypass cooldown')}});
  assert.equal(result.status,'empty');
  assert.equal(sqlite.prepare("SELECT due_at FROM enrichment_jobs WHERE error_code='crossref_rate_limited'").get().due_at,new Date(now+3*HOUR).toISOString());
});

test('an incoming-page retry preserves its cursor and previously persisted citation snapshot', async () => {
  const {sqlite,run} = await setup();
  sqlite.exec("UPDATE enrichment_jobs SET status='blocked' WHERE kind='metadata'");
  await run(0,async()=>Response.json({id:'https://openalex.org/W1',doi:first.doi,title:first.title,referenced_works:['https://openalex.org/W2'],cited_by_count:1}));
  const before = sqlite.prepare("SELECT checkpoint_json FROM enrichment_jobs WHERE kind='citations'").get().checkpoint_json;
  const edge = sqlite.prepare('SELECT * FROM enrichment_citation_observations').get();
  const limitedRun = await run(1,async()=>limited({'Retry-After':'7200'}));
  assert.equal(limitedRun.error_code,'openalex_rate_limited');
  assert.equal(sqlite.prepare("SELECT checkpoint_json FROM enrichment_jobs WHERE kind='citations'").get().checkpoint_json,before);
  assert.equal((await run(2,async()=>{throw Error('retry too early')})).status,'empty');
  assert.equal((await run(3,async url=>{
    assert.equal(new URL(url).searchParams.get('cursor'),JSON.parse(before).cursor);
    return Response.json({results:[{id:'https://openalex.org/W3'}],meta:{count:1,next_cursor:null}});
  })).status,'completed');
  assert.deepEqual(sqlite.prepare('SELECT * FROM enrichment_citation_observations WHERE observation_id=?').get(edge.observation_id),edge);
  assert.equal(sqlite.prepare('SELECT COUNT(*) n FROM enrichment_citation_observations').get().n,2);
});

test('rate limiting does not erase existing failure debt or rewrite historical exhausted jobs', async () => {
  const {sqlite,run} = await setup([first,second]);
  sqlite.exec("UPDATE enrichment_jobs SET status='blocked' WHERE kind='citations'");
  const old = sqlite.prepare("SELECT * FROM enrichment_jobs WHERE kind='metadata' ORDER BY job_id LIMIT 1").get();
  sqlite.prepare("UPDATE enrichment_jobs SET status='exhausted',failure_streak=3,due_at=NULL,error_code='rate_limited' WHERE job_id=?").run(old.job_id);
  const historical = sqlite.prepare('SELECT * FROM enrichment_jobs WHERE job_id=?').get(old.job_id);
  sqlite.exec("UPDATE enrichment_jobs SET failure_streak=2 WHERE kind='metadata' AND status='pending'");
  await run(0,async()=>limited({}));
  assert.deepEqual(sqlite.prepare('SELECT * FROM enrichment_jobs WHERE job_id=?').get(old.job_id),historical);
  const pending = sqlite.prepare("SELECT * FROM enrichment_jobs WHERE kind='metadata' AND status='pending'").get();
  assert.equal(pending.failure_streak,2);
  assert.equal(pending.attempts_total,1);
});

test('optional OpenAlex key is host-scoped and absent from retained provenance and errors', async () => {
  const {env,sqlite,objects,run} = await setup();
  env.OPENALEX_API_KEY = 'synthetic-private-key';
  await run(0,async(url,options)=>{
    assert.equal(options.headers.Authorization,undefined);
    return Response.json({message:{DOI:first.doi,title:[first.title]}});
  });
  // Crossref references are processed locally first; exercise the remote citation stage explicitly.
  sqlite.exec(`UPDATE enrichment_jobs SET checkpoint_json='{"crossref_done":true}' WHERE kind='citations'`);
  const response = await run(1,async(url,options)=>{
    assert.equal(new URL(url).hostname,'api.openalex.org');
    assert.equal(options.headers.Authorization,'Bearer synthetic-private-key');
    assert.equal(options.redirect,'manual');
    assert.ok(!url.includes(env.OPENALEX_API_KEY));
    return work();
  });
  assert.equal(response.status,'partial');
  const persisted = JSON.stringify(['enrichment_jobs','enrichment_runs','enrichment_attempts','enrichment_sources','enrichment_citation_coverage'].map(table=>sqlite.prepare('SELECT * FROM '+table).all()));
  assert.ok(!persisted.includes(env.OPENALEX_API_KEY));
  assert.ok(!JSON.stringify([...objects]).includes(env.OPENALEX_API_KEY));
  const noRegistry = await runEnrichment(env,{now:now+2*HOUR,fetcher:async(url,options)=>{
    if(new URL(url).hostname==='colazeta.github.io') {
      assert.equal(options.headers.Authorization,undefined);
      return new Response('',{status:503});
    }
    assert.equal(options.headers.Authorization,'Bearer synthetic-private-key');
    return Response.json({results:[],meta:{count:0,next_cursor:null}});
  }});
  assert.equal(noRegistry.status,'partial');
});
