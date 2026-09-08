import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import { canonicalJson, sha256, CRITERIA, validateProposal, verifyHumanApproval, handleV2 } from "../src/review-v2.js";
import { romeClock, romeTime, dayOutcome, runDay, superviseDays, validateQueryManifest } from "../src/daily-runner.js";

function database() {
  const sqlite = new DatabaseSync(":memory:");
  sqlite.exec(readFileSync(new URL("../migrations/0001_review_v2.sql", import.meta.url), "utf8"));
  sqlite.exec(readFileSync(new URL("../migrations/0002_open_access.sql", import.meta.url), "utf8"));
  const db = { sqlite,
    prepare(sql) { let values = []; return {
      bind(...args) { values = args; return this; },
      async first() { return sqlite.prepare(sql).get(...values) || null; },
      async all() { return { results: sqlite.prepare(sql).all(...values) }; },
      async run() { return { meta: { changes: Number(sqlite.prepare(sql).run(...values).changes) } }; },
    }; },
    async batch(statements) { sqlite.exec("BEGIN"); try { const result = []; for (const s of statements) result.push(await s.run()); sqlite.exec("COMMIT"); return result; } catch (e) { sqlite.exec("ROLLBACK"); throw e; } },
  };
  return db;
}
function setup() {
  const db = database();
  db.sqlite.exec(`INSERT INTO legacy_snapshots VALUES ('TEST-SNAPSHOT','TEST-COMMIT','TEST-HASH','test/private/snapshot',1,'2026-09-08T00:00:00Z','2026-09-08T00:00:00Z');
    INSERT INTO reviews VALUES ('TEST-REVIEW','Synthetic test review','CILE-4PT-OA-v3','0.3.0','active','Europe/Rome','2026-09-08','2026-09-08T00:00:00Z','TEST-SNAPSHOT','2026-09-08T00:00:00Z');
    INSERT INTO scholarly_works VALUES ('TEST-WORK','Synthetic test publication','book_chapter',NULL,'2026-09-08T00:00:00Z');
    INSERT INTO review_candidates VALUES ('TEST-REVIEW','TEST-CANDIDATE','TEST-WORK','Synthetic test publication','verified','screening',1,'TEST-ORIGIN','2026-09-08T00:00:00Z');`);
  const store = new Map(), env = { REVIEW_DB: db, REVIEW_EVIDENCE: { async put(key, value) { store.set(key, value); }, async get(key) { return store.has(key) ? { async text() { return store.get(key); } } : null; } } };
  const fixtureText = "Synthetic, complete OA source used only by automated tests.";
  db.sqlite.prepare("INSERT INTO evidence_sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?)").run("TEST-REVIEW", "TEST-OA-TEXT", "TEST-CANDIDATE", null, null, "https://example.org/full.pdf", "full_text", "verified", "a".repeat(64), "test/oa", "Synthetic authored text", "2026-09-08T00:00:00Z");
  db.sqlite.prepare("INSERT INTO access_assessments_v2 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)").run("TEST-OA", "TEST-REVIEW", "TEST-CANDIDATE", "TEST-OA-TEXT", "https://example.org/full.pdf", "accepted", "repository", null, "Synthetic authorised deposit", "https://example.org/rights", "verified_open", "anonymous_full_text_verified", "2026-09-08T00:00:00Z", "human-curator", null);
  store.set("test/oa", fixtureText);
  return { db, env, store };
}
function context() {
  return { access: { assessment_id: "TEST-OA", review_id: "TEST-REVIEW", candidate_id: "TEST-CANDIDATE", access_status: "verified_open" }, actor: "human-curator", review: { review_id: "TEST-REVIEW", phase: "active", protocol_version: "CILE-4PT-OA-v3" }, candidate: { review_id: "TEST-REVIEW", candidate_id: "TEST-CANDIDATE", record_version: 1, work_id: "TEST-WORK", identity_state: "verified" }, spans: [{ review_id: "TEST-REVIEW", candidate_id: "TEST-CANDIDATE", span_id: "TEST-SPAN", identity_state: "verified", evidence_kind: "abstract" }] };
}
function proposal() { return { access_assessment_id: "TEST-OA", proposal_id: "TEST-PROPOSAL-01", review_id: "TEST-REVIEW", candidate_id: "TEST-CANDIDATE", expected_version: 1, protocol_version: "CILE-4PT-OA-v3", decision: "eligible_core", stage: "title_abstract", confidence: "medium", rationale: "Synthetic source-grounded reasoning for this fixture.", exclusion_reason: "", duplicate_target: "", supersedes_id: null, criteria: CRITERIA.map((criterion_id) => ({ criterion_id, outcome: "YES", rationale: "Synthetic criterion-specific evidence.", evidence_span_ids: ["TEST-SPAN"] })) }; }
const request = (path, body) => new Request(`https://curator.example/api/v2/${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

test("OA is an independent gate and proposals bind the current access receipt", () => {
  for (const access of [null, { ...context().access, access_status: "revoked" }, { ...context().access, candidate_id: "ANOTHER" }, { ...context().access, assessment_id: "NEW-RECEIPT" }]) {
    assert.throws(() => validateProposal(proposal(), { ...context(), access }), /current_open_access/);
  }
  const p = proposal(); p.decision = "needs_full_text"; p.access_assessment_id = null;
  assert.equal(validateProposal(p, { ...context(), access: null }).decision, "needs_full_text");
});

test("access attestation checks retained full text, is idempotent and supports revocation", async () => {
  const { db, env } = setup(), session = { login: "human-curator" };
  const acquired = await handleV2(request("evidence", { candidate_id: "TEST-CANDIDATE", expected_version: 1, source_url: "https://example.org/complete.txt", evidence_kind: "full_text", identity_state: "verified", rights_basis: "Test-authored full text", text: "Complete synthetic test publication.", spans: [{ locator: "Body", start_offset: 0, end_offset: 8 }] }), env, session);
  assert.equal(acquired.status, 201);
  const evidence = await acquired.json();
  const input = { assessment_id: "OA-NEW-TEST", candidate_id: "TEST-CANDIDATE", expected_version: 2, evidence_id: evidence.evidence_id, full_text_url: "https://example.org/complete.txt", version_type: "accepted", host_type: "repository", license_uri: null, rights_basis: "Test-authored lawful deposit", rights_evidence_url: "https://example.org/rights", access_status: "verified_open", verification_method: "anonymous_full_text_verified", supersedes_id: "TEST-OA" };
  const bad = await handleV2(request("access-assessments", { ...input, full_text_url: "https://example.org/unrelated.pdf" }), env, session);
  assert.equal(bad.status, 422);
  const valid = await handleV2(request("access-assessments", input), env, session);
  assert.equal(valid.status, 201, JSON.stringify(await valid.clone().json()));
  const replay = await handleV2(request("access-assessments", input), env, session);
  assert.equal((await replay.json()).replayed, true);
  assert.equal(db.sqlite.prepare("SELECT record_version FROM review_candidates").get().record_version, 3);
  const revoked = await handleV2(request("access-assessments", { ...input, assessment_id: "OA-REVOKED", expected_version: 3, access_status: "revoked", verification_method: "access_observation", supersedes_id: "OA-NEW-TEST" }), env, session);
  assert.equal(revoked.status, 201, JSON.stringify(await revoked.clone().json()));
  assert.equal(db.sqlite.prepare("SELECT count(*) n FROM v2_open_access_candidates").get().n, 0);
  assert.equal(db.sqlite.prepare("SELECT count(*) n FROM access_assessments_v2").get().n, 3);
  assert.equal(db.sqlite.prepare("SELECT count(*) n FROM screening_decisions_v2").get().n, 0);
  assert.throws(() => db.sqlite.exec("DELETE FROM access_assessments_v2"), /append_only/);
});

test("SQL OA gate rejects abstracts and cross-candidate supersession", () => {
  const { db } = setup();
  db.sqlite.exec("INSERT INTO evidence_sources SELECT review_id,'ABSTRACT',candidate_id,manifestation_id,attempt_id,source_url,'abstract',identity_state,content_sha256,storage_key,rights_basis,observed_at FROM evidence_sources LIMIT 1");
  assert.throws(() => db.sqlite.exec("INSERT INTO access_assessments_v2 SELECT 'BAD-OA',review_id,candidate_id,'ABSTRACT',full_text_url,version_type,host_type,license_uri,rights_basis,rights_evidence_url,access_status,verification_method,verified_at,attributed_to,'TEST-OA' FROM access_assessments_v2 LIMIT 1"), /verified_full_text/);
  assert.throws(() => db.sqlite.exec("INSERT INTO access_assessments_v2 SELECT 'BAD-NULL',review_id,candidate_id,evidence_id,full_text_url,NULL,host_type,license_uri,rights_basis,rights_evidence_url,access_status,verification_method,verified_at,attributed_to,'TEST-OA' FROM access_assessments_v2 LIMIT 1"), /CHECK constraint/);
  assert.throws(() => db.sqlite.exec("INSERT INTO access_assessments_v2 SELECT 'BAD-SCOPE',review_id,'ANOTHER',NULL,NULL,NULL,NULL,NULL,rights_basis,NULL,'unknown','access_observation',verified_at,attributed_to,'TEST-OA' FROM access_assessments_v2 LIMIT 1"), /scope_mismatch/);
});

test("migration creates no scientific data and DOI-less bibliography is representable", () => {
  const db = database();
  for (const { name } of db.sqlite.prepare("SELECT name FROM sqlite_master WHERE type='table'").all()) assert.equal(db.sqlite.prepare(`SELECT count(*) n FROM ${name}`).get().n, 0);
  const { db: fixture } = setup(); assert.equal(fixture.sqlite.prepare("SELECT count(*) n FROM bibliographic_identifiers").get().n, 0);
  assert.throws(() => db.sqlite.exec("INSERT INTO reviews VALUES ('R','Test','CILE-4PT-OA-v3','0.3.0','active','Europe/Rome','2026-09-08','2026-09-08T00:00:00Z','MISSING-SNAPSHOT','2026-09-08T00:00:00Z')"), /verified_complete_snapshot_required/);
});
test("four-part core gate rejects uncertainty, stale input, wrong review and generated evidence", () => {
  assert.equal(validateProposal(proposal(), context()).decision, "eligible_core");
  const uncertain = proposal(); uncertain.criteria[2].outcome = "UNCERTAIN";
  assert.throws(() => validateProposal(uncertain, context()), /core_requires_four_yes/);
  assert.throws(() => validateProposal({ ...proposal(), expected_version: 2 }, context()), /stale_candidate/);
  assert.throws(() => validateProposal({ ...proposal(), review_id: "legacy" }, context()), /review_mismatch/);
  const generated = context(); generated.spans[0].evidence_kind = "model_summary";
  assert.throws(() => validateProposal(proposal(), generated), /non_source_evidence/);
  const wrongWork = context(); wrongWork.spans[0].candidate_id = "ANOTHER-CANDIDATE";
  assert.throws(() => validateProposal(proposal(), wrongWork), /non_source_evidence/);
});
test("approval must be human, on the exact head, and bind the exact payload hash", async () => {
  const p = { proposal_id: "TEST-PROPOSAL-01", payload_sha256: await sha256(canonicalJson(proposal())), protocol_version: "CILE-4PT-OA-v3" };
  const args = { repository: "owner/review", prNumber: 10, proposal: p, token: "test", humanLogin: "owner" };
  const manifest = { proposal_id: p.proposal_id, payload_sha256: p.payload_sha256, protocol_version: p.protocol_version, action: "approve_screening" };
  const review = { id: 1, user: { login: "owner", type: "User" }, state: "APPROVED", commit_id: "HEAD1", submitted_at: "2026-09-08T08:00:00Z" };
  const get = async (path) => path.includes("/contents/") ? { encoding: "base64", size: 200, content: btoa(JSON.stringify(manifest)) } : path.includes("/reviews?") ? [review] : { merged: true, head: { sha: "HEAD1", repo: { full_name: "owner/review" } }, base: { ref: "main", repo: { full_name: "owner/review" } } };
  assert.equal((await verifyHumanApproval(args, get)).human_login, "owner");
  review.user.type = "Bot"; await assert.rejects(verifyHumanApproval(args, get), /human_approval/); review.user.type = "User";
  review.commit_id = "OLDHEAD"; await assert.rejects(verifyHumanApproval(args, get), /human_approval/); review.commit_id = "HEAD1";
  manifest.payload_sha256 = "wrong"; await assert.rejects(verifyHumanApproval(args, get), /hash_mismatch/);
});
test("private evidence acquisition preserves bytes and offsets; proposals do not create decisions", async () => {
  const { db, env } = setup();
  const input = { candidate_id: "TEST-CANDIDATE", expected_version: 1, source_url: "https://example.org/test-source", evidence_kind: "abstract", identity_state: "verified", rights_basis: "Synthetic test content authored for the test", text: "  Synthetic source text for the integration test.  ", spans: [{ locator: "Abstract, sentence 1", start_offset: 2, end_offset: 23 }] };
  const response = await handleV2(request("evidence", input), env, { login: "human-curator" });
  assert.equal(response.status, 201, JSON.stringify(await response.clone().json()));
  const evidence = await response.json(); assert.equal(evidence.content_sha256, await sha256(input.text));
  const p = proposal(); p.expected_version = 2; p.criteria.forEach((c) => c.evidence_span_ids = [evidence.spans[0].span_id]);
  const submit = await handleV2(request("proposals", p), env, { login: "human-curator" });
  assert.equal(submit.status, 201, JSON.stringify(await submit.clone().json()));
  assert.equal(db.sqlite.prepare("SELECT count(*) n FROM decision_proposals").get().n, 1);
  assert.equal(db.sqlite.prepare("SELECT count(*) n FROM screening_decisions_v2").get().n, 0);
  assert.equal(db.sqlite.prepare("SELECT count(*) n FROM publication_approvals_v2").get().n, 0);
  assert.equal((await handleV2(request("proposals", p), env, { login: "human-curator" })).status, 200);
  assert.throws(() => db.sqlite.exec("DELETE FROM decision_proposals"), /append_only/);
  p.rationale = "Changed after submission";
  assert.equal((await handleV2(request("proposals", p), env, { login: "human-curator" })).status, 409);
});
test("Rome daily scheduling preserves 07:00 across both DST changes", () => {
  for (const day of ["2026-03-28", "2026-03-29", "2026-10-24", "2026-10-25"]) assert.deepEqual(romeClock(romeTime(day)), { date: day, minute: 420 });
  assert.equal(romeTime("2026-10-25"), "2026-10-25T06:00:00.000Z");
  assert.equal(romeTime("2026-03-29"), "2026-03-29T05:00:00.000Z");
});
function manifest() { return { protocol_version: "CILE-DAILY-v2", queries: ["Consensus", "Exa"].flatMap((provider) => Array.from({ length: 7 }, (_, i) => ({ provider, window: `W${i + 1}`, query_id: `${provider}-W${i + 1}`, text: `Synthetic approved window ${i + 1}` }))) }; }
test("checkpoints count once; failed queries are unknown, measured zeros remain zero", async () => {
  const { db, env } = setup(), m = validateQueryManifest(manifest());
  db.sqlite.prepare("INSERT INTO search_days VALUES (?,?,?,?,?,?,?,?)").run("TEST-REVIEW", "2026-09-08", "Europe/Rome", m.protocol_version, canonicalJson(m), "planned", "2026-09-08T05:20:00Z", "2026-09-08T00:00:00Z");
  let calls = 0;
  const now = Date.now();
  const run = await runDay(env, "TEST-REVIEW", "2026-09-08", { now, search: async () => { calls++; return []; } });
  assert.equal(run.status, "completed"); assert.equal(calls, 14);
  const replay = await runDay(env, "TEST-REVIEW", "2026-09-08", { now, search: async () => { throw Error("must not rerun"); } });
  assert.equal(replay.status, "completed");
  assert.equal(db.sqlite.prepare("SELECT sum(occurrences_returned) n FROM query_executions").get().n, 0);
  assert.equal(dayOutcome(m.queries, [{ ...m.queries[0], status: "completed" }, { ...m.queries[0], status: "completed" }]).queries_completed, 1);
});
test("partial recovery only retries unfinished queries and preserves the failed attempt", async () => {
  const { db, env } = setup(), m = manifest();
  db.sqlite.prepare("INSERT INTO search_days VALUES (?,?,?,?,?,?,?,?)").run("TEST-REVIEW", "2026-09-08", "Europe/Rome", m.protocol_version, canonicalJson(m), "planned", "2026-09-08T05:20:00Z", "2026-09-08T00:00:00Z");
  const now = Date.now(); let first = true, calls = 0;
  const partial = await runDay(env, "TEST-REVIEW", "2026-09-08", { now, search: async (_, q) => { if (first && q.query_id === "Consensus-W1") { first = false; throw Error("outage"); } return []; } });
  assert.equal(partial.status, "partial");
  const recovered = await runDay(env, "TEST-REVIEW", "2026-09-08", { now: now + 21 * 60000, search: async () => { calls++; return []; } });
  assert.equal(recovered.status, "completed"); assert.equal(calls, 1);
  assert.equal(db.sqlite.prepare("SELECT count(*) n FROM query_executions WHERE status='failed' AND occurrences_returned IS NULL").get().n, 1);
  assert.equal(db.sqlite.prepare("SELECT count(*) n FROM run_attempts").get().n, 2);
});

test("an expired final lease remains visible as a failed day with immutable attempt history", async () => {
  const { db, env } = setup(), m = manifest(), now = Date.parse("2026-09-08T08:00:00Z");
  db.sqlite.prepare("INSERT INTO search_days VALUES (?,?,?,?,?,?,?,?)").run("TEST-REVIEW", "2026-09-08", "Europe/Rome", m.protocol_version, canonicalJson(m), "running", "2026-09-08T05:20:00Z", "2026-09-08T00:00:00Z");
  for (let n = 1; n <= 3; n++) db.sqlite.prepare("INSERT INTO run_attempts(attempt_id,review_id,scheduled_date,attempt_number,started_at,lease_until,status) VALUES (?,?,?,?,?,?,?)").run(`ATTEMPT-${n}`, "TEST-REVIEW", "2026-09-08", n, "2026-09-08T05:00:00Z", "2026-09-08T05:10:00Z", n === 3 ? "running" : "failed");
  let deliveries = 0;
  Object.assign(env, { REVIEW_V2_RUNNER_ENABLED: "true", CONSENSUS_SEARCH: {}, REVIEW_DAILY_QUERY_MANIFEST: canonicalJson(m), REVIEW_JOBS: { async send() { deliveries++; } } });
  await superviseDays(env, now);
  assert.equal(deliveries, 0);
  assert.equal(db.sqlite.prepare("SELECT status FROM search_days WHERE scheduled_date='2026-09-08'").get().status, "failed");
  assert.equal(db.sqlite.prepare("SELECT status FROM run_attempts WHERE attempt_number=3").get().status, "expired");
  assert.throws(() => db.sqlite.exec("UPDATE run_attempts SET status='completed' WHERE attempt_number=3"), /final_attempt_immutable/);
  const exhausted = await runDay(env, "TEST-REVIEW", "2026-09-08", { now, search: async () => { throw Error("must not execute a fourth attempt"); } });
  assert.equal(exhausted.retry_exhausted, true);
});

test("verified approval import records one decision and four criteria atomically, without publication", async (t) => {
  const { db, env } = setup();
  Object.assign(env, { GITHUB_REPOSITORY: "owner/review", CURATOR_LOGIN: "owner" });
  const session = { login: "owner", token: "test-token" };
  const acquired = await handleV2(request("evidence", { candidate_id: "TEST-CANDIDATE", expected_version: 1, source_url: "https://example.org/test-source", evidence_kind: "abstract", identity_state: "verified", rights_basis: "Synthetic test text", text: "Synthetic source content.", spans: [{ locator: "Abstract", start_offset: 0, end_offset: 9 }] }), env, session);
  const evidence = await acquired.json(), p = proposal();
  p.expected_version = 2;
  p.criteria.forEach((c) => c.evidence_span_ids = [evidence.spans[0].span_id]);
  assert.equal((await handleV2(request("proposals", p), env, session)).status, 201);
  const saved = db.sqlite.prepare("SELECT * FROM decision_proposals").get();
  const manifest = { proposal_id: saved.proposal_id, payload_sha256: saved.payload_sha256, protocol_version: saved.protocol_version, action: "approve_screening" };
  let exactHead = false;
  t.mock.method(globalThis, "fetch", async (input) => {
    const url = String(input);
    if (url.includes("/reviews?")) return Response.json([{ id: 1, user: { login: "owner", type: "User" }, state: "APPROVED", commit_id: exactHead ? "HEAD1" : "OLDHEAD", submitted_at: "2026-09-08T08:00:00Z" }]);
    if (url.includes("/contents/")) return Response.json({ encoding: "base64", size: 200, content: btoa(JSON.stringify(manifest)) });
    return Response.json({ merged: true, head: { sha: "HEAD1", repo: { full_name: "owner/review" } }, base: { ref: "main", repo: { full_name: "owner/review" } } });
  });
  const input = { proposal_id: p.proposal_id, pr_number: 10 };
  assert.equal((await handleV2(request("approval-import", input), env, session)).status, 409);
  assert.equal(db.sqlite.prepare("SELECT count(*) n FROM approval_receipts").get().n, 0);
  exactHead = true;
  const imported = await handleV2(request("approval-import", input), env, session);
  assert.equal(imported.status, 200, JSON.stringify(await imported.clone().json()));
  assert.equal(db.sqlite.prepare("SELECT count(*) n FROM screening_decisions_v2").get().n, 1);
  assert.equal(db.sqlite.prepare("SELECT count(*) n FROM criterion_assessments").get().n, 4);
  assert.equal(db.sqlite.prepare("SELECT count(*) n FROM publication_approvals_v2").get().n, 0);
  assert.equal(db.sqlite.prepare("SELECT record_version FROM review_candidates").get().record_version, 3);
  const replay = await handleV2(request("approval-import", input), env, session);
  assert.equal((await replay.json()).replayed, true);
  assert.equal(db.sqlite.prepare("SELECT count(*) n FROM screening_decisions_v2").get().n, 1);
});
