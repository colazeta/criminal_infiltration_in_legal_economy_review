import { canonicalJson, sha256, V2Error } from "./review-v2.js";
import { fetchWithTimeout } from "./network.js";
import { reserveProjectProviderBudget, budgetFor } from "./provider-budget.js";
import { queryManifestProblem } from "./daily-source-policy.js";

const iso = (value) => new Date(value).toISOString();
const statement = (db, sql, ...values) => db.prepare(sql).bind(...values);
const results = async (db, sql, ...values) => (await statement(db, sql, ...values).all()).results;
export function romeClock(now) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Rome", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(new Date(now)).map((p) => [p.type, p.value]));
  return { date: `${parts.year}-${parts.month}-${parts.day}`, minute: Number(parts.hour) * 60 + Number(parts.minute) };
}
export function romeTime(day, hour = 7, minute = 0) {
  // Resolve the local civil time via Intl, including both DST transitions.
  let moment = Date.parse(`${day}T${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:00Z`);
  for (let i = 0; i < 3; i++) {
    const local = romeClock(moment);
    const target = Date.parse(`${day}T00:00:00Z`) + (hour * 60 + minute) * 60000;
    const actual = Date.parse(`${local.date}T00:00:00Z`) + local.minute * 60000;
    moment += target - actual;
  }
  return iso(moment);
}
export function validateQueryManifest(manifest) {
  const problem = queryManifestProblem(manifest);
  if (problem) throw new V2Error(problem);
  return manifest;
}
export function dayOutcome(expected, checkpoints) {
  const keys = new Set(checkpoints.filter((c) => c.status === "completed").map((c) => `${c.provider}:${c.query_id}`));
  const complete = expected.filter((q) => keys.has(`${q.provider}:${q.query_id}`));
  return { status: complete.length === expected.length ? "completed" : complete.length ? "partial" : "failed", queries_completed: complete.length };
}
function failure(error) {
  return ["budget_exhausted", "provider_not_configured", "rate_limited", "authentication_failed", "invalid_provider_response"].includes(error?.code) ? error.code : "provider_unavailable";
}
async function providerSearch(env, query, context) {
  if (query.provider !== "Exa") throw new V2Error("invalid_query_manifest");
  if (!env.EXA_API_KEY || env.EXA_FREE_ONLY !== "true" || env.EXA_DEDICATED_STARTER_ACCOUNT !== "true") throw new V2Error("provider_not_configured");
  const budget = await reserveProjectProviderBudget(env, "exa", `${context.review_id}/${context.scheduled_date}/${query.query_id}`);
  if (!budget.allowed) throw new V2Error("budget_exhausted");
  const response = await fetchWithTimeout("https://api.exa.ai/search", { method: "POST", headers: { "Content-Type": "application/json", "x-api-key": env.EXA_API_KEY }, body: JSON.stringify({ query: query.text, type: "fast", category: "research paper", numResults: 5 }) });
  if (response.status === 429) {
    const error = new V2Error("rate_limited");
    const retry = response.headers.get("Retry-After"), seconds = Number(retry);
    error.retryAfter = retry && Number.isFinite(seconds) ? Date.now() + seconds * 1000 : Date.parse(retry || "");
    throw error;
  }
  if ([401, 403].includes(response.status)) throw new V2Error("authentication_failed");
  if (response.status === 402) throw new V2Error("budget_exhausted");
  if (!response.ok) throw new V2Error("provider_unavailable");
  const payload = await response.json();
  if (query.provider === "Exa" && (!Number.isFinite(payload?.costDollars?.total) || payload.costDollars.total > budgetFor("exa").maxUnitCostUsd || payload.costDollars.total < 0)) throw new V2Error("budget_exhausted");
  if (!Array.isArray(payload.results) || payload.results.length > 10) throw new V2Error("invalid_provider_response");
  // Strip provider extras and any text bodies; search discovery does not acquire full text.
  return payload.results.map((r, i) => {
    if (typeof r.title !== "string" || !r.title.trim() || typeof r.url !== "string" || !r.url.startsWith("https://")) throw new V2Error("invalid_provider_response");
    return { title: r.title.slice(0, 1000), url: r.url.slice(0, 2000), rank: i + 1, provider: query.provider };
  });
}

