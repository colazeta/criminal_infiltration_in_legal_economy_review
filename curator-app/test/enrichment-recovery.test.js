import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import migration from '../src/enrichment-schedule-migration.json' with {type:'json'};
import {Hour40Schedule, SCHEDULE_ID} from '../src/enrichment-schedule.js';

test('persisted failed paper receipt is reconciled after acknowledgement loss without another operation', async t => {
  const db = new DatabaseSync(':memory:');
  t.after(() => db.close());
  db.exec('PRAGMA foreign_keys=ON');
  db.exec(migration.sql);
  const scheduled = Date.parse('2026-09-11T16:40:00Z');
  let now = scheduled - 1, alarm = null, calls = 0;
  const storage = {
    sql: {exec(sql, ...values) {return {toArray: () => db.prepare(sql).all(...values)};}},
    transactionSync(fn) {
      db.exec('BEGIN');
      try {const result = fn(); db.exec('COMMIT'); return result;}
      catch (error) {db.exec('ROLLBACK'); throw error;}
    },
    async getAlarm() {return alarm;},
    async setAlarm(at) {alarm = at;}
  };
  const queue = new Hour40Schedule(storage, async () => {calls++; return {status: 'completed'};},
    async () => ({status: 'failed', selected_job_id: 'synthetic-paper', run_id: 'persisted-failure', error_code: 'identity_conflict'}),
    async () => true, () => now);
  await queue.start();
  now = scheduled;
  queue.enqueue();
  db.prepare("UPDATE enrichment_iterations SET status='running',attempts=1,lease_token='old',lease_until=?").run(now + 1);
  db.prepare("INSERT INTO enrichment_iteration_attempts VALUES (?,?,1,'old',?,NULL,'running',NULL,NULL)").run(SCHEDULE_ID, now, now);
  now += 2;
  await queue.tick();
  assert.equal(calls, 0);
  const ticket = queue.status().iterations[0];
  assert.equal(ticket.status, 'failed');
  assert.equal(ticket.run_id, 'persisted-failure');
  assert.equal(ticket.attempts, 1);
  assert.equal(db.prepare('SELECT outcome FROM enrichment_iteration_attempts').get().outcome, 'failed');
});
