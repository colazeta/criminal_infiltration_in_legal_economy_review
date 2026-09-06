"use strict";

import { cleanDoi } from "./scholarly-providers.js";

const OPENCITATIONS_INDEX_API = "https://api.opencitations.net/index/v2";
const SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1";
const MAX_FRONTIER_ROWS = 250;

function cleanText(value, maximum = 2000) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, maximum);
}

function doiFromIdentifier(value) {
  const text = cleanText(value, 1000);
  const prefixed = text.match(/(?:^|\s)doi:(10\.\d{4,9}\/\S+)/i);
  const plain = text.match(/\b(10\.\d{4,9}\/[^\s;,]+)\b/i);
  return cleanDoi((prefixed || plain)?.[1] || "").replace(/[.)\]}]+$/, "");
}

async function fetchJson(url, headers = {}) {
  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
      "User-Agent": "criminal-infiltration-curator/1.0",
      ...headers,
    },
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`upstream_${response.status}`);
  return response.json();
}

function openCitationsCandidate(row, direction) {
  const primary = direction === "backward"
    ? [row?.cited, row?.cited_doi, row?.id]
    : [row?.citing, row?.citing_doi, row?.id];
  const doi = doiFromIdentifier(primary.filter(Boolean).join(" "));
  if (!doi) return null;
  return {
    doi,
    title: cleanText(direction === "backward" ? row?.cited_title : row?.citing_title, 1000),
    year: Number(cleanText(direction === "backward" ? row?.cited_publication_date : row?.citing_publication_date, 20).slice(0, 4)) || null,
    authors: "",
    providers: ["OpenCitations"],
    sourceIds: [cleanText(row?.oci || row?.id, 500)].filter(Boolean),
  };
}

async function openCitationsDirection(doi, direction) {
  const endpoint = direction === "backward" ? "references" : "citations";
  const payload = await fetchJson(`${OPENCITATIONS_INDEX_API}/${endpoint}/doi:${encodeURIComponent(doi)}`);
  const rows = Array.isArray(payload) ? payload : [];
  return rows.map((row) => openCitationsCandidate(row, direction)).filter(Boolean).slice(0, MAX_FRONTIER_ROWS);
}

function semanticCandidate(entry, direction) {
  const paper = direction === "backward" ? entry?.citedPaper : entry?.citingPaper;
  if (!paper) return null;
  const doi = cleanDoi(paper?.externalIds?.DOI || "");
  const paperId = cleanText(paper?.paperId, 300);
  if (!doi && !paperId) return null;
  return {
    doi,
    title: cleanText(paper.title, 1000),
    year: Number(paper.year) || null,
    authors: Array.isArray(paper.authors) ? paper.authors.map((author) => author?.name).filter(Boolean).join("; ") : "",
    providers: ["Semantic Scholar"],
    sourceIds: paperId ? [`s2:${paperId}`] : [],
  };
}

async function semanticDirection(doi, direction, apiKey = "") {
  const relation = direction === "backward" ? "references" : "citations";
  const target = new URL(`${SEMANTIC_SCHOLAR_API}/paper/${encodeURIComponent(`DOI:${doi}`)}/${relation}`);
  target.searchParams.set("limit", "1000");
  target.searchParams.set("fields", "title,year,authors,externalIds");
  const headers = apiKey ? { "x-api-key": apiKey } : {};
  const payload = await fetchJson(target, headers);
  const rows = Array.isArray(payload?.data) ? payload.data : [];
  return rows.map((row) => semanticCandidate(row, direction)).filter(Boolean).slice(0, MAX_FRONTIER_ROWS);
}

function candidateKey(candidate) {
  if (candidate?.doi) return `doi:${candidate.doi.toLowerCase()}`;
  const sourceId = candidate?.sourceIds?.[0] || "";
  return sourceId || "";
}

function mergeCandidates(groups) {
  const merged = new Map();
  for (const group of groups) {
    for (const candidate of group || []) {
      const key = candidateKey(candidate);
      if (!key) continue;
      if (!merged.has(key)) {
        merged.set(key, {
          doi: candidate.doi || "",
          title: candidate.title || "",
          year: candidate.year || null,
          authors: candidate.authors || "",
          providers: [],
          sourceIds: [],
        });
      }
      const row = merged.get(key);
      if (!row.title && candidate.title) row.title = candidate.title;
      if (!row.year && candidate.year) row.year = candidate.year;
      if (!row.authors && candidate.authors) row.authors = candidate.authors;
      for (const provider of candidate.providers || []) if (!row.providers.includes(provider)) row.providers.push(provider);
      for (const sourceId of candidate.sourceIds || []) if (sourceId && !row.sourceIds.includes(sourceId)) row.sourceIds.push(sourceId);
    }
  }
  return [...merged.values()]
    .sort((left, right) => right.providers.length - left.providers.length || Number(right.year || 0) - Number(left.year || 0))
    .slice(0, MAX_FRONTIER_ROWS);
}

function agreementSummary(rows) {
  const both = rows.filter((row) => row.providers.length >= 2).length;
  const single = rows.length - both;
  return { total: rows.length, providerAgreement: both, providerUnique: single };
}

async function citationFrontier({ doi, semanticScholarApiKey = "" } = {}) {
  const clean = cleanDoi(doi);
  if (!clean) {
    return {
      schemaVersion: 1,
      doi: "",
      backward: [],
      forward: [],
      providersTried: [],
      providerErrors: [],
      status: "doi_required",
    };
  }

  const calls = [
    { key: "oc_backward", provider: "OpenCitations", direction: "backward", promise: openCitationsDirection(clean, "backward") },
    { key: "oc_forward", provider: "OpenCitations", direction: "forward", promise: openCitationsDirection(clean, "forward") },
    { key: "s2_backward", provider: "Semantic Scholar", direction: "backward", promise: semanticDirection(clean, "backward", semanticScholarApiKey) },
    { key: "s2_forward", provider: "Semantic Scholar", direction: "forward", promise: semanticDirection(clean, "forward", semanticScholarApiKey) },
  ];
  const settled = await Promise.allSettled(calls.map((entry) => entry.promise));
  const byDirection = { backward: [], forward: [] };
  const providerErrors = [];
  settled.forEach((entry, index) => {
    const call = calls[index];
    if (entry.status === "fulfilled") byDirection[call.direction].push(entry.value || []);
    else providerErrors.push(`${call.provider}/${call.direction}:${entry.reason?.message || "error"}`);
  });
  const backward = mergeCandidates(byDirection.backward);
  const forward = mergeCandidates(byDirection.forward);
  return {
    schemaVersion: 1,
    doi: clean,
    backward,
    forward,
    summary: {
      backward: agreementSummary(backward),
      forward: agreementSummary(forward),
    },
    providersTried: ["OpenCitations", "Semantic Scholar"],
    providerErrors,
    status: providerErrors.length === calls.length ? "failed" : providerErrors.length ? "partial" : "completed",
    methodologicalNote: "E2/E3 candidate frontier only. Provider union is not treated as a complete citation graph and no candidate is screened or added automatically.",
  };
}

export {
  citationFrontier,
  openCitationsDirection,
  semanticDirection,
};
