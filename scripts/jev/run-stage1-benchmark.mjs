#!/usr/bin/env node

import { createHash } from "node:crypto";
import { chmod, mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { evaluateJev } from "../../curator-app/src/jev-client.js";
import { buildJevShadowState } from "../../curator-app/src/jev-policy.js";
import { getJevQuestionSet } from "../../curator-app/src/jev-question-sets.js";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const BENCHMARK_PATH = resolve(ROOT, "config/jev-stage1-benchmark.json");
const JEV_CONFIG_PATH = resolve(ROOT, "config/jev-validation.json");
const QUEUE_PATH = resolve(ROOT, "data/curation/review_queue.csv");
const AIDS_PATH = resolve(ROOT, "data/curation/reading_aid_overrides.json");
const ACCESS_PATH = resolve(ROOT, "data/curation/access_coverage.csv");

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  }
  return value;
}

function canonical(value) {
  return JSON.stringify(stable(value));
}

function sha256(value) {
  return createHash("sha256").update(typeof value === "string" ? value : canonical(value)).digest("hex");
}

function parseCsv(source) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;

  for (let i = 0; i < source.length; i += 1) {
    const char = source[i];
    if (quoted) {
      if (char === '"' && source[i + 1] === '"') {
        field += '"';
        i += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
      continue;
    }
    if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n") {
      row.push(field.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }
  if (quoted) throw new Error("csv_unterminated_quote");
  if (field.length || row.length) {
    row.push(field.replace(/\r$/, ""));
    rows.push(row);
  }
  if (!rows.length) return [];
  const header = rows[0];
  if (!header.length || new Set(header).size !== header.length) throw new Error("csv_header_invalid");
  return rows.slice(1)
    .filter((values) => values.some((value) => value !== ""))
    .map((values, index) => {
      if (values.length !== header.length) throw new Error(`csv_row_width_invalid:${index + 2}`);
      return Object.fromEntries(header.map((key, column) => [key, values[column]]));
    });
}

function parseArgs(argv) {
  const args = { dryRun: false };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === "--dry-run") args.dryRun = true;
    else if (token === "--output") {
      const next = argv[index + 1];
      if (!next || next.startsWith("--")) throw new Error("missing_argument:--output");
      args.output = next;
      index += 1;
    } else if (token === "--help") args.help = true;
    else throw new Error(`unknown_argument:${token}`);
  }
  return args;
}

function usage() {
  return "node scripts/jev/run-stage1-benchmark.mjs [--dry-run] [--output <json>]";
}

function maybeYear(value) {
  if (!value) return undefined;
  const year = Number(value);
  return Number.isInteger(year) ? year : undefined;
}

function candidateState(queueRow, aid, accessRow) {
  const candidate = {
    candidate_id: queueRow.candidate_id,
    title: queueRow.title,
  };
  for (const [target, source] of [
    ["authors", "authors"],
    ["venue", "venue"],
    ["doi", "doi"],
    ["work_type", "work_type"],
    ["review_stage", "review_stage"],
  ]) {
    if (queueRow[source]) candidate[target] = queueRow[source];
  }
  const year = maybeYear(queueRow.year);
  if (year) candidate.year = year;

  const evidence = {
    source_basis: aid.sourceLabel,
    evidence_scope: aid.kind,
    research_synopsis: aid.synopsis,
    source_urls: [aid.sourceUrl],
  };
  if (accessRow?.access_status) evidence.access_status = accessRow.access_status;
  if (aid.note) evidence.metadata_notes = aid.note;

  return buildJevShadowState("candidate_screening", { candidate, evidence });
}

