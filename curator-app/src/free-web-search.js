"use strict";

import {
  resolveFreeWebCapabilities,
  webCapabilityManifest,
} from "./web-capability-resolver.js";

function cleanText(value, maximum = 1000) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, maximum);
}

function cleanDoi(value) {
  return cleanText(value, 300)
    .replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, "")
    .replace(/^doi:\s*/i, "")
    .trim();
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

async function handleFreeWebSearchRequest(request, env = {}) {
  const url = new URL(request.url);
  const candidateId = cleanText(url.searchParams.get("candidate"), 200);
  const title = cleanText(url.searchParams.get("title"), 1000);
  const doi = cleanDoi(url.searchParams.get("doi"));
  const year = cleanText(url.searchParams.get("year"), 10);
  if (!title) return json({ error: { code: "title_required", message: "Titolo mancante." } }, 400);

  const providerPlan = webCapabilityManifest(env);
  const search = await resolveFreeWebCapabilities({ title, doi, year, candidateId, env });

  if (search.result?.abstract) {
    const matchType = search.result.matchType === "discovered_page_reader"
      ? "free_web_search"
      : search.result.matchType;
    return json({
      ...search.result,
      matchType,
      providersTried: search.providersTried,
      providerErrors: search.providerErrors,
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
    providerErrors: search.providerErrors,
    providerPlan,
    providerUsage: search.providerUsage,
    searchStatus: search.searchStatus,
    freeCreditsUsed: search.freeCreditsUsed,
    freeRequestsUsed: search.freeRequestsUsed,
  }));
}

export { handleFreeWebSearchRequest };
