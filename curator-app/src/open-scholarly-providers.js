"use strict";

import { cleanDoi, titleSimilarity } from "./scholarly-providers.js";

const ARXIV_API = "https://export.arxiv.org/api/query";
const ZENODO_API = "https://zenodo.org/api/records";
const HAL_API = "https://api.archives-ouvertes.fr/search/";
const DOAJ_API = "https://doaj.org/api/search/articles";
const OPENCITATIONS_META_API = "https://api.opencitations.net/meta/v1";
const MAX_ABSTRACT_LENGTH = 12000;

const OPEN_METADATA_PROVIDER_REGISTRY = Object.freeze([
  { id: "opencitations_meta", label: "OpenCitations Meta", stage: "identity", billing: "none", credential: "none" },
  { id: "arxiv", label: "arXiv", stage: "repository", billing: "none", credential: "none" },
  { id: "zenodo", label: "Zenodo", stage: "repository", billing: "none", credential: "none" },
  { id: "hal", label: "HAL", stage: "repository", billing: "none", credential: "none" },
  { id: "doaj", label: "DOAJ", stage: "oa_metadata", billing: "none", credential: "none" },
]);

function cleanText(value, maximum = 1000) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, maximum);
}

function decodeEntities(value) {
  return String(value || "")
    .replace(/&amp;/gi, "&")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">");
}

function stripMarkup(value, maximum = MAX_ABSTRACT_LENGTH) {
  return cleanText(
    decodeEntities(String(value || ""))
      .replace(/<script\b[\s\S]*?<\/script>/gi, " ")
      .replace(/<style\b[\s\S]*?<\/style>/gi, " ")
      .replace(/<[^>]+>/g, " "),
    maximum,
  );
}

function safeHttpsUrl(value) {
  try {
    const url = new URL(String(value || ""));
    return url.protocol === "https:" ? url.toString() : "";
  } catch {
    return "";
  }
}

function requestedWork({ title, doi, year }) {
  return {
    title: cleanText(title, 1000),
    doi: cleanDoi(doi),
    year: cleanText(year, 10),
  };
}

function yearCompatible(requested, candidate) {
  const left = Number(requested) || null;
  const right = Number(candidate) || null;
  return !left || !right || Math.abs(left - right) <= 1;
}

