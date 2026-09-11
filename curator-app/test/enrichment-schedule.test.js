import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import migration from '../src/enrichment-schedule-migration.json' with {type:'json'};
import {sha256} from '../src/review-v2.js';
import {Hour40Schedule, HOUR, SCHEDULE_ID, dueSlot, firstSlot} from '../src/enrichment-schedule.js';

const T = Date.parse('2026-09-11T16:40:00Z');
function fixture(processor = async () => ({status:'completed',run_id:'synthetic-run'})) {
  const db = new DatabaseSync(':memory:'); db.exec('PRAGMA foreign_keys=ON'); db.exec(migration.sql);
  let now = T - 60000, alarm = null, enabled = true;
  const storage = {sql:{exec(sql,...v){return{toArray:()=>db.prepare(sql).all(...v)}}},
    transactionSync(fn){db.exec('BEGIN');try{const r=fn();db.exec('COMMIT');return r;}catch(e){db.exec('ROLLBACK');throw e;}},
    async getAlarm(){return alarm;},async setAlarm(t){alarm=t;}
  };
  const make = (p = processor, resolve = async()=>null) => new Hour40Schedule(storage,p,resolve,async()=>enabled,()=>now);
  return {db,storage,make,queue:make(),setTime(t){now=t;},setEnabled(v){enabled=v;},getAlarm:()=>alarm};
}

