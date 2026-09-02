#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { enrichCandidate } from "../../curator-app/src/enrichment.js";
import { resolveAbstractFromRetrieval } from "../../curator-app/src/resolved-abstract.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const QUEUE_PATH = path.join(ROOT, "data/curation/review_queue.csv");
const RETRIEVAL_PATH = path.join(ROOT, "data/curation/retrieval_coverage.csv");
const COVERAGE_PATH = path.join(ROOT, "data/curation/abstract_coverage.csv");
const VALID_STATUSES = new Set(["available", "needs_web_search"]);
const CONCURRENCY = 2;

function parseCsv(source) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let index = 0; index < source.length; index += 1) {
    const char = source[index];
    if (quoted) {
      if (char === '"' && source[index + 1] === '"') {
        field += '"';
        index += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
      continue;
    }
    if (char === '"') quoted = true;
    else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n") {
      row.push(field.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      field = "";
    } else field += char;
  }
  if (field || row.length) {
    row.push(field.replace(/\r$/, ""));
    rows.push(row);
  }
  if (!rows.length) return [];
  const header = rows[0];
  return rows.slice(1)
    .filter((values) => values.some((value) => value !== ""))
    .map((values) => Object.fromEntries(header.map((key, index) => [key, values[index] ?? ""])));
}

