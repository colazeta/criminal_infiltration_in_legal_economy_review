#!/usr/bin/env node

import { createHash } from "node:crypto";
import { chmod, mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { evaluateJev } from "../../curator-app/src/jev-client.js";
import { buildJevShadowState } from "../../curator-app/src/jev-policy.js";
import { getJevQuestionSet } from "../../curator-app/src/jev-question-sets.js";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const CONFIG_PATH = resolve(ROOT, "config/jev-validation.json");
const KIND_TO_QUESTION_SET = Object.freeze({
  candidate_screening: "candidate_screening_v1",
  metadata_assertion: "metadata_assertion_v1",
  identity_relation: "identity_relation_v1",
  enrichment_qa: "enrichment_qa_v1",
});

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

function parseArgs(argv) {
  const args = { dryRun: false };
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === "--dry-run") args.dryRun = true;
    else if (["--input", "--output", "--question-set"].includes(token)) {
      const next = argv[index + 1];
      if (!next || next.startsWith("--")) throw new Error(`missing_argument:${token}`);
      args[token.slice(2).replace("question-set", "questionSet")] = next;
      index += 1;
    } else if (token === "--help") args.help = true;
    else throw new Error(`unknown_argument:${token}`);
  }
  return args;
}

function usage() {
  return [
    "Usage:",
    "  node scripts/jev/run-shadow.mjs --input <json> [--question-set <id>] [--output <json>] [--dry-run]",
    "",
    "The input JSON must contain `kind` plus only the bounded fields accepted by curator-app/src/jev-policy.js.",
    "Dry-run validates and hashes the request without contacting TypeSafe.",
  ].join("\n");
}

function subjectId(state) {
  if (state?.candidate?.candidate_id) return state.candidate.candidate_id;
  if (state?.candidate_id) return state.candidate_id;
  if (state?.left?.candidate_id && state?.right?.candidate_id) return `${state.left.candidate_id}--${state.right.candidate_id}`;
  return "jev-shadow";
}

function safeName(value) {
  return String(value).replace(/[^A-Za-z0-9._-]+/g, "_").slice(0, 180) || "jev-shadow";
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
  if (!args.input) throw new Error("input_required");

  const config = JSON.parse(await readFile(CONFIG_PATH, "utf-8"));
  if (config.contract !== "CILE-JEV-SHADOW-1" || config.mode !== "shadow" || config.authoritative_writes !== false || config.scientific_authority !== "none" || config.canonical_identity_authority !== "none" || config.publication_authority !== "none") {
    throw new Error("jev_shadow_config_not_fail_closed");
  }
  if (config.allow_private_full_text || config.allow_verbatim_abstract || config.allow_private_source_body || config.persist_raw_state) {
    throw new Error("jev_shadow_data_boundary_not_fail_closed");
  }

  const inputPath = resolve(process.cwd(), args.input);
  const input = JSON.parse(await readFile(inputPath, "utf-8"));
  const kind = input.kind;
  const questionSetId = args.questionSet || input.question_set || KIND_TO_QUESTION_SET[kind];
  if (!questionSetId) throw new Error(`question_set_required:${kind || "missing_kind"}`);
  const questionSet = getJevQuestionSet(questionSetId);
  if (questionSet.stateKind !== kind) throw new Error(`question_set_kind_mismatch:${questionSetId}:${kind}`);

  const { kind: _kind, question_set: _questionSet, ...boundedInput } = input;
  const state = buildJevShadowState(kind, boundedInput);
  const subject = subjectId(state);
  const createdAt = new Date().toISOString();
  const base = {
    contract: config.contract,
    mode: "shadow",
    authoritative: false,
    scientific_authority: "none",
    canonical_identity_authority: "none",
    publication_authority: "none",
    subject_id: subject,
    question_set_id: questionSetId,
    question_set_version: questionSet.version,
    question_set_sha256: sha256(questionSet),
    state_sha256: sha256(state),
    model_requested: config.model,
    created_at: createdAt,
  };

  let receipt;
  if (args.dryRun) {
    receipt = { ...base, status: "shadow_request_validated", external_call: false, question_ids: Object.keys(questionSet.questions).sort() };
  } else {
    const result = await evaluateJev({
      state,
      questions: questionSet.questions,
      apiKey: process.env.TYPESAFE_API_KEY,
      model: config.model,
      endpoint: config.endpoint,
      timeoutMs: config.timeout_ms,
      maxAttempts: config.max_attempts,
    });
    receipt = {
      ...base,
      status: "shadow_judgment_recorded",
      external_call: true,
      model_returned: result.model,
      answers: result.answers,
      usage: result.usage,
    };
  }

  const stamp = createdAt.replace(/[:.]/g, "-");
  const outputPath = args.output
    ? resolve(process.cwd(), args.output)
    : resolve(ROOT, "outputs/jev-shadow", `${stamp}_${safeName(subject)}_${safeName(questionSetId)}.json`);
  await writePrivateJson(outputPath, receipt);
  process.stdout.write(`${JSON.stringify({ status: receipt.status, subject_id: subject, question_set_id: questionSetId, output: outputPath })}\n`);
}

main().catch((error) => {
  process.stderr.write(`${JSON.stringify({ status: "failed", code: error?.code || error?.message || "jev_shadow_failure" })}\n`);
  process.exitCode = 1;
});
