"use strict";

import { providerManifest, searchFreeWebProvider } from "./scholarly-providers.js";

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

function emptyResult({ doi, providersTried = [], providerErrors = [], searchStatus, providerPlan }) {
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
    searchStatus,
  };
}

async function handleFreeWebSearchRequest(request, env = {}) {
  const url = new URL(request.url);
  const title = cleanText(url.searchParams.get("title"), 1000);
  const doi = cleanDoi(url.searchParams.get("doi"));
  const year = cleanText(url.searchParams.get("year"), 10);
  if (!title) return json({ error: { code: "title_required", message: "Titolo mancante." } }, 400);

  const tavilyApiKey = cleanText(env.TAVILY_API_KEY, 300);
  const freeOnly = cleanText(env.TAVILY_FREE_ONLY, 20).toLowerCase() === "true";
  const providerPlan = providerManifest({ tavilyApiKey });

  if (!freeOnly || !tavilyApiKey) {
    return json(emptyResult({
      doi,
      providerPlan,
      searchStatus: "needs_web_search",
      providerErrors: !freeOnly ? ["Tavily Basic:free-only guard not enabled"] : [],
    }));
  }

  const search = await searchFreeWebProvider({ title, doi, year, tavilyApiKey });
  if (search.result?.abstract) {
    return json({
      ...search.result,
      providersTried: search.providersTried,
      providerErrors: search.providerErrors,
      providerPlan,
      searchStatus: "found",
      freeCreditsUsed: search.creditsUsed,
    });
  }

  const searchStatus = search.providerErrors.length ? "needs_web_search" : "web_search_exhausted";
  return json({
    ...emptyResult({
      doi,
      providersTried: search.providersTried,
      providerErrors: search.providerErrors,
      providerPlan,
      searchStatus,
    }),
    freeCreditsUsed: search.creditsUsed,
  });
}

export { handleFreeWebSearchRequest };
