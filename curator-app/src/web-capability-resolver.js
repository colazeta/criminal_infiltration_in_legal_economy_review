"use strict";

import {
  cleanDoi,
  plainTextAbstract,
  searchFreeWebProvider,
  titleSimilarity,
} from "./scholarly-providers.js";
import { reserveProjectProviderBudget } from "./provider-budget.js";
import { safePublicHttpsUrl } from "./resolved-abstract.js";

const JINA_READER_BASE = "https://r.jina.ai/";
const SERPER_SEARCH_API = "https://google.serper.dev/search";
const EXA_SEARCH_API = "https://api.exa.ai/search";
const EXA_MAX_REPORTED_COST_USD = 0.01;

const WEB_CAPABILITY_REGISTRY = Object.freeze([
  {
    id: "jina_reader",
    label: "Jina Reader",
    layer: 1,
    capabilities: ["known_url_read", "page_to_text", "abstract_section_detection"],
    implemented: true,
    automaticAllowed: true,
    guard: "JINA_READER_FREE_ONLY",
    credential: "optional",
    paidBalancePossible: true,
  },
  {
    id: "serper",
    label: "Serper",
    layer: 2,
    capabilities: ["serp_search", "scholar_search", "news_search"],
    implemented: true,
    automaticAllowed: true,
    guard: "SERPER_FREE_ONLY",
    credential: "required",
    paidBalancePossible: true,
  },
  {
    id: "exa",
    label: "Exa Search",
    layer: 3,
    capabilities: ["semantic_web_search", "research_paper_search"],
    implemented: true,
    automaticAllowed: true,
    guard: "EXA_FREE_ONLY",
    credential: "required",
    paidBalancePossible: true,
  },
  {
    id: "tavily_basic",
    label: "Tavily Basic",
    layer: 3,
    capabilities: ["web_search", "result_content", "abstract_discovery"],
    implemented: true,
    automaticAllowed: true,
    guard: "TAVILY_FREE_ONLY",
    credential: "required",
    paidBalancePossible: true,
  },
  {
    id: "firecrawl",
    label: "Firecrawl",
    layer: 4,
    capabilities: ["web_search", "scrape", "crawl", "browser_interact", "agentic_research"],
    implemented: false,
    automaticAllowed: false,
    guard: "FIRECRAWL_FREE_ONLY",
    credential: "optional",
    paidBalancePossible: true,
  },
  {
    id: "cloudflare_browser_run",
    label: "Cloudflare Browser Run",
    layer: 4,
    capabilities: ["rendered_page", "browser_session", "dynamic_page_extract"],
    implemented: false,
    automaticAllowed: false,
    guard: "CLOUDFLARE_BROWSER_FREE_ONLY",
    credential: "binding",
    paidBalancePossible: true,
  },
]);

function cleanText(value, maximum = 1000) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, maximum);
}

function enabledGuard(env, name) {
  return cleanText(env?.[name], 20).toLowerCase() === "true";
}

function providerConfigured(provider, env) {
  if (!enabledGuard(env, provider.guard)) return false;
  if (provider.id === "tavily_basic") return Boolean(cleanText(env?.TAVILY_API_KEY, 400));
  if (provider.id === "serper") {
    return Boolean(cleanText(env?.SERPER_API_KEY, 400)) && enabledGuard(env, "SERPER_DEDICATED_FREE_ACCOUNT");
  }
  if (provider.id === "exa") {
    return Boolean(cleanText(env?.EXA_API_KEY, 400)) && enabledGuard(env, "EXA_DEDICATED_STARTER_ACCOUNT");
  }
  if (provider.id === "firecrawl") return Boolean(cleanText(env?.FIRECRAWL_API_KEY, 400)) || enabledGuard(env, "FIRECRAWL_KEYLESS_CONFIRMED");
  if (provider.id === "cloudflare_browser_run") return Boolean(env?.BROWSER);
  return true;
}