function observation({
  provider,
  title,
  year,
  doi,
  authors = "",
  venue = "",
  abstract = "",
  articleUrl = "",
  sourceId = "",
  relations = [],
  requested,
  matchType,
}) {
  const matchedTitle = cleanText(title, 1000);
  const matchedDoi = cleanDoi(doi);
  const similarity = titleSimilarity(requested.title, matchedTitle);
  if (matchType !== "doi" && (similarity < 0.84 || !yearCompatible(requested.year, year))) return null;
  if (matchType === "doi" && requested.doi && matchedDoi && requested.doi.toLowerCase() !== matchedDoi.toLowerCase()) return null;
  return {
    abstract: stripMarkup(abstract),
    abstractSource: stripMarkup(abstract) ? provider : "",
    provider,
    articleUrl: safeHttpsUrl(articleUrl) || (matchedDoi ? `https://doi.org/${matchedDoi}` : ""),
    matchedTitle,
    matchedYear: Number(year) || null,
    matchedDoi,
    authors: cleanText(authors, 3000),
    venue: cleanText(venue, 1000),
    sourceId: cleanText(sourceId, 500),
    relations: Array.isArray(relations) ? relations.map((value) => cleanText(value, 500)).filter(Boolean).slice(0, 30) : [],
    matchType,
    matchScore: matchType === "doi" ? 1 : Number(similarity.toFixed(3)),
  };
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

async function fetchText(url, headers = {}) {
  const response = await fetch(url, {
    headers: {
      Accept: "application/atom+xml, application/xml, text/xml;q=0.9, text/plain;q=0.5",
      "User-Agent": "criminal-infiltration-curator/1.0",
      ...headers,
    },
  });
  if (response.status === 404) return "";
  if (!response.ok) throw new Error(`upstream_${response.status}`);
  return response.text();
}

function xmlTag(source, name) {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = String(source || "").match(new RegExp(`<${escaped}(?:\\s[^>]*)?>([\\s\\S]*?)<\\/${escaped}>`, "i"));
  return match ? stripMarkup(match[1], MAX_ABSTRACT_LENGTH) : "";
}

function xmlTags(source, name) {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return Array.from(String(source || "").matchAll(new RegExp(`<${escaped}(?:\\s[^>]*)?>([\\s\\S]*?)<\\/${escaped}>`, "gi")))
    .map((match) => stripMarkup(match[1], 2000))
    .filter(Boolean);
}

function arxivEntries(feed) {
  return Array.from(String(feed || "").matchAll(/<entry>([\s\S]*?)<\/entry>/gi)).map((match) => match[1]);
}

function arxivEntry(entry, requested) {
  const title = xmlTag(entry, "title");
  const summary = xmlTag(entry, "summary");
  const published = xmlTag(entry, "published");
  const year = published ? Number(published.slice(0, 4)) : null;
  const doi = xmlTag(entry, "arxiv:doi");
  const id = xmlTag(entry, "id");
  const journalRef = xmlTag(entry, "arxiv:journal_ref");
  const authors = Array.from(entry.matchAll(/<author>([\s\S]*?)<\/author>/gi))
    .map((match) => xmlTag(match[1], "name"))
    .filter(Boolean)
    .join("; ");
  const relations = [];
  if (id) relations.push(`arxiv:${id.split("/").pop()}`);
  if (doi) relations.push(`doi:${cleanDoi(doi)}`);
  return observation({
    provider: "arXiv",
    title,
    year,
    doi,
    authors,
    venue: journalRef,
    abstract: summary,
    articleUrl: id.replace(/^http:/i, "https:"),
    sourceId: id ? `arxiv:${id.split("/").pop()}` : "",
    relations,
    requested,
    matchType: requested.doi && cleanDoi(doi).toLowerCase() === requested.doi.toLowerCase() ? "doi" : "title_year",
  });
}

async function arxiv(requestedInput) {
  const requested = requestedWork(requestedInput);
  const target = new URL(ARXIV_API);
  const query = requested.doi
    ? `doi:\"${requested.doi}\" OR ti:\"${requested.title.replace(/\"/g, "")}\"`
    : `ti:\"${requested.title.replace(/\"/g, "")}\"`;
  target.searchParams.set("search_query", query);
  target.searchParams.set("start", "0");
  target.searchParams.set("max_results", "5");
  const feed = await fetchText(target);
  return arxivEntries(feed)
    .map((entry) => arxivEntry(entry, requested))
    .filter(Boolean)
    .sort((a, b) => b.matchScore - a.matchScore)[0] || null;
}

function zenodoRelations(metadata) {
  const related = Array.isArray(metadata?.related_identifiers) ? metadata.related_identifiers : [];
  return related.map((entry) => {
    const identifier = cleanText(entry?.identifier, 400);
    const relation = cleanText(entry?.relation, 80);
    return identifier ? `${relation || "related"}:${identifier}` : "";
  }).filter(Boolean);
}

function zenodoObservation(record, requested) {
  const metadata = record?.metadata || {};
  const creators = Array.isArray(metadata.creators) ? metadata.creators : [];
  const files = Array.isArray(record?.files) ? record.files : [];
  const fileUrl = files.map((file) => file?.links?.self || file?.links?.download).find((value) => safeHttpsUrl(value)) || "";
  const doi = metadata.doi || record?.doi || "";
  return observation({
    provider: "Zenodo",
    title: metadata.title,
    year: cleanText(metadata.publication_date, 20).slice(0, 4),
    doi,
    authors: creators.map((creator) => creator?.name).filter(Boolean).join("; "),
    venue: metadata?.journal?.title || metadata.publisher || "",
    abstract: metadata.description,
    articleUrl: fileUrl || record?.links?.html || record?.links?.self,
    sourceId: record?.id ? `zenodo:${record.id}` : "",
    relations: zenodoRelations(metadata),
    requested,
    matchType: requested.doi && cleanDoi(doi).toLowerCase() === requested.doi.toLowerCase() ? "doi" : "title_year",
  });
}

async function zenodo(requestedInput) {
  const requested = requestedWork(requestedInput);
  const target = new URL(ZENODO_API);
  target.searchParams.set("q", requested.doi ? `doi:\"${requested.doi}\"` : `title:\"${requested.title.replace(/\"/g, "")}\"`);
  target.searchParams.set("size", "5");
  const payload = await fetchJson(target);
  const candidates = Array.isArray(payload?.hits?.hits) ? payload.hits.hits : [];
  return candidates
    .map((record) => zenodoObservation(record, requested))
    .filter(Boolean)
    .sort((a, b) => b.matchScore - a.matchScore)[0] || null;
}

function halObservation(record, requested) {
  const title = Array.isArray(record?.title_s) ? record.title_s[0] : record?.title_s || record?.title_t;
  const abstract = Array.isArray(record?.abstract_s) ? record.abstract_s[0] : record?.abstract_s;
  const doi = Array.isArray(record?.doiId_s) ? record.doiId_s[0] : record?.doiId_s;
  const authors = Array.isArray(record?.authFullName_s) ? record.authFullName_s.join("; ") : record?.authFullName_s || "";
  const venue = Array.isArray(record?.journalTitle_s) ? record.journalTitle_s[0] : record?.journalTitle_s || "";
  return observation({
    provider: "HAL",
    title,
    year: record?.producedDateY_i || record?.publicationDateY_i,
    doi,
    authors,
    venue,
    abstract,
    articleUrl: record?.fileMain_s || record?.uri_s,
    sourceId: record?.halId_s ? `hal:${record.halId_s}` : "",
    relations: [record?.halId_s ? `hal:${record.halId_s}` : ""].filter(Boolean),
    requested,
    matchType: requested.doi && cleanDoi(doi).toLowerCase() === requested.doi.toLowerCase() ? "doi" : "title_year",
  });
}

async function hal(requestedInput) {
  const requested = requestedWork(requestedInput);
  const target = new URL(HAL_API);
  target.searchParams.set("q", requested.doi ? `doiId_s:\"${requested.doi}\"` : `title_t:\"${requested.title.replace(/\"/g, "")}\"`);
  target.searchParams.set("fl", "halId_s,title_s,authFullName_s,producedDateY_i,publicationDateY_i,doiId_s,abstract_s,journalTitle_s,uri_s,fileMain_s");
  target.searchParams.set("rows", "5");
  target.searchParams.set("wt", "json");
  const payload = await fetchJson(target);
  const candidates = Array.isArray(payload?.response?.docs) ? payload.response.docs : [];
  return candidates
    .map((record) => halObservation(record, requested))
    .filter(Boolean)
    .sort((a, b) => b.matchScore - a.matchScore)[0] || null;
}

function doajIdentifier(bibjson, type) {
  const identifiers = Array.isArray(bibjson?.identifier) ? bibjson.identifier : [];
  return identifiers.find((entry) => String(entry?.type || "").toLowerCase() === type)?.id || "";
}

function doajObservation(record, requested) {
  const bibjson = record?.bibjson || record?._source?.bibjson || {};
  const doi = doajIdentifier(bibjson, "doi");
  const links = Array.isArray(bibjson?.link) ? bibjson.link : [];
  const articleUrl = links.find((entry) => entry?.type === "fulltext")?.url || links[0]?.url || "";
  const authors = Array.isArray(bibjson?.author) ? bibjson.author.map((author) => author?.name).filter(Boolean).join("; ") : "";
  return observation({
    provider: "DOAJ",
    title: bibjson.title,
    year: bibjson.year,
    doi,
    authors,
    venue: bibjson?.journal?.title || "",
    abstract: bibjson.abstract,
    articleUrl,
    sourceId: record?.id ? `doaj:${record.id}` : "",
    relations: [doajIdentifier(bibjson, "eissn"), doajIdentifier(bibjson, "pissn")].filter(Boolean).map((value) => `issn:${value}`),
    requested,
    matchType: requested.doi && cleanDoi(doi).toLowerCase() === requested.doi.toLowerCase() ? "doi" : "title_year",
  });
}

async function doaj(requestedInput) {
  const requested = requestedWork(requestedInput);
  const query = requested.doi ? `doi:${requested.doi}` : `title:\"${requested.title.replace(/\"/g, "")}\"`;
  const target = new URL(`${DOAJ_API}/${encodeURIComponent(query)}`);
  target.searchParams.set("pageSize", "5");
  const payload = await fetchJson(target);
  const candidates = Array.isArray(payload?.results) ? payload.results : [];
  return candidates
    .map((record) => doajObservation(record, requested))
    .filter(Boolean)
    .sort((a, b) => b.matchScore - a.matchScore)[0] || null;
}

function opencitationsDoi(row) {
  const values = [row?.id, row?.doi, row?.identifier].filter(Boolean).join(" ");
  const match = values.match(/(?:^|\s)doi:(10\.\S+)/i) || values.match(/\b(10\.\d{4,9}\/\S+)\b/i);
  return match ? cleanDoi(match[1].replace(/[;,]$/, "")) : "";
}

function opencitationsMetaObservation(row, requested) {
  const doi = opencitationsDoi(row) || requested.doi;
  return observation({
    provider: "OpenCitations Meta",
    title: row?.title,
    year: cleanText(row?.pub_date, 20).slice(0, 4),
    doi,
    authors: row?.author,
    venue: row?.venue,
    abstract: "",
    articleUrl: doi ? `https://doi.org/${doi}` : "",
    sourceId: row?.id || "",
    relations: [row?.id, row?.venue].filter(Boolean),
    requested,
    matchType: "doi",
  });
}

async function openCitationsMeta(requestedInput) {
  const requested = requestedWork(requestedInput);
  if (!requested.doi) return null;
  const payload = await fetchJson(`${OPENCITATIONS_META_API}/metadata/doi:${encodeURIComponent(requested.doi)}`);
  const rows = Array.isArray(payload) ? payload : [];
  return rows.map((row) => opencitationsMetaObservation(row, requested)).find(Boolean) || null;
}

function openMetadataProviderManifest() {
  return OPEN_METADATA_PROVIDER_REGISTRY.map((provider) => ({ ...provider, enabled: true, enhanced: false }));
}

async function searchOpenScholarlyProviders({ title, doi, year }) {
  const requested = requestedWork({ title, doi, year });
  const calls = [
    { label: "arXiv", promise: arxiv(requested) },
    { label: "Zenodo", promise: zenodo(requested) },
    { label: "HAL", promise: hal(requested) },
    { label: "DOAJ", promise: doaj(requested) },
  ];
  if (requested.doi) calls.unshift({ label: "OpenCitations Meta", promise: openCitationsMeta(requested) });
  const settled = await Promise.allSettled(calls.map((entry) => entry.promise));
  const observations = settled
    .filter((entry) => entry.status === "fulfilled" && entry.value)
    .map((entry) => entry.value);
  const withAbstract = observations.filter((entry) => entry.abstract).sort((a, b) => b.matchScore - a.matchScore);
  return {
    result: withAbstract[0] || [...observations].sort((a, b) => b.matchScore - a.matchScore)[0] || null,
    observations,
    providersTried: calls.map((entry) => entry.label),
    providerErrors: settled
      .map((entry, index) => entry.status === "rejected" ? `${calls[index].label}:${entry.reason?.message || "error"}` : "")
      .filter(Boolean),
  };
}

export {
  OPEN_METADATA_PROVIDER_REGISTRY,
  arxiv,
  doaj,
  hal,
  openCitationsMeta,
  openMetadataProviderManifest,
  searchOpenScholarlyProviders,
  zenodo,
};
