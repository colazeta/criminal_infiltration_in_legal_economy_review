"use strict";

import assert from "node:assert/strict";
import test from "node:test";

import { handleFreeWebSearchRequest } from "../src/free-web-search.js";

function withFetchMock(context, implementation) {
  const original = globalThis.fetch;
  context.after(() => {
    globalThis.fetch = original;
  });
  globalThis.fetch = implementation;
}

const title = "Bricks or cooks? Geographical and social determinants of the investment choices of mafia-type organized crime";

function request() {
  const url = new URL("https://curator.example/api/free-web-search");
  url.searchParams.set("title", title);
  url.searchParams.set("doi", "10.1177/17488958241293927");
  url.searchParams.set("year", "2024");
  return new Request(url);
}

test("free web endpoint makes no external request when free-only guards are disabled", async (context) => {
  withFetchMock(context, async () => {
    throw new Error("must not call any web provider without an enabled free-only guard");
  });
  const response = await handleFreeWebSearchRequest(request(), {});
  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.equal(payload.searchStatus, "needs_web_search");
  assert.equal(payload.matchType, "needs_web_search");
  assert.deepEqual(payload.providersTried, []);
  assert.equal(payload.freeCreditsUsed, 0);
  assert.equal(payload.freeRequestsUsed, 0);
  assert.equal(payload.providerPlan.find((provider) => provider.id === "exa").automaticEligible, false);
});

test("free web endpoint can recover an abstract through the zero-credit Jina Reader layer", async (context) => {
  withFetchMock(context, async (url) => {
    assert.match(String(url), /^https:\/\/r\.jina\.ai\/https:\/\/doi\.org\//);
    return new Response(
      `Title: ${title}\n\nAbstract This article studies legitimate businesses confiscated from mafia groups in Italy and their investment choices across sectors and territories, with enough detail for a reliable abstract extraction. Introduction The article then presents data and methods.`,
      { status: 200 },
    );
  });
  const response = await handleFreeWebSearchRequest(request(), {
    JINA_READER_FREE_ONLY: "true",
  });
  const payload = await response.json();
  assert.equal(payload.searchStatus, "found");
  assert.equal(payload.matchType, "free_page_reader");
  assert.equal(payload.provider, "Jina Reader");
  assert.equal(payload.freeCreditsUsed, 0);
  assert.equal(payload.freeRequestsUsed, 1);
});

test("Tavily key alone cannot run while its free-only guard is off", async (context) => {
  withFetchMock(context, async () => {
    throw new Error("must not call Tavily when free-only guard is off");
  });
  const response = await handleFreeWebSearchRequest(request(), {
    JINA_READER_FREE_ONLY: "false",
    TAVILY_FREE_ONLY: "false",
    TAVILY_API_KEY: "tvly-free-test-key",
  });
  const payload = await response.json();
  assert.equal(payload.searchStatus, "needs_web_search");
  assert.deepEqual(payload.providersTried, []);
});

test("configured free Tavily Basic result is returned with one-credit accounting", async (context) => {
  withFetchMock(context, async (url, options) => {
    assert.equal(String(url), "https://api.tavily.com/search");
    const body = JSON.parse(options.body);
    assert.equal(body.search_depth, "basic");
    return Response.json({
      usage: { credits: 1 },
      results: [{
        title,
        url: "https://publisher.example/paper",
        raw_content: "Abstract This article studies legitimate businesses confiscated from mafia groups in Italy and their investment choices across sectors and territories. Introduction The article then presents data and methods.",
      }],
    });
  });
  const response = await handleFreeWebSearchRequest(request(), {
    JINA_READER_FREE_ONLY: "false",
    TAVILY_FREE_ONLY: "true",
    TAVILY_API_KEY: "tvly-free-test-key",
  });
  const payload = await response.json();
  assert.equal(payload.searchStatus, "found");
  assert.equal(payload.matchType, "free_web_search");
  assert.equal(payload.freeCreditsUsed, 1);
  assert.equal(payload.freeRequestsUsed, 1);
  assert.equal(payload.provider, "Tavily Basic");
});
