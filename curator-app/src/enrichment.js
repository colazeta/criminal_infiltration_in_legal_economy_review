"use strict";

import { citationFrontier } from "./citation-chasing.js";
import { reconcileMetadata } from "./metadata-reconciliation.js";
import { openMetadataProviderManifest, searchOpenScholarlyProviders } from "./open-scholarly-providers.js";
import { providerManifest, searchFreeScholarlyProviders } from "./scholarly-providers.js";

const OPENALEX_API = "https://api.openalex.org";
const CROSSREF_API = "https://api.crossref.org";
const MAX_ABSTRACT_LENGTH = 12000;

function cleanText(value, maximum = 1000) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, maximum);
}

function cleanDoi(value) {
  return cleanText(value, 300)
    .replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, "")
    .replace(/^doi:\s*/i, "")
    .trim();
}

function normaliseTitle(value) {
  return cleanText(value, 1000)
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function titleTokens(value) {
  return new Set(normaliseTitle(value).split(" ").filter((token) => token.length > 2));
}

function titleSimilarity(left, right) {
  const a = titleTokens(left);
  const b = titleTokens(right);
  if (!a.size || !b.size) return 0;
  let overlap = 0;
  for (const token of a) if (b.has(token)) overlap += 1;
  return (2 * overlap) / (a.size + b.size);
}

function reconstructAbstract(inverted) {
  if (!inverted || typeof inverted !== "object" || Array.isArray(inverted)) return "";
  const positions = [];
  for (const [word, indexes] of Object.entries(inverted)) {
    if (!Array.isArray(indexes)) continue;
    for (const index of indexes) {
      if (Number.isInteger(index) && index >= 0 && index < 10000) positions.push([index, word]);
    }
  }
  positions.sort((left, right) => left[0] - right[0]);
  return cleanText(positions.map(([, word]) => word).join(" "), MAX_ABSTRACT_LENGTH);
}

function stripJats(value) {
  return cleanText(
    String(value || "")
      .replace(/<\/?jats:[^>]+>/gi, " ")
      .replace(/<[^>]+>/g, " ")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&amp;/g, "&")
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'"),
    MAX_ABSTRACT_LENGTH,
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

function openAlexArticleUrl(work) {
  const candidates = [
    work?.primary_location?.landing_page_url,
    work?.open_access?.oa_url,
    work?.doi,
  ];
  for (const candidate of candidates) {
    const safe = safeHttpsUrl(candidate);
    if (safe) return safe;
  }
  return "";
}

function openAlexAuthors(work) {
  return (Array.isArray(work?.authorships) ? work.authorships : [])
    .map((entry) => entry?.author?.display_name)
    .filter(Boolean)
    .join("; ");
}

function crossrefAuthors(message) {
  return (Array.isArray(message?.author) ? message.author : [])
    .map((author) => cleanText([author?.given, author?.family].filter(Boolean).join(" "), 300))
    .filter(Boolean)
    .join("; ");
}

function crossrefArticleUrl(message) {
  const doi = cleanDoi(message?.DOI || "");
  if (doi) return `https://doi.org/${doi}`;
  return safeHttpsUrl(message?.URL);
}

function resultFromOpenAlex(work, requested, matchType) {
  if (!work) return null;
  const title = cleanText(work.display_name || work.title, 1000);
  const year = Number(work.publication_year) || null;
  const doi = cleanDoi(work.doi || "");
  const abstract = reconstructAbstract(work.abstract_inverted_index);
  const similarity = titleSimilarity(requested.title, title);
  const requestedYear = Number(requested.year) || null;
  const yearCompatible = !requestedYear || !year || Math.abs(requestedYear - year) <= 1;
  if (matchType !== "doi" && (similarity < 0.86 || !yearCompatible)) return null;
  if (matchType === "doi" && requested.doi && doi && requested.doi.toLowerCase() !== doi.toLowerCase()) return null;
  return {
    abstract,
    abstractSource: abstract ? "OpenAlex" : "",
    provider: "OpenAlex",
    articleUrl: openAlexArticleUrl(work),
    matchedTitle: title,
    matchedYear: year,
    matchedDoi: doi,
    authors: openAlexAuthors(work),
    venue: cleanText(work?.primary_location?.source?.display_name, 1000),
    sourceId: cleanText(work?.id, 500),
    relations: [],
    matchType,
    matchScore: matchType === "doi" ? 1 : Number(similarity.toFixed(3)),
  };
}

function resultFromCrossref(message, requested, matchType) {
  if (!message) return null;
  const title = cleanText(Array.isArray(message.title) ? message.title[0] : message.title, 1000);
  const year = Number(
    message?.published?.["date-parts"]?.[0]?.[0]
      || message?.issued?.["date-parts"]?.[0]?.[0]
      || message?.created?.["date-parts"]?.[0]?.[0],
  ) || null;
  const doi = cleanDoi(message.DOI || "");
  const abstract = stripJats(message.abstract || "");
  const similarity = titleSimilarity(requested.title, title);
  const requestedYear = Number(requested.year) || null;
  const yearCompatible = !requestedYear || !year || Math.abs(requestedYear - year) <= 1;
  if (matchType !== "doi" && (similarity < 0.9 || !yearCompatible)) return null;
  if (matchType === "doi" && requested.doi && doi && requested.doi.toLowerCase() !== doi.toLowerCase()) return null;
  return {
    abstract,
    abstractSource: abstract ? "Crossref" : "",
    provider: "Crossref",
    articleUrl: crossrefArticleUrl(message),
    matchedTitle: title,
    matchedYear: year,
    matchedDoi: doi,
    authors: crossrefAuthors(message),
    venue: cleanText(Array.isArray(message?.["container-title"]) ? message["container-title"][0] : message?.["container-title"], 1000),
    sourceId: doi ? `doi:${doi}` : "",
    relations: Object.entries(message?.relation || {}).flatMap(([relation, rows]) =>
      (Array.isArray(rows) ? rows : []).map((row) => `${relation}:${cleanText(row?.id || row?.["id-type"], 400)}`).filter(Boolean)),
    matchType,
    matchScore: matchType === "doi" ? 1 : Number(similarity.toFixed(3)),
  };
}

async function fetchJson(url) {
  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
      "User-Agent": "criminal-infiltration-curator/1.0",
    },
  });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`upstream_${response.status}`);
  return response.json();
}