test('schedule migration is additive and byte-bound',async()=>{
  const sql=readFileSync(new URL('../migrations/0004_enrichment_schedule.sql',import.meta.url),'utf8');
  assert.equal(sql,migration.sql);assert.equal(await sha256(sql),migration.sha256);
});
test('minute 40, not minute zero; no future or retroactive first ticket',async()=>{
  assert.equal(dueSlot(T-1),T-HOUR);assert.equal(firstSlot(T-1),T);assert.equal(firstSlot(T),T);assert.equal(firstSlot(T+1),T+HOUR);
  const f=fixture();await f.queue.start();assert.equal(f.getAlarm(),T);await f.queue.tick();assert.equal(f.queue.status().iterations.length,0);
});
test('missed deliveries are recovered from the watermark without gaps or duplicates',async()=>{
  const f=fixture();await f.queue.start();f.setTime(T+3*HOUR+2000);assert.equal(f.queue.enqueue(),4);assert.equal(f.queue.enqueue(),0);
  assert.equal(f.queue.status().iterations.length,4);assert.equal(f.queue.status().schedule.next_slot,T+4*HOUR);
  for(let i=0;i<4;i++)await f.queue.tick();
  assert.equal(f.queue.status().totals.find(r=>r.status==='completed').count,4);
  await f.queue.tick();assert.equal(f.db.prepare('SELECT COUNT(*) n FROM enrichment_iteration_attempts').get().n,4);
});
test('catch-up uses bounded pages without dropping the older backlog',async()=>{
  const f=fixture();await f.queue.start();f.setTime(T+400*HOUR);
  assert.equal(f.queue.enqueue(),168);assert.equal(f.queue.enqueue(),168);assert.equal(f.queue.enqueue(),65);assert.equal(f.queue.enqueue(),0);
  assert.equal(f.db.prepare('SELECT COUNT(*) n FROM enrichment_iterations').get().n,401);
});
test('overlapping hour-40 arrivals remain pending and drain immediately after release',async()=>{
  let release,calls=0;
  const f=fixture(async()=>{calls++;if(calls===1)await new Promise(r=>release=r);return{status:'completed',run_id:'synthetic-'+calls};});
  await f.queue.start();f.setTime(T);const first=f.queue.tick();while(!release)await new Promise(r=>setTimeout(r,0));
  f.setTime(T+2*HOUR);assert.equal((await f.queue.tick()).status,'queued');assert.equal(calls,1);
  assert.equal(f.queue.status().totals.find(r=>r.status==='pending').count,2);
  release();await first;assert.ok(f.getAlarm()<=T+2*HOUR+1000);
  await f.queue.tick();await f.queue.tick();assert.equal(calls,3);
  assert.equal(f.queue.status().totals.find(r=>r.status==='completed').count,3);
});
test('simultaneous callbacks cannot race through the asynchronous enabled check',async()=>{
  const f=fixture();await f.queue.start();f.setTime(T);await Promise.all([f.queue.tick(),f.queue.tick(),f.queue.tick()]);
  assert.equal(f.db.prepare('SELECT COUNT(*) n FROM enrichment_iteration_attempts').get().n,1);
});
test('processor lease contention defers, rather than dropping, the ticket',async()=>{
  let calls=0;const f=fixture(async()=>++calls===1?{status:'leased'}:{status:'completed',run_id:'synthetic'});
  await f.queue.start();f.setTime(T);await f.queue.tick();assert.equal(f.queue.status().iterations[0].status,'pending');
  f.setTime(T+60001);await f.queue.tick();assert.equal(f.queue.status().iterations[0].status,'completed');
  assert.deepEqual(f.db.prepare('SELECT outcome FROM enrichment_iteration_attempts ORDER BY attempt').all().map(r=>r.outcome),['deferred','completed']);
});
test('a crashed attempt is recovered, and old lease tokens cannot acknowledge it',async()=>{
  const f=fixture();await f.queue.start();f.setTime(T);f.queue.enqueue();
  f.db.prepare("UPDATE enrichment_iterations SET status='running',attempts=1,lease_token='old',lease_until=?,started_at=?").run(T+1,T);
  f.db.prepare("INSERT INTO enrichment_iteration_attempts VALUES (?,?,1,'old',?,NULL,'running',NULL,NULL)").run(SCHEDULE_ID,T,T);
  f.setTime(T+2);await f.make().tick();
  assert.equal(f.queue.status().iterations[0].status,'completed');assert.equal(f.queue.status().iterations[0].attempts,2);
  assert.deepEqual(f.db.prepare('SELECT outcome FROM enrichment_iteration_attempts ORDER BY attempt').all().map(r=>r.outcome),['interrupted','completed']);
  assert.throws(()=>f.queue.finish({scheduled_at:T,attempts:1,lease_token:'old'},{status:'completed'},'completed'),/fence_lost/);
});
test('crash after processor persistence is reconciled without a second paper operation',async()=>{
  const f=fixture();await f.queue.start();f.setTime(T);f.queue.enqueue();
  f.db.prepare("UPDATE enrichment_iterations SET status='running',attempts=1,lease_token='old',lease_until=?").run(T+1);
  f.db.prepare("INSERT INTO enrichment_iteration_attempts VALUES (?,?,1,'old',?,NULL,'running',NULL,NULL)").run(SCHEDULE_ID,T,T);
  f.setTime(T+2);let calls=0;const q=f.make(async()=>{calls++;},async()=>({status:'completed',run_id:'persisted-before-crash'}));await q.tick();
  assert.equal(calls,0);assert.equal(q.status().iterations[0].run_id,'persisted-before-crash');assert.equal(q.status().iterations[0].attempts,1);
});
test('transient exceptions preserve tickets and terminal attempt history',async()=>{
  const f=fixture(async()=>{throw Error('synthetic-network-failure')});await f.queue.start();f.setTime(T);
  await assert.rejects(f.queue.tick());assert.equal(f.queue.status().iterations[0].status,'pending');assert.ok(f.getAlarm()>T);
  assert.throws(()=>f.db.prepare("UPDATE enrichment_iteration_attempts SET outcome='completed'").run(),/immutable/);
  assert.throws(()=>f.db.prepare('DELETE FROM enrichment_iterations').run(),/append_only/);
});
test('failed paper operation is visible as failed, not a completed scientific extraction',async()=>{
  const f=fixture(async()=>({status:'failed',selected_job_id:'synthetic-job',run_id:'synthetic',error_code:'identity_conflict'}));await f.queue.start();f.setTime(T);await f.queue.tick();
  assert.equal(f.queue.status().iterations[0].status,'failed');assert.equal(f.queue.status().iterations[0].error_code,'identity_conflict');
});
test('reactivation never resets the start epoch or pending backlog',async()=>{
  const f=fixture();await f.queue.start();f.setTime(T+HOUR);f.setEnabled(false);await f.queue.tick();
  assert.equal(f.queue.status().iterations.length,2);await f.make().start();assert.equal(f.queue.status().schedule.first_slot,T);
  f.setEnabled(true);await f.make().tick();await f.make().tick();assert.equal(f.queue.status().totals.find(r=>r.status==='completed').count,2);
});