function csvCell(value) {
  const text = String(value ?? "");
  if (!/[",\r\n]/.test(text)) return text;
  return `"${text.replace(/"/g, '""')}"`;
}

function writeCsv(rows) {
  const fields = [
    "candidate_id",
    "title",
    "doi",
    "coverage_status",
    "abstract_source",
    "article_url",
    "providers_tried",
    "match_type",
    "match_score",
    "provider_errors",
    "checked_at",
    "notes",
  ];
  const lines = [fields.join(",")];
  for (const row of rows) lines.push(fields.map((field) => csvCell(row[field] || "")).join(","));
  return `${lines.join("\n")}\n`;
}

function readRows(filePath) {
  return parseCsv(fs.readFileSync(filePath, "utf8").replace(/^\uFEFF/, ""));
}

function retrievalMap() {
  if (!fs.existsSync(RETRIEVAL_PATH)) return new Map();
  return new Map(readRows(RETRIEVAL_PATH).map((row) => [row.candidate_id, {
    bestUrl: row.best_url || "",
    fullTextUrl: row.full_text_url || "",
    openAccessUrl: row.open_access_url || "",
    landingUrl: row.landing_url || "",
    doiUrl: row.doi_url || "",
  }]));
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

function dateStamp() {
  const supplied = String(process.env.ABSTRACT_COVERAGE_DATE || "").trim();
  if (supplied) return supplied;
  return new Date().toISOString().slice(0, 10);
}

async function inspectCandidate(candidate, retrieval, checkedAt) {
  let primary;
  try {
    primary = await enrichCandidate({
      title: candidate.title,
      doi: candidate.doi,
      year: candidate.year,
      semanticScholarApiKey: String(process.env.SEMANTIC_SCHOLAR_API_KEY || "").trim(),
      coreApiKey: String(process.env.CORE_API_KEY || "").trim(),
      unpaywallEmail: String(process.env.UNPAYWALL_EMAIL || "").trim(),
    });
  } catch (error) {
    primary = {
      abstract: "",
      abstractSource: "",
      articleUrl: candidate.doi ? `https://doi.org/${candidate.doi}` : "",
      providersTried: [],
      providerErrors: [`structured:${error?.message || "error"}`],
      matchType: "unavailable",
      matchScore: 0,
    };
  }

  let final = primary;
  const providers = [...(primary.providersTried || [])];
  const errors = [...(primary.providerErrors || [])];
  if (!String(primary.abstract || "").trim() && retrieval) {
    providers.push("paper/repository resolved");
    try {
      const resolved = await resolveAbstractFromRetrieval({ title: candidate.title, retrieval });
      if (String(resolved.abstract || "").trim()) final = resolved;
      else if (resolved.articleUrl && !final.articleUrl) final = { ...final, articleUrl: resolved.articleUrl };
    } catch (error) {
      errors.push(`resolved_document:${error?.message || "error"}`);
    }
  }

  const available = Boolean(String(final.abstract || "").trim());
  const notes = available
    ? "Abstract text detected by the zero-cost cascade; text is intentionally not persisted."
    : "No abstract text detected by the bulk zero-cost cascade; retain for per-paper free web/assisted search.";
  return {
    candidate_id: candidate.candidate_id,
    title: candidate.title,
    doi: candidate.doi || "",
    coverage_status: available ? "available" : "needs_web_search",
    abstract_source: available ? (final.abstractSource || final.provider || "verified source") : "",
    article_url: final.articleUrl || primary.articleUrl || retrieval?.bestUrl || "",
    providers_tried: unique(providers).join("; "),
    match_type: available ? (final.matchType || "verified") : "needs_web_search",
    match_score: Number.isFinite(Number(final.matchScore)) ? String(final.matchScore) : "",
    provider_errors: unique(errors).join("; "),
    checked_at: checkedAt,
    notes,
  };
}

async function runPool(candidates, retrievals, checkedAt) {
  const output = new Array(candidates.length);
  let cursor = 0;
  async function worker() {
    while (true) {
      const index = cursor;
      cursor += 1;
      if (index >= candidates.length) return;
      const candidate = candidates[index];
      output[index] = await inspectCandidate(candidate, retrievals.get(candidate.candidate_id), checkedAt);
      if ((index + 1) % 10 === 0 || index + 1 === candidates.length) {
        console.log(`Abstract coverage: ${index + 1}/${candidates.length}`);
      }
      await new Promise((resolve) => setTimeout(resolve, 200));
    }
  }
  await Promise.all(Array.from({ length: Math.min(CONCURRENCY, candidates.length) }, () => worker()));
  return output;
}

function validateCoverage(queue, coverage) {
  if (queue.length !== coverage.length) throw new Error(`coverage_count_mismatch:${coverage.length}:${queue.length}`);
  for (let index = 0; index < queue.length; index += 1) {
    const expected = queue[index].candidate_id;
    const row = coverage[index];
    if (row.candidate_id !== expected) throw new Error(`coverage_order_mismatch:${index}:${row.candidate_id}:${expected}`);
    if (!VALID_STATUSES.has(row.coverage_status)) throw new Error(`invalid_coverage_status:${row.candidate_id}:${row.coverage_status}`);
    if (!row.checked_at) throw new Error(`missing_checked_at:${row.candidate_id}`);
    if (row.coverage_status === "available" && !row.abstract_source) throw new Error(`missing_abstract_source:${row.candidate_id}`);
    if (Object.prototype.hasOwnProperty.call(row, "abstract") || Object.prototype.hasOwnProperty.call(row, "abstract_text")) {
      throw new Error("abstract_text_must_not_be_persisted");
    }
  }
  const counts = coverage.reduce((result, row) => {
    result[row.coverage_status] = (result[row.coverage_status] || 0) + 1;
    return result;
  }, {});
  return { total: coverage.length, ...counts };
}

async function main() {
  const queue = readRows(QUEUE_PATH);
  if (process.argv.includes("--check")) {
    if (!fs.existsSync(COVERAGE_PATH)) throw new Error("abstract_coverage_missing");
    console.log(JSON.stringify(validateCoverage(queue, readRows(COVERAGE_PATH))));
    return;
  }
  const coverage = await runPool(queue, retrievalMap(), dateStamp());
  const summary = validateCoverage(queue, coverage);
  fs.writeFileSync(COVERAGE_PATH, writeCsv(coverage), "utf8");
  const outputArg = process.argv.indexOf("--summary");
  if (outputArg >= 0 && process.argv[outputArg + 1]) {
    fs.writeFileSync(process.argv[outputArg + 1], `${JSON.stringify(summary, null, 2)}\n`, "utf8");
  }
  console.log(JSON.stringify(summary));
}

main().catch((error) => {
  console.error(error?.stack || error);
  process.exitCode = 1;
});