async function writePrivateJson(path, payload) {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, `${JSON.stringify(payload, null, 2)}\n`, { encoding: "utf-8", mode: 0o600 });
  await chmod(path, 0o600);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    process.stdout.write(`${usage()}\n`);
    return;
  }

  const [benchmark, jevConfig, queueCsv, aidsJson, accessCsv] = await Promise.all([
    readFile(BENCHMARK_PATH, "utf-8").then(JSON.parse),
    readFile(JEV_CONFIG_PATH, "utf-8").then(JSON.parse),
    readFile(QUEUE_PATH, "utf-8"),
    readFile(AIDS_PATH, "utf-8").then(JSON.parse),
    readFile(ACCESS_PATH, "utf-8"),
  ]);

  if (benchmark.contract !== "CILE-JEV-STAGE1-BENCHMARK-1") throw new Error("benchmark_contract_invalid");
  if (!Array.isArray(benchmark.candidates) || benchmark.candidates.length < 8 || benchmark.candidates.length > 30) {
    throw new Error("benchmark_cohort_size_invalid");
  }
  if (new Set(benchmark.candidates).size !== benchmark.candidates.length) throw new Error("benchmark_duplicate_candidate");

  const questionSet = getJevQuestionSet(benchmark.question_set);
  if (questionSet.stateKind !== "candidate_screening") throw new Error("benchmark_question_set_invalid");
  if (jevConfig.contract !== "CILE-JEV-SHADOW-1" || jevConfig.mode !== "shadow" || jevConfig.authoritative_writes !== false) {
    throw new Error("jev_shadow_config_not_fail_closed");
  }

  const queue = new Map(parseCsv(queueCsv).map((row) => [row.candidate_id, row]));
  const aids = new Map(aidsJson.records.map((record) => [record.candidateId, record]));
  const access = new Map(parseCsv(accessCsv).map((row) => [row.candidate_id, row]));

  const createdAt = new Date().toISOString();
  const results = [];
  let inputTokens = 0;
  let outputTokens = 0;

  for (const candidateId of benchmark.candidates) {
    const queueRow = queue.get(candidateId);
    const aid = aids.get(candidateId);
    if (!queueRow) throw new Error(`benchmark_candidate_missing:${candidateId}`);
    if (!aid?.synopsis || !aid?.sourceUrl || !aid?.sourceLabel || !aid?.kind) {
      throw new Error(`benchmark_reading_aid_incomplete:${candidateId}`);
    }

    const state = candidateState(queueRow, aid, access.get(candidateId));
    const base = {
      candidate_id: candidateId,
      title: queueRow.title,
      reading_aid_kind: aid.kind,
      source_label: aid.sourceLabel,
      state_sha256: sha256(state),
    };

    if (args.dryRun) {
      results.push({ ...base, status: "validated_no_external_call" });
      continue;
    }

    try {
      const response = await evaluateJev({
        state,
        questions: questionSet.questions,
        apiKey: process.env.TYPESAFE_API_KEY,
        model: jevConfig.model,
        endpoint: jevConfig.endpoint,
        timeoutMs: jevConfig.timeout_ms,
        maxAttempts: jevConfig.max_attempts,
      });
      inputTokens += response.usage.input_tokens;
      outputTokens += response.usage.output_tokens;
      results.push({
        ...base,
        status: "judged",
        model_returned: response.model,
        answers: response.answers,
        usage: response.usage,
      });
    } catch (error) {
      const errorCode = error?.code || error?.message || "jev_stage1_candidate_failure";
      results.push({
        ...base,
        status: "failed",
        error_code: errorCode,
      });
      if ([
        "api_key_missing",
        "provider_unauthorized",
        "provider_request_rejected",
        "configuration_invalid",
        "model_mismatch",
        "provider_response_invalid",
        "fetch_unavailable"
      ].includes(errorCode)) {
        break;
      }
    }
  }

  const failures = results.filter((result) => result.status === "failed");
  const report = {
    contract: benchmark.contract,
    shadow_contract: jevConfig.contract,
    mode: "shadow",
    authoritative: false,
    scientific_authority: "none",
    canonical_identity_authority: "none",
    publication_authority: "none",
    created_at: createdAt,
    git_sha: process.env.GITHUB_SHA || null,
    question_set_id: benchmark.question_set,
    question_set_version: questionSet.version,
    question_set_sha256: sha256(questionSet),
    model_requested: jevConfig.model,
    cohort_sha256: sha256(benchmark.candidates),
    cohort_size: benchmark.candidates.length,
    completed: results.length - failures.length,
    failed: failures.length,
    external_call: !args.dryRun,
    aggregate_usage: {
      input_tokens: inputTokens,
      output_tokens: outputTokens,
    },
    results,
  };

  const outputPath = resolve(process.cwd(), args.output || "outputs/jev-shadow/stage1-benchmark.json");
  await writePrivateJson(outputPath, report);
  process.stdout.write(`${JSON.stringify({
    status: failures.length ? "partial" : args.dryRun ? "validated" : "complete",
    cohort_size: report.cohort_size,
    completed: report.completed,
    failed: report.failed,
    input_tokens: inputTokens,
    output_tokens: outputTokens,
    output: outputPath,
  })}\n`);

  if (failures.length) process.exitCode = 1;
}

main().catch((error) => {
  process.stderr.write(`${JSON.stringify({ status: "failed", code: error?.code || error?.message || "jev_stage1_failure" })}\n`);
  process.exitCode = 1;
});