async function openAlexByDoi(doi) {
  return (await fetchJson(`${OPENALEX_API}/works/https://doi.org/${doi}`)) || null;
}

async function openAlexByTitle(title, year) {
  const target = new URL(`${OPENALEX_API}/works`);
  target.searchParams.set("search", title);
  target.searchParams.set("per_page", "5");
  target.searchParams.set(
    "select",
    "id,doi,display_name,publication_year,abstract_inverted_index,primary_location,open_access,authorships",
  );
  if (year) target.searchParams.set("filter", `publication_year:${year}`);
  const payload = await fetchJson(target);
  const works = Array.isArray(payload?.results) ? payload.results : [];
  return works
    .map((work) => ({ work, score: titleSimilarity(title, work?.display_name || "") }))
    .sort((left, right) => right.score - left.score)[0]?.work || null;
}

async function crossrefByDoi(doi) {
  const payload = await fetchJson(`${CROSSREF_API}/works/${encodeURIComponent(doi)}`);
  return payload?.message || null;
}

async function crossrefByTitle(title, year) {
  const target = new URL(`${CROSSREF_API}/works`);
  target.searchParams.set("query.bibliographic", title);
  target.searchParams.set("rows", "5");
  target.searchParams.set("select", "DOI,title,abstract,URL,published,issued,created,author,container-title,relation");
  if (year) target.searchParams.set("filter", `from-pub-date:${year}-01-01,until-pub-date:${year}-12-31`);
  const payload = await fetchJson(target);
  const works = Array.isArray(payload?.message?.items) ? payload.message.items : [];
  return works
    .map((work) => ({ work, score: titleSimilarity(title, Array.isArray(work.title) ? work.title[0] : work.title) }))
    .sort((left, right) => right.score - left.score)[0]?.work || null;
}

