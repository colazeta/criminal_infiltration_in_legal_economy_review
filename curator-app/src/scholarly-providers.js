"use strict";

const SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1";
const DATACITE_API = "https://api.datacite.org";
const EUROPE_PMC_API = "https://www.ebi.ac.uk/europepmc/webservices/rest";
const EXA_API = "https://api.exa.ai/search";
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

function yearCompatible(requested, candidate) {
  const left = Number(requested) || null;
  const right = Number(candidate) || null;
  return !left || !right || Math.abs(left - right) <= 1;
}

function safeHttpsUrl(value) {
  try {
    const url = new URL(String(value || ""));
    return url.protocol === "https:" ? url.toString() : "";
  } catch {
    return "";
  }
}

function decodeEntities(value) {
  return String(value || "")
    .replace(/&amp;/gi, "&")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">");
}

function stripMarkup(value) {
  return cleanText(
    decodeEntities(String(value || ""))
      .replace(/<script\b[\s\S]*?<\/script>/gi, " ")
      .replace(/<style\b[\s\S]*?<\/style>/gi, " ")
      .replace(/<[^>]+>/g, " "),
    MAX_ABSTRACT_LENGTH,
  );
}

function usableAbstract(value) {
  const text = stripMarkup(value);
  return text.length >= 60 ? text : "";
}

function result({ provider, title, year, doi, abstract, articleUrl, requested, matchType }) {
  const matchedTitle = cleanText(title, 1000);
  const matchedDoi = cleanDoi(doi);
  const similarity = titleSimilarity(requested.title, matchedTitle);
  if (matchType !== "doi" && (similarity < 0.86 || !yearCompatible(requested.year, year))) return null;
  if (matchType === "doi" && requested.doi && matchedDoi && requested.doi.toLowerCase() !== matchedDoi.toLowerCase()) return null;
  return {
    abstract: usableAbstract(abstract),
    abstractSource: usableAbstract(abstract) ? provider : "",
    provider,
    articleUrl: safeHttpsUrl(articleUrl) || (matchedDoi ? `https://doi.org/${matchedDoi}` : ""),
    matchedTitle,
    matchedYear: Number(year) || null,
    matchedDoi,
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

async function semanticScholar(requested, apiKey = "") {
  const headers = apiKey ? { "x-api-key": apiKey } : {};
  if (requested.doi) {
    const target = new URL(`${SEMANTIC_SCHOLAR_API}/paper/DOI:${requested.doi}`);
    target.searchParams.set("fields", "title,year,abstract,url,externalIds,openAccessPdf");
    const paper = await fetchJson(target, headers);
    if (paper) {
      return result({
        provider: "Semantic Scholar",
        title: paper.title,
        year: paper.year,
        doi: paper?.externalIds?.DOI || requested.doi,
        abstract: paper.abstract,
        articleUrl: paper?.openAccessPdf?.url || paper.url,
        requested,
        matchType: "doi",
      });
    }
  }
  const target = new URL(`${SEMANTIC_SCHOLAR_API}/paper/search`);
  target.searchParams.set("query", requested.title);
  target.searchParams.set("limit", "5");
  target.searchParams.set("fields", "title,year,abstract,url,externalIds,openAccessPdf");
  const payload = await fetchJson(target, headers);
  const candidates = Array.isArray(payload?.data) ? payload.data : [];
  return candidates
    .map((paper) => result({
      provider: "Semantic Scholar",
      title: paper.title,
      year: paper.year,
      doi: paper?.externalIds?.DOI,
      abstract: paper.abstract,
      articleUrl: paper?.openAccessPdf?.url || paper.url,
      requested,
      matchType: "title_year",
    }))
    .filter(Boolean)
    .sort((a, b) => b.matchScore - a.matchScore)[0] || null;
}

function dataciteAbstract(attributes) {
  const descriptions = Array.isArray(attributes?.descriptions) ? attributes.descriptions : [];
  const abstract = descriptions.find((entry) => String(entry?.descriptionType || "").toLowerCase() === "abstract");
  return abstract?.description || "";
}

function dataciteTitle(attributes) {
  const titles = Array.isArray(attributes?.titles) ? attributes.titles : [];
  return titles[0]?.title || "";
}

function dataciteResult(item, requested, matchType) {
  const attributes = item?.attributes || {};
  return result({
    provider: "DataCite",
    title: dataciteTitle(attributes),
    year: attributes.publicationYear,
    doi: attributes.doi || item?.id,
    abstract: dataciteAbstract(attributes),
    articleUrl: attributes.url,
    requested,
    matchType,
  });
}

async function datacite(requested) {
  if (requested.doi) {
    const payload = await fetchJson(`${DATACITE_API}/dois/${encodeURIComponent(requested.doi)}`);
    if (payload?.data) {
      const exact = dataciteResult(payload.data, requested, "doi");
      if (exact) return exact;
    }
  }
  const target = new URL(`${DATACITE_API}/dois`);
  target.searchParams.set("query", requested.title);
  target.searchParams.set("page[size]", "5");
  const payload = await fetchJson(target);
  const candidates = Array.isArray(payload?.data) ? payload.data : [];
  return candidates
    .map((item) => dataciteResult(item, requested, "title_year"))
    .filter(Boolean)
    .sort((a, b) => b.matchScore - a.matchScore)[0] || null;
}

function europePmcResult(item, requested, matchType) {
  return result({
    provider: "Europe PMC",
    title: item?.title,
    year: item?.pubYear,
    doi: item?.doi,
    abstract: item?.abstractText,
    articleUrl: item?.doi ? `https://doi.org/${cleanDoi(item.doi)}` : item?.pmcid ? `https://europepmc.org/article/PMC/${item.pmcid}` : "",
    requested,
    matchType,
  });
}

async function europePmc(requested) {
  const query = requested.doi ? `DOI:${requested.doi}` : `TITLE:\"${requested.title.replace(/\"/g, "")}\"`;
  const target = new URL(`${EUROPE_PMC_API}/search`);
  target.searchParams.set("query", query);
  target.searchParams.set("format", "json");
  target.searchParams.set("resultType", "core");
  target.searchParams.set("pageSize", "5");
  const payload = await fetchJson(target);
  const candidates = Array.isArray(payload?.resultList?.result) ? payload.resultList.result : [];
  return candidates
    .map((item) => europePmcResult(item, requested, requested.doi ? "doi" : "title_year"))
    .filter(Boolean)
    .sort((a, b) => b.matchScore - a.matchScore)[0] || null;
}

function plainTextAbstract(text) {
  const source = cleanText(text, 20000);
  if (!source) return "";
  const marked = source.match(/(?:^|\s)Abstract\s*[:.\-]?\s*(.{80,8000}?)(?=\s(?:Keywords?|JEL(?:\s+classification)?|Introduction|1\.?\s+Introduction)\b|$)/i);
  if (marked) return usableAbstract(marked[1]);
  return "";
}

function exaResult(item, requested) {
  const title = cleanText(item?.title, 1000);
  const similarity = titleSimilarity(requested.title, title);
  if (similarity < 0.88) return null;
  const text = plainTextAbstract(item?.text || "") || (Array.isArray(item?.highlights) ? plainTextAbstract(item.highlights.join(" ")) : "");
  if (!text) return null;
  return {
    abstract: text,
    abstractSource: "Exa / web",
    provider: "Exa",
    articleUrl: safeHttpsUrl(item?.url),
    matchedTitle: title,
    matchedYear: item?.publishedDate ? Number(String(item.publishedDate).slice(0, 4)) || null : null,
    matchedDoi: requested.doi,
    matchType: "web_search",
    matchScore: Number(similarity.toFixed(3)),
  };
}

async function exa(requested, apiKey = "") {
  if (!apiKey) return null;
  const response = await fetch(EXA_API, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "User-Agent": "criminal-infiltration-curator/1.0",
      "x-api-key": apiKey,
    },
    body: JSON.stringify({
      query: `Exact scholarly publication titled \"${requested.title}\"${requested.doi ? ` DOI ${requested.doi}` : ""}. Find the publication, repository, preprint, publisher or full-text page and its abstract.`,
      category: "publication",
      type: "auto",
      numResults: 8,
      contents: { text: true, highlights: true },
    }),
  });
  if (!response.ok) throw new Error(`exa_${response.status}`);
  const payload = await response.json();
  const candidates = Array.isArray(payload?.results) ? payload.results : [];
  return candidates
    .map((item) => exaResult(item, requested))
    .filter(Boolean)
    .sort((a, b) => b.matchScore - a.matchScore)[0] || null;
}

