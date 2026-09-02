"use strict";

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
    "id,doi,display_name,publication_year,abstract_inverted_index,primary_location,open_access",
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
  target.searchParams.set("select", "DOI,title,abstract,URL,published,issued,created");
  if (year) target.searchParams.set("filter", `from-pub-date:${year}-01-01,until-pub-date:${year}-12-31`);
  const payload = await fetchJson(target);
  const works = Array.isArray(payload?.message?.items) ? payload.message.items : [];
  return works
    .map((work) => ({ work, score: titleSimilarity(title, Array.isArray(work.title) ? work.title[0] : work.title) }))
    .sort((left, right) => right.score - left.score)[0]?.work || null;
}

function betterResult(primary, secondary) {
  if (primary?.abstract) return primary;
  if (secondary?.abstract) return secondary;
  return primary || secondary || null;
}

function decorated(result, providersTried, providerErrors = [], searchStatus = "found", providerPlan = []) {
  return {
    ...result,
    providersTried,
    providerErrors,
    searchStatus,
    providerPlan,
  };
}

async function enrichCandidate({
  title,
  doi,
  year,
  semanticScholarApiKey = "",
  coreApiKey = "",
  unpaywallEmail = "",
}) {
  const requested = {
    title: cleanText(title, 1000),
    doi: cleanDoi(doi),
    year: cleanText(year, 10),
  };
  if (!requested.title) throw new Error("missing_title");

  const providerPlan = [
    { id: "openalex", label: "OpenAlex", stage: "primary", billing: "anonymous_free" },
    { id: "crossref", label: "Crossref", stage: "primary", billing: "none" },
    ...providerManifest({ semanticScholarApiKey, coreApiKey, unpaywallEmail }),
  ];
  const providersTried = ["OpenAlex", "Crossref"];
  let baseline = null;

  if (requested.doi) {
    const [openAlex, crossref] = await Promise.allSettled([
      openAlexByDoi(requested.doi),
      crossrefByDoi(requested.doi),
    ]);
    const oaResult = openAlex.status === "fulfilled"
      ? resultFromOpenAlex(openAlex.value, requested, "doi")
      : null;
    const crResult = crossref.status === "fulfilled"
      ? resultFromCrossref(crossref.value, requested, "doi")
      : null;
    baseline = betterResult(oaResult, crResult);
    if (baseline?.abstract) return decorated(baseline, providersTried, [], "found", providerPlan);
  }

  const [openAlexSearch, crossrefSearch] = await Promise.allSettled([
    openAlexByTitle(requested.title, requested.year),
    crossrefByTitle(requested.title, requested.year),
  ]);
  const oaResult = openAlexSearch.status === "fulfilled"
    ? resultFromOpenAlex(openAlexSearch.value, requested, "title_year")
    : null;
  const crResult = crossrefSearch.status === "fulfilled"
    ? resultFromCrossref(crossrefSearch.value, requested, "title_year")
    : null;
  const titleBaseline = betterResult(oaResult, crResult);
  if (titleBaseline?.abstract) return decorated(titleBaseline, providersTried, [], "found", providerPlan);
  baseline = baseline || titleBaseline;

  const additional = await searchFreeScholarlyProviders({
    title: requested.title,
    doi: requested.doi,
    year: requested.year,
    semanticScholarApiKey,
    coreApiKey,
    unpaywallEmail,
  });
  providersTried.push(...additional.providersTried);
  if (additional.result?.abstract) {
    return decorated(additional.result, providersTried, additional.providerErrors, "found", providerPlan);
  }

  return decorated({
    abstract: "",
    abstractSource: "",
    provider: "",
    articleUrl: additional.result?.articleUrl || baseline?.articleUrl || (requested.doi ? `https://doi.org/${requested.doi}` : ""),
    matchedTitle: additional.result?.matchedTitle || baseline?.matchedTitle || "",
    matchedYear: additional.result?.matchedYear || baseline?.matchedYear || null,
    matchedDoi: additional.result?.matchedDoi || baseline?.matchedDoi || requested.doi,
    matchType: "needs_resolved_document",
    matchScore: additional.result?.matchScore || baseline?.matchScore || 0,
  }, providersTried, additional.providerErrors, "needs_resolved_document", providerPlan);
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
  if (!title) return json({ error: { code: "title_required", message: "Titolo mancante." } }, 400);
  try {
    const result = await enrichCandidate({
      title,
      doi,
      year,
      semanticScholarApiKey: cleanText(env.SEMANTIC_SCHOLAR_API_KEY, 300),
      coreApiKey: cleanText(env.CORE_API_KEY, 300),
      unpaywallEmail: cleanText(env.UNPAYWALL_EMAIL, 320),
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