function scoreResult(result) {
  if (!result) return -1;
  return (result.abstract ? 100 : 0) + (result.matchType === "doi" ? 20 : 0) + Number(result.matchScore || 0);
}

function bestResult(results) {
  return results.filter(Boolean).sort((left, right) => scoreResult(right) - scoreResult(left))[0] || null;
}

function uniqueObservations(observations) {
  const seen = new Set();
  const rows = [];
  for (const observation of observations.filter(Boolean)) {
    const key = [
      observation.provider,
      cleanDoi(observation.matchedDoi || "").toLowerCase(),
      normaliseTitle(observation.matchedTitle || ""),
      observation.matchedYear || "",
    ].join("|");
    if (seen.has(key)) continue;
    seen.add(key);
    rows.push(observation);
  }
  return rows;
}

function compactObservations(observations) {
  return observations.map((entry) => ({
    provider: entry.provider,
    title: entry.matchedTitle || "",
    year: entry.matchedYear || null,
    doi: entry.matchedDoi || "",
    authors: entry.authors || "",
    venue: entry.venue || "",
    articleUrl: entry.articleUrl || "",
    sourceId: entry.sourceId || "",
    relations: Array.isArray(entry.relations) ? entry.relations.slice(0, 12) : [],
    hasAbstract: Boolean(entry.abstract),
    matchType: entry.matchType,
    matchScore: entry.matchScore,
  }));
}

function decorated(result, providersTried, providerErrors = [], searchStatus = "found", providerPlan = [], extras = {}) {
  return {
    ...result,
    providersTried,
    providerErrors,
    searchStatus,
    providerPlan,
    ...extras,
  };
}

async function enrichCandidate({
  title,
  doi,
  year,
  authors = "",
  venue = "",
  semanticScholarApiKey = "",
  coreApiKey = "",
  unpaywallEmail = "",
  includeCitationFrontier = false,
}) {
  const requested = {
    title: cleanText(title, 1000),
    doi: cleanDoi(doi),
    year: cleanText(year, 10),
    authors: cleanText(authors, 3000),
    venue: cleanText(venue, 1000),
  };
  if (!requested.title) throw new Error("missing_title");

  const providerPlan = [
    { id: "openalex", label: "OpenAlex", stage: "primary", billing: "free_daily_credit" },
    { id: "crossref", label: "Crossref", stage: "primary", billing: "none" },
    ...providerManifest({ semanticScholarApiKey, coreApiKey, unpaywallEmail }),
    ...openMetadataProviderManifest(),
  ];
  const providersTried = ["OpenAlex", "Crossref"];
  const providerErrors = [];
  const baselineObservations = [];

  if (requested.doi) {
    const [openAlex, crossref] = await Promise.allSettled([
      openAlexByDoi(requested.doi),
      crossrefByDoi(requested.doi),
    ]);
    if (openAlex.status === "rejected") providerErrors.push(`OpenAlex:${openAlex.reason?.message || "error"}`);
    if (crossref.status === "rejected") providerErrors.push(`Crossref:${crossref.reason?.message || "error"}`);
    const oaResult = openAlex.status === "fulfilled" ? resultFromOpenAlex(openAlex.value, requested, "doi") : null;
    const crResult = crossref.status === "fulfilled" ? resultFromCrossref(crossref.value, requested, "doi") : null;
    if (oaResult) baselineObservations.push(oaResult);
    if (crResult) baselineObservations.push(crResult);
  }

  if (!requested.doi || baselineObservations.length === 0) {
    const [openAlexSearch, crossrefSearch] = await Promise.allSettled([
      openAlexByTitle(requested.title, requested.year),
      crossrefByTitle(requested.title, requested.year),
    ]);
    if (openAlexSearch.status === "rejected") providerErrors.push(`OpenAlex:${openAlexSearch.reason?.message || "error"}`);
    if (crossrefSearch.status === "rejected") providerErrors.push(`Crossref:${crossrefSearch.reason?.message || "error"}`);
    const oaResult = openAlexSearch.status === "fulfilled" ? resultFromOpenAlex(openAlexSearch.value, requested, "title_year") : null;
    const crResult = crossrefSearch.status === "fulfilled" ? resultFromCrossref(crossrefSearch.value, requested, "title_year") : null;
    if (oaResult) baselineObservations.push(oaResult);
    if (crResult) baselineObservations.push(crResult);
  }

  const [additional, openAdditional] = await Promise.all([
    searchFreeScholarlyProviders({
      title: requested.title,
      doi: requested.doi,
      year: requested.year,
      semanticScholarApiKey,
      coreApiKey,
      unpaywallEmail,
    }),
    searchOpenScholarlyProviders({
      title: requested.title,
      doi: requested.doi,
      year: requested.year,
    }),
  ]);
  providersTried.push(...additional.providersTried, ...openAdditional.providersTried);
  providerErrors.push(...additional.providerErrors, ...openAdditional.providerErrors);

  const observations = uniqueObservations([
    ...baselineObservations,
    additional.result,
    ...openAdditional.observations,
  ]);
  const chosen = bestResult(observations);
  const metadataResolution = reconcileMetadata({ requested, observations });
  const resolvedDoi = cleanDoi(metadataResolution?.fields?.doi?.value || chosen?.matchedDoi || requested.doi);
  const citations = includeCitationFrontier && resolvedDoi
    ? await citationFrontier({ doi: resolvedDoi, semanticScholarApiKey })
    : null;
  const searchStatus = chosen?.abstract ? "found" : "needs_resolved_document";

  const result = chosen || {
    abstract: "",
    abstractSource: "",
    provider: "",
    articleUrl: resolvedDoi ? `https://doi.org/${resolvedDoi}` : "",
    matchedTitle: metadataResolution?.fields?.title?.value || "",
    matchedYear: metadataResolution?.fields?.year?.value || null,
    matchedDoi: resolvedDoi,
    authors: metadataResolution?.fields?.authors?.value || "",
    venue: metadataResolution?.fields?.venue?.value || "",
    matchType: "needs_resolved_document",
    matchScore: 0,
  };

  return decorated(result, [...new Set(providersTried)], providerErrors, searchStatus, providerPlan, {
    metadataResolution,
    metadataObservations: compactObservations(observations),
    citationFrontier: citations,
  });
}