async function searchAdditionalProviders({ title, doi, year, semanticScholarApiKey = "", exaApiKey = "" }) {
  const requested = {
    title: cleanText(title, 1000),
    doi: cleanDoi(doi),
    year: cleanText(year, 10),
  };
  const providersTried = ["Semantic Scholar", "DataCite", "Europe PMC"];
  if (exaApiKey) providersTried.push("Exa");
  const calls = [
    semanticScholar(requested, semanticScholarApiKey),
    datacite(requested),
    europePmc(requested),
  ];
  if (exaApiKey) calls.push(exa(requested, exaApiKey));
  const settled = await Promise.allSettled(calls);
  const results = settled
    .filter((entry) => entry.status === "fulfilled" && entry.value)
    .map((entry) => entry.value);
  const withAbstract = results
    .filter((entry) => entry.abstract)
    .sort((a, b) => b.matchScore - a.matchScore);
  return {
    result: withAbstract[0] || results.sort((a, b) => b.matchScore - a.matchScore)[0] || null,
    providersTried,
    exaConfigured: Boolean(exaApiKey),
    providerErrors: settled
      .map((entry, index) => entry.status === "rejected" ? `${providersTried[index] || `provider-${index}`}:${entry.reason?.message || "error"}` : "")
      .filter(Boolean),
  };
}

export {
  cleanDoi,
  datacite,
  europePmc,
  exa,
  plainTextAbstract,
  searchAdditionalProviders,
  semanticScholar,
  titleSimilarity,
};