function webCapabilityManifest(env = {}) {
  return WEB_CAPABILITY_REGISTRY.map((provider) => {
    const configured = providerConfigured(provider, env);
    return {
      ...provider,
      configured,
      automaticEligible: Boolean(provider.implemented && provider.automaticAllowed && configured),
      mode: provider.implemented ? (configured ? "ready" : "guarded") : "registered_only",
    };
  });
}

function jinaKnownTarget(doi) {
  const normalized = cleanDoi(doi);
  return normalized ? `https://doi.org/${normalized}` : "";
}

function readerTitle(text) {
  const match = String(text || "").match(/^Title:\s*(.+)$/im);
  return cleanText(match?.[1], 1000);
}

async function readUrlWithJina({ title, doi, url, apiKey = "", requireTitleMatch = false, source = "resolved DOI" }) {
  const target = safePublicHttpsUrl(url);
  if (!target) return null;
  const headers = {
    Accept: "text/plain, text/markdown;q=0.9, */*;q=0.1",
    "User-Agent": "criminal-infiltration-curator/1.0",
  };
  if (apiKey) headers.Authorization = `Bearer ${apiKey}`;
  const response = await fetch(`${JINA_READER_BASE}${target}`, { headers });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`jina_reader_${response.status}`);
  const text = (await response.text()).slice(0, 120000);
  const matchedTitle = readerTitle(text);
  if (requireTitleMatch && !matchedTitle) return null;
  const similarity = matchedTitle ? titleSimilarity(title, matchedTitle) : 1;
  if (matchedTitle && similarity < 0.82) return null;
  const abstract = plainTextAbstract(text);
  if (!abstract) return null;
  return {
    abstract,
    abstractSource: `Jina Reader / ${source}`,
    provider: "Jina Reader",
    articleUrl: target,
    matchedTitle,
    matchedYear: null,
    matchedDoi: cleanDoi(doi),
    matchType: source === "resolved DOI" ? "free_page_reader" : "discovered_page_reader",
    matchScore: Number(similarity.toFixed(3)),
  };
}

async function readKnownUrlWithJina({ title, doi, apiKey = "" }) {
  const target = jinaKnownTarget(doi);
  if (!target) return null;
  return readUrlWithJina({ title, doi, url: target, apiKey, source: "resolved DOI" });
}

function exactDoiSignal(value, doi) {
  const normalized = cleanDoi(doi).toLowerCase();
  return Boolean(normalized && cleanText(value, 4000).toLowerCase().includes(normalized));
}

function bestDiscoveryCandidate(items, requestedTitle, doi) {
  return (Array.isArray(items) ? items : [])
    .map((item) => {
      const title = cleanText(item.title, 1000);
      const url = safePublicHttpsUrl(item.url || item.link);
      if (!title || !url) return null;
      const similarity = titleSimilarity(requestedTitle, title);
      const doiSignal = exactDoiSignal(`${title} ${url} ${item.snippet || ""}`, doi);
      if (!doiSignal && similarity < 0.72) return null;
      return {
        title,
        url,
        matchScore: doiSignal ? 1 : Number(similarity.toFixed(3)),
        matchType: doiSignal ? "doi_discovery" : "title_discovery",
      };
    })
    .filter(Boolean)
    .sort((a, b) => b.matchScore - a.matchScore)[0] || null;
}

async function searchSerper({ title, doi, apiKey }) {
  const query = `Exact scholarly publication \"${cleanText(title, 800)}\"${doi ? ` DOI ${cleanDoi(doi)}` : ""} publisher repository abstract PDF`;
  const response = await fetch(SERPER_SEARCH_API, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "User-Agent": "criminal-infiltration-curator/1.0",
      "X-API-KEY": apiKey,
    },
    body: JSON.stringify({ q: query, num: 5 }),
  });
  if (response.status === 402 || response.status === 429) throw new Error("serper_free_balance_unavailable");
  if (!response.ok) throw new Error(`serper_${response.status}`);
  const payload = await response.json();
  return bestDiscoveryCandidate(
    (payload?.organic || []).map((item) => ({ ...item, url: item.link })),
    title,
    doi,
  );
}