async function recoverDay(db, reviewId, day, manifest, now) {
  await statement(db, "UPDATE run_attempts SET status='expired',finished_at=?,error_code='lease_expired' WHERE review_id=? AND scheduled_date=? AND status='running' AND lease_until<=?", iso(now), reviewId, day, iso(now)).run();
  const previous = await statement(db, "SELECT * FROM run_attempts WHERE review_id=? AND scheduled_date=? ORDER BY attempt_number DESC LIMIT 1", reviewId, day).first();
  if (previous && previous.status !== "running") {
    const checkpoints = await results(db, "SELECT provider,query_id,status FROM query_executions WHERE review_id=? AND scheduled_date=?", reviewId, day);
    const outcome = dayOutcome(manifest.queries, checkpoints);
    if (previous.attempt_number >= 3 || outcome.status === "completed") {
      await statement(db, "UPDATE search_days SET status=? WHERE review_id=? AND scheduled_date=? AND status <> 'cancelled_authorized'", outcome.status, reviewId, day).run();
      return { previous, terminal: { ...outcome, retry_exhausted: previous.attempt_number >= 3 && outcome.status !== "completed" } };
    }
  }
  return { previous, terminal: null };
}

export async function runDay(env, reviewId, day, { now = Date.now(), search = providerSearch } = {}) {
  const db = env.REVIEW_DB;
  if (!db || !env.REVIEW_EVIDENCE) throw new V2Error("private_storage_required", 503);
  const review = await statement(db, "SELECT * FROM reviews WHERE review_id=? AND phase='active'", reviewId).first();
  if (!review) return { status: "paused" };
  const searchDay = await statement(db, "SELECT * FROM search_days WHERE review_id=? AND scheduled_date=?", reviewId, day).first();
  if (!searchDay || searchDay.status === "cancelled_authorized" || searchDay.status === "completed") return { status: searchDay?.status || "not_planned" };
  const manifest = validateQueryManifest(JSON.parse(searchDay.query_manifest_json));
  const { previous, terminal } = await recoverDay(db, reviewId, day, manifest, now);
  if (terminal) return terminal;
  if (previous?.status === "running") return { status: "leased" };
  if (previous && Date.parse(previous.retry_after || previous.lease_until) > now) return { status: "retry_wait" };
  const attemptId = crypto.randomUUID(), attemptNumber = (previous?.attempt_number || 0) + 1;
  // Unique active lease and unique attempt ordinal make duplicate queue delivery harmless.
  try {
    await db.batch([
      statement(db, "INSERT INTO run_attempts(attempt_id,review_id,scheduled_date,attempt_number,started_at,lease_until,status) VALUES (?,?,?,?,?,?,'running')", attemptId, reviewId, day, attemptNumber, iso(now), iso(now + 10 * 60000)),
      statement(db, "UPDATE search_days SET status='running' WHERE review_id=? AND scheduled_date=?", reviewId, day),
    ]);
  } catch (error) {
    if (/UNIQUE constraint failed/.test(String(error))) return { status: "duplicate_delivery" };
    throw error;
  }
  let retryAt = now + (attemptNumber === 1 ? 20 : 60) * 60000, errorCode = null;
  const blockedProviders = new Set();
  for (const query of manifest.queries) {
    if (blockedProviders.has(query.provider)) continue;
    const known = await statement(db, "SELECT 1 FROM query_executions WHERE review_id=? AND scheduled_date=? AND provider=? AND query_id=? AND status='completed'", reviewId, day, query.provider, query.query_id).first();
    if (known) continue;
    const started = new Date().toISOString(), executionId = crypto.randomUUID();
    let status = "completed", items = null, key = null, code = null;
    try {
      items = await search(env, query, { review_id: reviewId, scheduled_date: day });
      const encoded = canonicalJson(items), hash = await sha256(encoded);
      key = `${reviewId}/discovery/${day}/${executionId}/${hash}.json`;
      await env.REVIEW_EVIDENCE.put(key, encoded, { httpMetadata: { contentType: "application/json" } });
    } catch (error) {
      status = "failed"; code = failure(error); errorCode = code; items = null; key = null;
      if (Number.isFinite(error.retryAfter)) retryAt = Math.max(retryAt, error.retryAfter);
    }
    const finished = new Date().toISOString();
    const insert = statement(db, `INSERT INTO query_executions SELECT ?,?,?,?,?,?,?,?,?,?,?,?
      FROM run_attempts WHERE attempt_id=? AND status='running' AND lease_until>?`, executionId, attemptId, reviewId, day, query.provider, query.query_id, status, started, finished, items?.length ?? null, key, code, attemptId, finished);
    const batch = [insert];
    if (items?.length) batch.push(...items.map((r) => statement(db,
      "INSERT INTO discovery_occurrences SELECT ?,?,?,?,?,?,?,?,? WHERE EXISTS (SELECT 1 FROM query_executions WHERE execution_id=?)",
      crypto.randomUUID(), reviewId, executionId, null, query.provider, r.url, r.rank, canonicalJson(r), finished, executionId)));
    const saved = await db.batch(batch);
    if (!saved[0].meta?.changes) return { status: "lease_lost" };
    if (["rate_limited", "budget_exhausted", "authentication_failed", "provider_not_configured"].includes(code)) blockedProviders.add(query.provider);
  }
  const checkpoints = await results(db, "SELECT provider,query_id,status FROM query_executions WHERE review_id=? AND scheduled_date=?", reviewId, day);
  const outcome = dayOutcome(manifest.queries, checkpoints), finished = new Date().toISOString();
  const finalised = await db.batch([
    statement(db, "UPDATE run_attempts SET status=?,finished_at=?,error_code=?,retry_after=? WHERE attempt_id=? AND status='running' AND lease_until>?", outcome.status, finished, errorCode, iso(retryAt), attemptId, finished),
    statement(db, "UPDATE search_days SET status=? WHERE review_id=? AND scheduled_date=? AND status <> 'cancelled_authorized' AND EXISTS (SELECT 1 FROM run_attempts WHERE attempt_id=? AND status=? AND finished_at=?)", outcome.status, reviewId, day, attemptId, outcome.status, finished),
  ]);
  if (!finalised[0].meta?.changes) return { status: "lease_lost" };
  return { ...outcome, attempt_id: attemptId };
}

