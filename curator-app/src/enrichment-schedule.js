/* Persistent hourly tickets, distinct from attempts and from scientific completeness. */
export const SCHEDULE_ID = 'cile-hour40-v1';
export const HOUR = 3600000;
const OFFSET = 40 * 60000, LEASE = 10 * 60000, RETRY = 60000;
const terminal = new Set(['completed', 'partial', 'empty']);
export const dueSlot = now => Math.floor((now - OFFSET) / HOUR) * HOUR + OFFSET;
export const firstSlot = now => dueSlot(now) + (now === dueSlot(now) ? 0 : HOUR);
export const iterationKey = (scheduledAt, attempt) => `hour40:${new Date(scheduledAt).toISOString()}:${attempt}`;

export class Hour40Schedule {
  constructor(storage, processor, resolve, enabled, clock = Date.now) {
    this.storage = storage; this.processor = processor; this.resolve = resolve;
    this.enabled = enabled; this.clock = clock; this.busy = false;
  }
  rows(sql, ...values) { return this.storage.sql.exec(sql, ...values).toArray(); }
  one(sql, ...values) { return this.rows(sql, ...values)[0] || null; }
  async start() {
    const now = this.clock(), first = firstSlot(now);
    this.storage.transactionSync(() => {
      this.rows('INSERT OR IGNORE INTO enrichment_schedules VALUES (?,?,?,?,?)', SCHEDULE_ID, 'CILE-HOUR40-1', first, first, now);
    });
    await this.arm();
    return this.status();
  }
  enqueue() {
    const now = this.clock();
    return this.storage.transactionSync(() => {
      const schedule = this.one('SELECT * FROM enrichment_schedules WHERE schedule_id=?', SCHEDULE_ID);
      if (!schedule) return 0;
      let slot = schedule.next_slot, count = 0;
      // Bounded transactions, not a truncated catch-up window. Cursor stops at last inserted slot.
      while (slot <= dueSlot(now) && count < 168) {
        this.rows("INSERT OR IGNORE INTO enrichment_iterations(schedule_id,scheduled_at,materialised_at,status,retry_at) VALUES (?,?,?,'pending',?)", SCHEDULE_ID, slot, now, now);
        slot += HOUR; count++;
      }
      this.rows('UPDATE enrichment_schedules SET next_slot=? WHERE schedule_id=?', slot, SCHEDULE_ID);
      return count;
    });
  }
  async arm() {
    const now = this.clock(), schedule = this.one('SELECT * FROM enrichment_schedules WHERE schedule_id=?', SCHEDULE_ID);
    if (!schedule) return;
    const pending = this.one("SELECT MIN(retry_at) AS at FROM enrichment_iterations WHERE schedule_id=? AND status='pending'", SCHEDULE_ID);
    const running = this.one("SELECT lease_until AS at FROM enrichment_iterations WHERE schedule_id=? AND status='running'", SCHEDULE_ID);
    const live = await this.enabled();
    const times = [schedule.next_slot];
    if (live && !this.busy && !running && pending?.at != null) times.push(pending.at);
    if (live && running?.at != null) times.push(Math.max(running.at, now + (this.busy ? RETRY : 1000)));
    // Do not move an already earlier wake-up into the future on a duplicate trigger.
    const at = Math.max(now + 1000, Math.min(...times));
    const prior = await this.storage.getAlarm();
    if (prior === null || prior <= now || at < prior) await this.storage.setAlarm(at);
  }
  status() {
    return {
      protocol: 'CILE-HOUR40-1', cron: '40 * * * *', timezone: 'UTC',
      schedule: this.one('SELECT * FROM enrichment_schedules WHERE schedule_id=?', SCHEDULE_ID),
      totals: this.rows('SELECT status,COUNT(*) AS count FROM enrichment_iterations WHERE schedule_id=? GROUP BY status', SCHEDULE_ID),
      iterations: this.rows('SELECT * FROM enrichment_iterations WHERE schedule_id=? ORDER BY scheduled_at DESC LIMIT 48', SCHEDULE_ID)
    };
  }
  async tick() {
    this.enqueue(); // Always record due tickets, including during another attempt.
    if (this.busy) { await this.arm(); return {status: 'queued'}; }
    this.busy = true;
    let job = null;
    try {
      if (!await this.enabled()) return {status: 'inactive'};
      const now = this.clock();
      const active = this.one("SELECT * FROM enrichment_iterations WHERE schedule_id=? AND status='running'", SCHEDULE_ID);
      if (active && active.lease_until > now) return {status: 'leased'};
      // On restart, first reconcile a completed processor receipt. Do not select a second paper.
      if (active) {
        const previous = await this.resolve(active.scheduled_at, active.attempts);
        if (previous && terminal.has(previous.status)) this.finish(active, previous, 'completed');
        else this.storage.transactionSync(() => {
          this.rows("UPDATE enrichment_iteration_attempts SET outcome='interrupted',finished_at=?,error_code='lease_expired' WHERE schedule_id=? AND scheduled_at=? AND attempt=? AND outcome='running'", now, SCHEDULE_ID, active.scheduled_at, active.attempts);
          this.rows("UPDATE enrichment_iterations SET status='pending',lease_token=NULL,lease_until=NULL,retry_at=?,error_code='lease_expired' WHERE schedule_id=? AND scheduled_at=? AND lease_token=?", now, SCHEDULE_ID, active.scheduled_at, active.lease_token);
        });
      }
      job = this.storage.transactionSync(() => {
        if (this.one("SELECT 1 AS n FROM enrichment_iterations WHERE schedule_id=? AND status='running'", SCHEDULE_ID)) return null;
        const selected = this.one("SELECT * FROM enrichment_iterations WHERE schedule_id=? AND status='pending' AND retry_at<=? ORDER BY scheduled_at LIMIT 1", SCHEDULE_ID, this.clock());
        if (!selected) return null;
        const token = crypto.randomUUID(), attempt = selected.attempts + 1, time = this.clock();
        this.rows("UPDATE enrichment_iterations SET status='running',attempts=?,lease_token=?,lease_until=?,started_at=COALESCE(started_at,?) WHERE schedule_id=? AND scheduled_at=? AND status='pending'", attempt, token, time + LEASE, time, SCHEDULE_ID, selected.scheduled_at);
        this.rows("INSERT INTO enrichment_iteration_attempts VALUES (?,?,?,?,?,NULL,'running',NULL,NULL)", SCHEDULE_ID, selected.scheduled_at, attempt, token, time);
        return {...selected, attempts: attempt, lease_token: token};
      });
      if (!job) return {status: 'idle'};
      // Persist recovery wake-up before any network work. No cancellation of a live invocation.
      await this.storage.setAlarm(this.clock() + LEASE);
      const receipt = await this.processor(job.scheduled_at, job.attempts);
      if (terminal.has(receipt.status)) this.finish(job, receipt, 'completed');
      else if (receipt.status === 'failed' && receipt.selected_job_id) this.finish(job, receipt, 'failed');
      else this.defer(job, receipt.error_code || (receipt.status === 'leased' ? 'processor_leased' : 'processor_unavailable'));
      return receipt;
    } catch (error) {
      if (job) this.defer(job, 'scheduler_operation_failed');
      throw error;
    } finally {
      this.busy = false;
      this.enqueue(); // Account for the hour boundary crossed while the processor was running.
      await this.arm(); // Pending work wakes immediately rather than waiting until next hour.
    }
  }
  finish(job, receipt, status) {
    this.storage.transactionSync(() => {
      const current = this.one('SELECT * FROM enrichment_iterations WHERE schedule_id=? AND scheduled_at=?', SCHEDULE_ID, job.scheduled_at);
      if (current?.status !== 'running' || current.lease_token !== job.lease_token) throw Error('iteration_fence_lost');
      this.rows('UPDATE enrichment_iteration_attempts SET outcome=?,finished_at=?,run_id=?,error_code=? WHERE schedule_id=? AND scheduled_at=? AND attempt=? AND outcome=\'running\'', status, this.clock(), receipt.run_id || null, receipt.error_code || null, SCHEDULE_ID, job.scheduled_at, job.attempts);
      this.rows('UPDATE enrichment_iterations SET status=?,finished_at=?,run_id=?,error_code=?,lease_token=NULL,lease_until=NULL WHERE schedule_id=? AND scheduled_at=? AND lease_token=?', status, this.clock(), receipt.run_id || null, receipt.error_code || null, SCHEDULE_ID, job.scheduled_at, job.lease_token);
    });
  }
  defer(job, code) {
    this.storage.transactionSync(() => {
      const current = this.one('SELECT * FROM enrichment_iterations WHERE schedule_id=? AND scheduled_at=?', SCHEDULE_ID, job.scheduled_at);
      if (current?.status !== 'running' || current.lease_token !== job.lease_token) return;
      this.rows("UPDATE enrichment_iteration_attempts SET outcome='deferred',finished_at=?,error_code=? WHERE schedule_id=? AND scheduled_at=? AND attempt=? AND outcome='running'", this.clock(), code, SCHEDULE_ID, job.scheduled_at, job.attempts);
      this.rows("UPDATE enrichment_iterations SET status='pending',retry_at=?,error_code=?,lease_token=NULL,lease_until=NULL WHERE schedule_id=? AND scheduled_at=? AND lease_token=?", this.clock() + Math.min(RETRY * 2 ** Math.min(job.attempts - 1, 6), HOUR), code, SCHEDULE_ID, job.scheduled_at, job.lease_token);
    });
  }
}
