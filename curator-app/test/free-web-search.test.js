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

test("free web endpoint makes no external request without a Tavily free key", async (context) => {
  withFetchMock(context, async () => {
    throw new Error("must not call a web provider without a configured free key");
  });
  const response = await handleFreeWebSearchRequest(request(), { TAVILY_FREE_ONLY: "true" });
  assert.equal(response.status, 200);
  const payload = await response.json();
  assert.equal(payload.searchStatus, "needs_web_search");
  assert.equal(payload.matchType, "needs_web_search");
  assert.deepEqual(payload.providersTried, []);
});

test("free web endpoint refuses to run if the runtime free-only guard is off", async (context) => {
  withFetchMock(context, async () => {
    throw new Error("must not call Tavily when free-only guard is off");
  });
  const response = await handleFreeWebSearchRequest(request(), {
    TAVILY_FREE_ONLY: "false",
    TAVILY_API_KEY: "tvly-free-test-key",
  });
  const payload = await response.json();
  assert.equal(payload.searchStatus, "needs_web_search");
  assert.match(payload.providerErrors.join(" "), /free-only guard/);
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
    TAVILY_FREE_ONLY: "true",
    TAVILY_API_KEY: "tvly-free-test-key",
  });
  const payload = await response.json();
  assert.equal(payload.searchStatus, "found");
  assert.equal(payload.matchType, "free_web_search");
  assert.equal(payload.freeCreditsUsed, 1);
  assert.equal(payload.provider, "Tavily Basic");
});
