"use strict";

const SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1";
const DATACITE_API = "https://api.datacite.org";
const UNPAYWALL_API = "https://api.unpaywall.org/v2";
const CORE_API = "https://api.core.ac.uk/v3";
const EUROPE_PMC_API = "https://www.ebi.ac.uk/europepmc/webservices/rest";
const TAVILY_API = "https://api.tavily.com/search";
const MAX_ABSTRACT_LENGTH = 12000;

const FREE_PROVIDER_REGISTRY = Object.freeze([
  { id: "semantic_scholar", label: "Semantic Scholar", stage: "scholarly", billing: "none", credential: "optional" },
  { id: "datacite", label: "DataCite", stage: "scholarly", billing: "none", credential: "none" },
  { id: "unpaywall", label: "Unpaywall", stage: "oa_resolution", billing: "none", credential: "email" },
  { id: "core", label: "CORE", stage: "repository", billing: "none", credential: "optional" },
  { id: "europe_pmc", label: "Europe PMC", stage: "scholarly", billing: "none", credential: "none" },
  { id: "tavily", label: "Tavily Basic", stage: "web", billing: "free_hard_cap", credential: "free_key" },
]);

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

function requestedWork({ title, doi, year }) {
  return {
    title: cleanText(title, 1000),
    doi: cleanDoi(doi),
    year: cleanText(year, 10),
  };
}

