#!/usr/bin/env node

"use strict";

import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";

import { citationFrontier } from "../../curator-app/src/citation-chasing.js";
import { cleanDoi } from "../../curator-app/src/enrichment.js";

function parseArgs(argv) {
  const args = { dois: [], doiFile: "", output: "" };
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === "--doi") args.dois.push(argv[++index] || "");
    else if (value === "--doi-file") args.doiFile = argv[++index] || "";
    else if (value === "--output") args.output = argv[++index] || "";
    else if (value === "--help" || value === "-h") args.help = true;
    else throw new Error(`unknown_argument:${value}`);
  }
  return args;
}

function usage() {
  return [
    "Usage:",
    "  node scripts/expansion/citation_frontier.mjs --doi 10.x/seed [--doi 10.y/seed] [--output frontier.json]",
    "  node scripts/expansion/citation_frontier.mjs --doi-file frontier-dois.txt [--output frontier.json]",
    "",
    "The command performs DOI-bound E2 backward and E3 forward citation chasing using OpenCitations and Semantic Scholar.",
    "It never mutates the queue, registry, screening state or publication state.",
  ].join("\n");
}

async function readDoiFile(filePath) {
  if (!filePath) return [];
  const content = await fs.readFile(filePath, "utf8");
  return content.split(/\r?\n/).map((line) => line.trim()).filter((line) => line && !line.startsWith("#"));
}

function uniqueDois(values) {
  const seen = new Set();
  const rows = [];
  for (const value of values) {
    const doi = cleanDoi(value).toLowerCase();
    if (!doi || seen.has(doi)) continue;
    seen.add(doi);
    rows.push(doi);
  }
  return rows;
}

function mergeFrontier(rows, direction) {
  const merged = new Map();
  for (const seed of rows) {
    for (const candidate of seed?.[direction] || []) {
      const key = candidate.doi ? `doi:${candidate.doi.toLowerCase()}` : candidate.sourceIds?.[0] || "";
      if (!key) continue;
      if (!merged.has(key)) {
        merged.set(key, {
          doi: candidate.doi || "",
          title: candidate.title || "",
          year: candidate.year || null,
          authors: candidate.authors || "",
          foundFromSeeds: [],
          providers: [],
          sourceIds: [],
        });
      }
      const target = merged.get(key);
      if (!target.foundFromSeeds.includes(seed.doi)) target.foundFromSeeds.push(seed.doi);
      for (const provider of candidate.providers || []) if (!target.providers.includes(provider)) target.providers.push(provider);
      for (const sourceId of candidate.sourceIds || []) if (sourceId && !target.sourceIds.includes(sourceId)) target.sourceIds.push(sourceId);
    }
  }
  return [...merged.values()].sort((left, right) => right.providers.length - left.providers.length || right.foundFromSeeds.length - left.foundFromSeeds.length);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    process.stdout.write(`${usage()}\n`);
    return;
  }
  const fileDois = await readDoiFile(args.doiFile);
  const dois = uniqueDois([...args.dois, ...fileDois]);
  if (!dois.length) throw new Error("at_least_one_doi_required");

  const seeds = [];
  for (const doi of dois) {
    seeds.push(await citationFrontier({
      doi,
      semanticScholarApiKey: String(process.env.SEMANTIC_SCHOLAR_API_KEY || "").trim(),
    }));
  }
  const payload = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    execution: "formal_citation_frontier",
    seedDois: dois,
    providers: ["OpenCitations", "Semantic Scholar"],
    seeds,
    uniqueBackward: mergeFrontier(seeds, "backward"),
    uniqueForward: mergeFrontier(seeds, "forward"),
    unresolvedSeeds: seeds.filter((seed) => seed.status === "failed").map((seed) => seed.doi),
    note: "Mechanical E2/E3 retrieval only. Screening, deduplication and frontier promotion remain separate governed human-review steps.",
  };
  const output = `${JSON.stringify(payload, null, 2)}\n`;
  if (args.output) {
    await fs.mkdir(path.dirname(path.resolve(args.output)), { recursive: true });
    await fs.writeFile(args.output, output, "utf8");
  } else {
    process.stdout.write(output);
  }
}

main().catch((error) => {
  process.stderr.write(`${error?.message || error}\n`);
  process.exitCode = 1;
});