function json(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Cache-Control": "no-store",
      "Content-Type": "application/json; charset=utf-8",
      "Referrer-Policy": "no-referrer",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

async function handleEnrichmentRequest(request, env = {}) {
  const url = new URL(request.url);
  const title = cleanText(url.searchParams.get("title"), 1000);
  const doi = cleanDoi(url.searchParams.get("doi"));
  const year = cleanText(url.searchParams.get("year"), 10);
  const authors = cleanText(url.searchParams.get("authors"), 3000);
  const venue = cleanText(url.searchParams.get("venue"), 1000);
  const includeCitationFrontier = url.searchParams.get("citations") === "1";
  if (!title) return json({ error: { code: "title_required", message: "Titolo mancante." } }, 400);
  try {
    const result = await enrichCandidate({
      title,
      doi,
      year,
      authors,
      venue,
      semanticScholarApiKey: cleanText(env.SEMANTIC_SCHOLAR_API_KEY, 300),
      coreApiKey: cleanText(env.CORE_API_KEY, 300),
      unpaywallEmail: cleanText(env.UNPAYWALL_EMAIL, 320),
      includeCitationFrontier,
    });
    return json(result);
  } catch {
    return json({
      abstract: "",
      abstractSource: "",
      provider: "",
      articleUrl: doi ? `https://doi.org/${doi}` : "",
      matchedTitle: "",
      matchedYear: null,
      matchedDoi: doi,
      matchType: "unavailable",
      matchScore: 0,
      providersTried: [],
      providerErrors: [],
      providerPlan: [],
      metadataResolution: null,
      metadataObservations: [],
      citationFrontier: null,
      searchStatus: "unavailable",
    });
  }
}

export {
  cleanDoi,
  enrichCandidate,
  handleEnrichmentRequest,
  normaliseTitle,
  reconstructAbstract,
  stripJats,
  titleSimilarity,
};
