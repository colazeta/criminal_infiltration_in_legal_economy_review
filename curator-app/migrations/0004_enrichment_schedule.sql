-- Additive operational schedule. No candidate, evidence or scientific decision changes.
CREATE TABLE IF NOT EXISTS enrichment_schedules (
 schedule_id TEXT PRIMARY KEY, protocol_version TEXT NOT NULL,
 first_slot INTEGER NOT NULL, next_slot INTEGER NOT NULL, created_at INTEGER NOT NULL,
 CHECK(first_slot % 3600000 = 2400000), CHECK(next_slot % 3600000 = 2400000)
);
CREATE TABLE IF NOT EXISTS enrichment_iterations (
 schedule_id TEXT NOT NULL REFERENCES enrichment_schedules(schedule_id), scheduled_at INTEGER NOT NULL,
 materialised_at INTEGER NOT NULL, status TEXT NOT NULL CHECK(status IN ('pending','running','completed','failed')),
 attempts INTEGER NOT NULL DEFAULT 0, lease_token TEXT, lease_until INTEGER, retry_at INTEGER NOT NULL,
 started_at INTEGER, finished_at INTEGER, run_id TEXT, error_code TEXT,
 PRIMARY KEY(schedule_id,scheduled_at), CHECK(scheduled_at % 3600000 = 2400000)
);
CREATE UNIQUE INDEX IF NOT EXISTS enrichment_one_iteration ON enrichment_iterations(schedule_id) WHERE status='running';
CREATE TABLE IF NOT EXISTS enrichment_iteration_attempts (
 schedule_id TEXT NOT NULL, scheduled_at INTEGER NOT NULL, attempt INTEGER NOT NULL,
 lease_token TEXT NOT NULL, started_at INTEGER NOT NULL, finished_at INTEGER,
 outcome TEXT NOT NULL CHECK(outcome IN ('running','completed','failed','interrupted','deferred')),
 run_id TEXT, error_code TEXT,
 PRIMARY KEY(schedule_id,scheduled_at,attempt),
 FOREIGN KEY(schedule_id,scheduled_at) REFERENCES enrichment_iterations(schedule_id,scheduled_at)
);
CREATE TRIGGER IF NOT EXISTS enrichment_iteration_attempts_terminal_immutable
 BEFORE UPDATE ON enrichment_iteration_attempts WHEN OLD.outcome<>'running'
 BEGIN SELECT RAISE(ABORT,'terminal_attempt_immutable'); END;
CREATE TRIGGER IF NOT EXISTS enrichment_iteration_attempts_no_delete
 BEFORE DELETE ON enrichment_iteration_attempts BEGIN SELECT RAISE(ABORT,'append_only'); END;
CREATE TRIGGER IF NOT EXISTS enrichment_iterations_no_delete
 BEFORE DELETE ON enrichment_iterations BEGIN SELECT RAISE(ABORT,'append_only'); END;