function result({ provider, title, year, doi, abstract, articleUrl, requested, matchType }) {
  const matchedTitle = cleanText(title, 1000);
  const matchedDoi = cleanDoi(doi);
  const similarity = titleSimilarity(requested.title, matchedTitle);
  if (matchType !== "doi" && (similarity < 0.86 || !yearCompatible(requested.year, year))) return null;
  if (matchType === "doi" && requested.doi && matchedDoi && requested.doi.toLowerCase() !== matchedDoi.toLowerCase()) return null;
  const abstractText = usableAbstract(abstract);
  return {
    abstract: abstractText,
    abstractSource: abstractText ? provider : "",
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
    const paperId = encodeURIComponent(`DOI:${requested.doi}`);
    const target = new URL(`${SEMANTIC_SCHOLAR_API}/paper/${paperId}`);
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

function unpaywallResult(work, requested, matchType) {
  const best = work?.best_oa_location || {};
  return result({
    provider: "Unpaywall",
    title: work?.title,
    year: work?.year,
    doi: work?.doi,
    abstract: "",
    articleUrl: best?.url_for_pdf || best?.url_for_landing_page || work?.doi_url,
    requested,
    matchType,
  });
}

async function unpaywall(requested, email = "") {
  const contact = cleanText(email, 320);
  if (!contact) return null;
  if (requested.doi) {
    const target = new URL(`${UNPAYWALL_API}/${encodeURIComponent(requested.doi)}`);
    target.searchParams.set("email", contact);
    const work = await fetchJson(target);
    if (work) {
      const exact = unpaywallResult(work, requested, "doi");
      if (exact) return exact;
    }
  }
  const target = new URL(`${UNPAYWALL_API}/search`);
  target.searchParams.set("query", `\"${requested.title}\"`);
  target.searchParams.set("email", contact);
  const payload = await fetchJson(target);
  const candidates = Array.isArray(payload?.results) ? payload.results : [];
  return candidates
    .map((entry) => unpaywallResult(entry?.response, requested, "title_year"))
    .filter(Boolean)
    .sort((a, b) => b.matchScore - a.matchScore)[0] || null;
}

function coreResult(item, requested) {
  return result({
    provider: "CORE",
    title: item?.title,
    year: item?.yearPublished,
    doi: item?.doi,
    abstract: item?.abstract,
    articleUrl: item?.downloadUrl || item?.sourceFulltextUrls?.[0] || item?.links?.[0],
    requested,
    matchType: requested.doi && cleanDoi(item?.doi).toLowerCase() === requested.doi.toLowerCase() ? "doi" : "title_year",
  });
}

async function core(requested, apiKey = "") {
  const target = new URL(`${CORE_API}/search/works`);
  const queryTitle = requested.title.replace(/"/g, "");
  target.searchParams.set("q", `title:\"${queryTitle}\"`);
  target.searchParams.set("limit", "5");
  const headers = apiKey ? { Authorization: `Bearer ${apiKey}` } : {};
  const payload = await fetchJson(target, headers);
  const candidates = Array.isArray(payload?.results) ? payload.results : [];
  return candidates
    .map((item) => coreResult(item, requested))
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
  const source = cleanText(text, 30000);
  if (!source) return "";
  const marked = source.match(/(?:^|\s)Abstract\s*[:.\-]?\s*(.{80,10000}?)(?=\s(?:Keywords?|JEL(?:\s+classification)?|Introduction|1\.?\s+Introduction)\b|$)/i);
  return marked ? usableAbstract(marked[1]) : "";
}

function tavilyResult(item, requested) {
  const title = cleanText(item?.title, 1000);
  const similarity = titleSimilarity(requested.title, title);
  if (similarity < 0.88) return null;
  const abstract = plainTextAbstract(item?.raw_content || "") || plainTextAbstract(item?.content || "");
  if (!abstract) return null;
  return {
    abstract,
    abstractSource: "Tavily / web",
    provider: "Tavily Basic",
    articleUrl: safeHttpsUrl(item?.url),
    matchedTitle: title,
    matchedYear: null,
    matchedDoi: requested.doi,
    matchType: "free_web_search",
    matchScore: Number(similarity.toFixed(3)),
  };
}

async function tavily(requested, apiKey = "") {
  if (!apiKey) return null;
  const response = await fetch(TAVILY_API, {
    method: "POST",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "User-Agent": "criminal-infiltration-curator/1.0",
    },
    body: JSON.stringify({
      query: `Exact scholarly publication titled \"${requested.title}\"${requested.doi ? ` DOI ${requested.doi}` : ""}. Find the publisher, repository, preprint or full-text page and the paper abstract.`,
      search_depth: "basic",
      auto_parameters: false,
      include_answer: false,
      include_raw_content: "text",
      max_results: 5,
    }),
  });
  if (!response.ok) throw new Error(`tavily_${response.status}`);
  const payload = await response.json();
  const credits = Number(payload?.usage?.credits || 0);
  if (credits > 1) throw new Error("tavily_credit_guard");
  const candidates = Array.isArray(payload?.results) ? payload.results : [];
  return candidates
    .map((item) => tavilyResult(item, requested))
    .filter(Boolean)
    .sort((a, b) => b.matchScore - a.matchScore)[0] || null;
}

function providerManifest({ unpaywallEmail = "", tavilyApiKey = "", coreApiKey = "", semanticScholarApiKey = "" } = {}) {
  return FREE_PROVIDER_REGISTRY.map((provider) => ({
    ...provider,
    enabled:
      provider.id === "unpaywall" ? Boolean(unpaywallEmail)
        : provider.id === "tavily" ? Boolean(tavilyApiKey)
          : true,
    enhanced:
      provider.id === "core" ? Boolean(coreApiKey)
        : provider.id === "semantic_scholar" ? Boolean(semanticScholarApiKey)
          : false,
  }));
}

async function searchFreeScholarlyProviders({
  title,
  doi,
  year,
  semanticScholarApiKey = "",
  coreApiKey = "",
  unpaywallEmail = "",
}) {
  const requested = requestedWork({ title, doi, year });
  const calls = [
    { label: "Semantic Scholar", promise: semanticScholar(requested, semanticScholarApiKey) },
    { label: "DataCite", promise: datacite(requested) },
    { label: "CORE", promise: core(requested, coreApiKey) },
    { label: "Europe PMC", promise: europePmc(requested) },
  ];
  if (unpaywallEmail) calls.splice(2, 0, { label: "Unpaywall", promise: unpaywall(requested, unpaywallEmail) });
  const settled = await Promise.allSettled(calls.map((entry) => entry.promise));
  const results = settled
    .filter((entry) => entry.status === "fulfilled" && entry.value)
    .map((entry) => entry.value);
  const withAbstract = results.filter((entry) => entry.abstract).sort((a, b) => b.matchScore - a.matchScore);
  return {
    result: withAbstract[0] || results.sort((a, b) => b.matchScore - a.matchScore)[0] || null,
    providersTried: calls.map((entry) => entry.label),
    providerErrors: settled
      .map((entry, index) => entry.status === "rejected" ? `${calls[index].label}:${entry.reason?.message || "error"}` : "")
      .filter(Boolean),
  };
}

async function searchFreeWebProvider({ title, doi, year, tavilyApiKey = "" }) {
  const requested = requestedWork({ title, doi, year });
  if (!tavilyApiKey) {
    return { result: null, providersTried: [], providerErrors: [], configured: false, creditsUsed: 0 };
  }
  try {
    const resultValue = await tavily(requested, tavilyApiKey);
    return {
      result: resultValue,
      providersTried: ["Tavily Basic"],
      providerErrors: [],
      configured: true,
      creditsUsed: 1,
    };
  } catch (error) {
    return {
      result: null,
      providersTried: ["Tavily Basic"],
      providerErrors: [`Tavily Basic:${error?.message || "error"}`],
      configured: true,
      creditsUsed: 0,
    };
  }
}

export {
  FREE_PROVIDER_REGISTRY,
  cleanDoi,
  core,
  datacite,
  europePmc,
  plainTextAbstract,
  providerManifest,
  searchFreeScholarlyProviders,
  searchFreeWebProvider,
  semanticScholar,
  tavily,
  titleSimilarity,
  unpaywall,
};
