"use strict";

import {
  cleanDoi,
  plainTextAbstract,
  searchFreeWebProvider,
  titleSimilarity,
} from "./scholarly-providers.js";

const JINA_READER_BASE = "https://r.jina.ai/";

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
    implemented: false,
    automaticAllowed: false,
    guard: "SERPER_FREE_ONLY",
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
    id: "exa",
    label: "Exa",
    layer: 3,
    capabilities: ["semantic_web_search", "contents", "deep_search", "agentic_research"],
    implemented: false,
    automaticAllowed: false,
    guard: "EXA_FREE_ONLY",
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
  if (provider.id === "serper") return Boolean(cleanText(env?.SERPER_API_KEY, 400));
  if (provider.id === "exa") return Boolean(cleanText(env?.EXA_API_KEY, 400));
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

async function readKnownUrlWithJina({ title, doi, apiKey = "" }) {
  const target = jinaKnownTarget(doi);
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
  const similarity = matchedTitle ? titleSimilarity(title, matchedTitle) : 1;
  if (matchedTitle && similarity < 0.82) return null;
  const abstract = plainTextAbstract(text);
  if (!abstract) return null;
  return {
    abstract,
    abstractSource: "Jina Reader / resolved DOI",
    provider: "Jina Reader",
    articleUrl: target,
    matchedTitle,
    matchedYear: null,
    matchedDoi: cleanDoi(doi),
    matchType: "free_page_reader",
    matchScore: Number(similarity.toFixed(3)),
  };
}

async function resolveFreeWebCapabilities({ title, doi, year, env = {} }) {
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
      providerUsage.push({ provider: jina.id, capability: "known_url_read", freeCreditsUsed: 0, requestsUsed: 1 });
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
        freeCreditsUsed: Number(search.creditsUsed || 0),
        requestsUsed: 1,
      });
      completedSearch = (search.providerErrors || []).length === 0;
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
  WEB_CAPABILITY_REGISTRY,
  readKnownUrlWithJina,
  resolveFreeWebCapabilities,
  webCapabilityManifest,
};
