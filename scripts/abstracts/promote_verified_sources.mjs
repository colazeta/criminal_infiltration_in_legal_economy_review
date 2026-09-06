#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "../..");
const COVERAGE_PATH = path.join(ROOT, "data/curation/abstract_coverage.csv");
const READING_AIDS_PATH = path.join(ROOT, "data/curation/reading_aids.json");
const READING_AID_OVERRIDES_PATH = path.join(ROOT, "data/curation/reading_aid_overrides.json");

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
      } else if (char === '"') quoted = false;
      else field += char;
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
    "candidate_id", "title", "doi", "coverage_status", "abstract_source",
    "article_url", "providers_tried", "match_type", "match_score",
    "provider_errors", "checked_at", "notes",
  ];
  return `${[fields.join(","), ...rows.map((row) => fields.map((field) => csvCell(row[field] || "")).join(","))].join("\n")}\n`;
}

function readJson(filePath) {
  if (!fs.existsSync(filePath)) return { records: [] };
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function verifiedAbstractSourceMap() {
  const base = readJson(READING_AIDS_PATH).records || [];
  const overrides = readJson(READING_AID_OVERRIDES_PATH).records || [];
  const merged = new Map(base.map((record) => [record.candidateId, record]));
  for (const record of overrides) merged.set(record.candidateId, record);
  return new Map(
    [...merged.entries()].filter(([, record]) => record.kind === "verified_abstract_source"),
  );
}

function appendProvider(existing, provider) {
  const values = String(existing || "").split(";").map((value) => value.trim()).filter(Boolean);
  if (!values.includes(provider)) values.push(provider);
  return values.join("; ");
}

function promote(rows, sources) {
  let changed = 0;
  const output = rows.map((row) => {
    if (row.coverage_status !== "needs_web_search") return row;
    const source = sources.get(row.candidate_id);
    if (!source) return row;
    changed += 1;
    return {
      ...row,
      coverage_status: "available",
      abstract_source: source.sourceLabel || "Verified abstract source",
      article_url: source.sourceUrl || row.article_url,
      providers_tried: appendProvider(row.providers_tried, "curator verified abstract source"),
      match_type: "verified_abstract_source",
      match_score: "1",
      checked_at: source.checkedAt || row.checked_at,
      notes: "Verified abstract source located by assisted curator retrieval; abstract text does not persist in the corpus.",
    };
  });
  return { output, changed };
}

function main() {
  const rows = parseCsv(fs.readFileSync(COVERAGE_PATH, "utf8").replace(/^\uFEFF/, ""));
  const sources = verifiedAbstractSourceMap();
  const { output, changed } = promote(rows, sources);
  if (changed) fs.writeFileSync(COVERAGE_PATH, writeCsv(output));
  console.log(`Verified abstract source bridge: ${changed} coverage row(s) promoted; ${sources.size} verified source(s) registered.`);
}

main();