async function searchExa({ title, doi, apiKey }) {
  const query = `Find the exact scholarly publication titled \"${cleanText(title, 800)}\"${doi ? ` with DOI ${cleanDoi(doi)}` : ""}. Prefer the publisher, institutional repository, preprint, or author-hosted scholarly page.`;
  const response = await fetch(EXA_SEARCH_API, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "User-Agent": "criminal-infiltration-curator/1.0",
      "x-api-key": apiKey,
    },
    body: JSON.stringify({
      query,
      type: "fast",
      category: "research paper",
      numResults: 5,
    }),
  });
  if (response.status === 402 || response.status === 429) throw new Error("exa_free_balance_unavailable");
  if (!response.ok) throw new Error(`exa_${response.status}`);
  const payload = await response.json();
  const reportedCostUsd = Number(payload?.costDollars?.total || 0);
  if (reportedCostUsd > EXA_MAX_REPORTED_COST_USD) throw new Error("exa_cost_guard");
  const discovery = bestDiscoveryCandidate(payload?.results || [], title, doi);
  return { discovery, reportedCostUsd };
}

async function tryDiscoveredPageWithJina({ discovery, title, doi, env, providersTried, providerErrors, providerUsage }) {
  if (!discovery) return null;
  const jina = webCapabilityManifest(env).find((provider) => provider.id === "jina_reader");
  if (!jina?.automaticEligible) return null;
  if (!providersTried.includes(jina.label)) providersTried.push(jina.label);
  try {
    const result = await readUrlWithJina({
      title,
      doi,
      url: discovery.url,
      apiKey: cleanText(env?.JINA_API_KEY, 400),
      requireTitleMatch: true,
      source: "provider-discovered manifestation",
    });
    providerUsage.push({
      provider: jina.id,
      capability: "page_to_text",
      freeQuotaUsed: 0,
      quotaUnit: "request",
      requestsUsed: 1,
      discoveredUrl: discovery.url,
    });
    return result;
  } catch (error) {
    providerErrors.push(`${jina.label}:${error?.message || "error"}`);
    return null;
  }
}