export async function superviseDays(env, now = Date.now()) {
  if (env.REVIEW_V2_RUNNER_ENABLED !== "true") return { status: "disabled" };
  if (!env.REVIEW_DB || !env.REVIEW_JOBS || !env.REVIEW_EVIDENCE) throw new V2Error("daily_readiness_incomplete");
  const manifest = validateQueryManifest(JSON.parse(env.REVIEW_DAILY_QUERY_MANIFEST || "null"));
  const db = env.REVIEW_DB, review = await db.prepare("SELECT * FROM reviews WHERE phase='active'").first();
  if (!review) return { status: "not_activated" };
  const clock = romeClock(now), tomorrow = iso(Date.parse(`${clock.date}T12:00:00Z`) + 86400000).slice(0, 10);
  // Calendar creation and outbox creation share one transaction; a broker outage cannot erase a day.
  for (let day = review.start_date; day <= tomorrow; day = iso(Date.parse(`${day}T12:00:00Z`) + 86400000).slice(0, 10)) {
    await db.batch([
      statement(db, "INSERT OR IGNORE INTO search_days VALUES (?,?,?,?,?,'planned',?,?)", review.review_id, day, "Europe/Rome", manifest.protocol_version, canonicalJson(manifest), romeTime(day, 7, 20), iso(now)),
      statement(db, "INSERT OR IGNORE INTO outbox(outbox_id,review_id,kind,payload_json,created_at) VALUES (?,?,'search_day',?,?)", `daily-${review.review_id}-${day}`, review.review_id, canonicalJson({ review_id: review.review_id, scheduled_date: day }), iso(now)),
    ]);
  }
  await statement(db, "UPDATE search_days SET status='missing' WHERE review_id=? AND status='planned' AND deadline_at<?", review.review_id, iso(now)).run();
  const due = await results(db, "SELECT * FROM search_days WHERE review_id=? AND scheduled_date<=? AND status NOT IN ('completed','cancelled_authorized') ORDER BY scheduled_date", review.review_id, clock.date);
  for (const day of due) {
    if (Date.parse(romeTime(day.scheduled_date)) > now) continue;
    const { previous: attempt, terminal } = await recoverDay(db, review.review_id, day.scheduled_date, validateQueryManifest(JSON.parse(day.query_manifest_json)), now);
    if (terminal || (attempt?.status === "running" && Date.parse(attempt.lease_until) > now)
      || (attempt?.retry_after && Date.parse(attempt.retry_after) > now)) continue;
    await env.REVIEW_JOBS.send({ review_id: review.review_id, scheduled_date: day.scheduled_date });
    await statement(db, "UPDATE outbox SET delivered_at=?,attempts=attempts+1 WHERE outbox_id=?", iso(now), `daily-${review.review_id}-${day.scheduled_date}`).run();
  }
  return { status: "supervised", expected_days: due.length };
}

export async function consumeDays(batch, env) {
  for (const message of batch.messages) {
    try {
      if (env.REVIEW_V2_RUNNER_ENABLED !== "true") { message.retry({ delaySeconds: 900 }); continue; }
      await runDay(env, message.body.review_id, message.body.scheduled_date);
      message.ack();
    } catch { message.retry({ delaySeconds: 60 }); }
  }
}
