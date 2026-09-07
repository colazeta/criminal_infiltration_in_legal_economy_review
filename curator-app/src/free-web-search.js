"use strict";

import {
  resolveFreeWebCapabilities,
  webCapabilityManifest,
} from "./web-capability-resolver.js";
import { plainTextAbstract, titleSimilarity } from "./scholarly-providers.js";

const JINA_READER_BASE = "https://r.jina.ai/";

function cleanText(value, maximum = 1000) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, maximum);
}

function cleanDoi(value) {
  return cleanText(value, 300)
    .replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, "")
    .replace(/^doi:\s*/i, "")
    .trim();
}

function safePublicHttpsUrl(value) {
  try {
    const url = new URL(String(value || ""));
    if (url.protocol !== "https:") return "";
    const host = url.hostname.toLowerCase();
    if (!host || host === "localhost" || host.endsWith(".localhost") || host.endsWith(".local")) return "";
    return url.toString();
  } catch {
    return "";
  }
}

function enabledGuard(env, name) {
  return cleanText(env?.[name], 20).toLowerCase() === "true";
}

function readerTitle(text) {
  const match = String(text || "").match(/^Title:\s*(.+)$/im);
  return cleanText(match?.[1], 1000);
}

async function readVerifiedAbstractLocator({ title, doi, retrieval, env }) {
  if (!enabledGuard(env, "JINA_READER_FREE_ONLY")) return null;
  if (cleanText(retrieval?.abstractCoverageStatus, 40) !== "available") return null;
  const target = safePublicHttpsUrl(retrieval?.abstractArticleUrl);
  if (!target) return null;

  const headers = {
    Accept: "text/plain, text/markdown;q=0.9, */*;q=0.1",
    "User-Agent": "criminal-infiltration-curator/1.0",
  };
  const apiKey = cleanText(env?.JINA_API_KEY, 400);
  if (apiKey) headers.Authorization = `Bearer ${apiKey}`;

  const response = await fetch(`${JINA_READER_BASE}${target}`, { headers });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`jina_verified_locator_${response.status}`);
  const text = (await response.text()).slice(0, 120000);
  const matchedTitle = readerTitle(text);
  const similarity = matchedTitle ? titleSimilarity(title, matchedTitle) : 1;
  if (matchedTitle && similarity < 0.72) return null;
  const abstract = plainTextAbstract(text);
  if (!abstract) return null;

  const sourceLabel = cleanText(retrieval?.abstractSource, 300) || "verified abstract locator";
  return {
    abstract,
    abstractSource: `Jina Reader / ${sourceLabel}`,
    provider: "Jina Reader",
    articleUrl: target,
    matchedTitle,
    matchedYear: null,
    matchedDoi: cleanDoi(doi),
    matchType: "resolved_url",
    matchScore: Number(similarity.toFixed(3)),
  };
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

function emptyResult({ doi, providersTried = [], providerErrors = [], searchStatus, providerPlan, providerUsage = [], freeCreditsUsed = 0, freeRequestsUsed = 0 }) {
  return {
    abstract: "",
    abstractSource: "",
    provider: "",
    articleUrl: doi ? `https://doi.org/${doi}` : "",
    matchedTitle: "",
    matchedYear: null,
    matchedDoi: doi,
    matchType: searchStatus,
    matchScore: 0,
    providersTried,
    providerErrors,
    providerPlan,
    providerUsage,
    searchStatus,
    freeCreditsUsed,
    freeRequestsUsed,
  };
}

async function handleFreeWebSearchRequest(request, env = {}, retrieval = null) {
  const url = new URL(request.url);
  const candidateId = cleanText(url.searchParams.get("candidate"), 200);
  const title = cleanText(url.searchParams.get("title"), 1000);
  const doi = cleanDoi(url.searchParams.get("doi"));
  const year = cleanText(url.searchParams.get("year"), 10);
  if (!title) return json({ error: { code: "title_required", message: "Titolo mancante." } }, 400);

  const providerPlan = webCapabilityManifest(env);
  const locatorErrors = [];
  if (retrieval?.abstractCoverageStatus === "available" && retrieval?.abstractArticleUrl) {
    try {
      const located = await readVerifiedAbstractLocator({ title, doi, retrieval, env });
      if (located?.abstract) {
        return json({
          ...located,
          providersTried: ["Verified abstract locator", "Jina Reader"],
          providerErrors: [],
          providerPlan,
          providerUsage: [{
            provider: "jina_reader",
            capability: "verified_abstract_locator_read",
            freeQuotaUsed: 0,
            quotaUnit: "request",
            requestsUsed: 1,
            sourceUrl: retrieval.abstractArticleUrl,
          }],
          searchStatus: "found",
          freeCreditsUsed: 0,
          freeRequestsUsed: 1,
        });
      }
    } catch (error) {
      locatorErrors.push(`Verified abstract locator:${error?.message || "error"}`);
    }
  }

  const search = await resolveFreeWebCapabilities({ title, doi, year, candidateId, env });
  const providerErrors = [...locatorErrors, ...(search.providerErrors || [])];

  if (search.result?.abstract) {
    const matchType = search.result.matchType === "discovered_page_reader"
      ? "free_web_search"
      : search.result.matchType;
    return json({
      ...search.result,
      matchType,
      providersTried: search.providersTried,
      providerErrors,
      providerPlan,
      providerUsage: search.providerUsage,
      searchStatus: "found",
      freeCreditsUsed: search.freeCreditsUsed,
      freeRequestsUsed: search.freeRequestsUsed,
    });
  }

  return json(emptyResult({
    doi,
    providersTried: search.providersTried,
    providerErrors,
    providerPlan,
    providerUsage: search.providerUsage,
    searchStatus: search.searchStatus,
    freeCreditsUsed: search.freeCreditsUsed,
    freeRequestsUsed: search.freeRequestsUsed,
  }));
}

export { handleFreeWebSearchRequest, readVerifiedAbstractLocator };