async function resolveFreeWebCapabilities({ title, doi, year, candidateId = "", env = {} }) {
  const providerPlan = webCapabilityManifest(env);
  const providersTried = [];
  const providerErrors = [];
  const providerUsage = [];
  let freeCreditsUsed = 0;
  let freeRequestsUsed = 0;
  let completedSearch = false;

  const jina = providerPlan.find((provider) => provider.id === "jina_reader");
  if (jina?.automaticEligible && cleanDoi(doi)) {
    providersTried.push(jina.label);
    try {
      freeRequestsUsed += 1;
      const result = await readKnownUrlWithJina({
        title,
        doi,
        apiKey: cleanText(env?.JINA_API_KEY, 400),
      });
      providerUsage.push({ provider: jina.id, capability: "known_url_read", freeQuotaUsed: 0, quotaUnit: "request", requestsUsed: 1 });
      if (result?.abstract) {
        return {
          result,
          providersTried,
          providerErrors,
          providerPlan,
          providerUsage,
          freeCreditsUsed,
          freeRequestsUsed,
          searchStatus: "found",
        };
      }
    } catch (error) {
      providerErrors.push(`${jina.label}:${error?.message || "error"}`);
    }
  }

  const serper = providerPlan.find((provider) => provider.id === "serper");
  if (serper?.automaticEligible) {
    const budget = await reserveProjectProviderBudget(env, serper.id, candidateId);
    if (budget.allowed) {
      providersTried.push(serper.label);
      freeRequestsUsed += 1;
      try {
        const discovery = await searchSerper({
          title,
          doi,
          apiKey: cleanText(env?.SERPER_API_KEY, 400),
        });
        completedSearch = true;
        providerUsage.push({
          provider: serper.id,
          capability: "serp_search",
          freeQuotaUsed: 1,
          quotaUnit: "query",
          requestsUsed: 1,
          projectBudget: budget,
        });
        const result = await tryDiscoveredPageWithJina({ discovery, title, doi, env, providersTried, providerErrors, providerUsage });
        if (discovery) freeRequestsUsed += 1;
        if (result?.abstract) {
          return { result, providersTried, providerErrors, providerPlan, providerUsage, freeCreditsUsed, freeRequestsUsed, searchStatus: "found" };
        }
      } catch (error) {
        providerErrors.push(`${serper.label}:${error?.message || "error"}`);
      }
    } else {
      providerErrors.push(`${serper.label}:${budget.reason || "provider_project_budget_exhausted"}`);
    }
  }

  const exa = providerPlan.find((provider) => provider.id === "exa");
  if (exa?.automaticEligible) {
    const budget = await reserveProjectProviderBudget(env, exa.id, candidateId);
    if (budget.allowed) {
      providersTried.push(exa.label);
      freeRequestsUsed += 1;
      try {
        const { discovery, reportedCostUsd } = await searchExa({
          title,
          doi,
          apiKey: cleanText(env?.EXA_API_KEY, 400),
        });
        completedSearch = true;
        providerUsage.push({
          provider: exa.id,
          capability: "semantic_web_search",
          freeQuotaUsed: reportedCostUsd,
          quotaUnit: "usd_credit",
          requestsUsed: 1,
          projectBudget: budget,
        });
        const result = await tryDiscoveredPageWithJina({ discovery, title, doi, env, providersTried, providerErrors, providerUsage });
        if (discovery) freeRequestsUsed += 1;
        if (result?.abstract) {
          return { result, providersTried, providerErrors, providerPlan, providerUsage, freeCreditsUsed, freeRequestsUsed, searchStatus: "found" };
        }
      } catch (error) {
        providerErrors.push(`${exa.label}:${error?.message || "error"}`);
      }
    } else {
      providerErrors.push(`${exa.label}:${budget.reason || "provider_project_budget_exhausted"}`);
    }
  }

  const tavily = providerPlan.find((provider) => provider.id === "tavily_basic");
  if (tavily?.automaticEligible) {
    const search = await searchFreeWebProvider({
      title,
      doi,
      year,
      tavilyApiKey: cleanText(env?.TAVILY_API_KEY, 400),
    });
    for (const label of search.providersTried || []) {
      if (!providersTried.includes(label)) providersTried.push(label);
    }
    providerErrors.push(...(search.providerErrors || []));
    freeCreditsUsed += Number(search.creditsUsed || 0);
    freeRequestsUsed += search.configured ? 1 : 0;
    if (search.configured) {
      providerUsage.push({
        provider: tavily.id,
        capability: "web_search",
        freeQuotaUsed: Number(search.creditsUsed || 0),
        quotaUnit: "tavily_credit",
        requestsUsed: 1,
      });
      completedSearch = completedSearch || (search.providerErrors || []).length === 0;
    }
    if (search.result?.abstract) {
      return {
        result: search.result,
        providersTried,
        providerErrors,
        providerPlan,
        providerUsage,
        freeCreditsUsed,
        freeRequestsUsed,
        searchStatus: "found",
      };
    }
  }

  return {
    result: null,
    providersTried,
    providerErrors,
    providerPlan,
    providerUsage,
    freeCreditsUsed,
    freeRequestsUsed,
    searchStatus: completedSearch ? "web_search_exhausted" : "needs_web_search",
  };
}

export {
  EXA_MAX_REPORTED_COST_USD,
  WEB_CAPABILITY_REGISTRY,
  bestDiscoveryCandidate,
  readKnownUrlWithJina,
  readUrlWithJina,
  resolveFreeWebCapabilities,
  searchExa,
  searchSerper,
  webCapabilityManifest,
};
