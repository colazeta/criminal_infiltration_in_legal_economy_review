"use strict";

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  WEB_CAPABILITY_REGISTRY,
  readKnownUrlWithJina,
  resolveFreeWebCapabilities,
  webCapabilityManifest,
} from "../src/web-capability-resolver.js";

function withFetchMock(context, implementation) {
  const original = globalThis.fetch;
  context.after(() => {
    globalThis.fetch = original;
  });
  globalThis.fetch = implementation;
}

function budgetNamespace({ deny = new Set() } = {}) {
  const counts = new Map();
  return {
    getByName(name) {
      assert.equal(name, "web-provider-budget-v1");
      return {
        async fetch(url, options) {
          assert.equal(String(url), "https://submission.internal/provider-budget");
          const payload = JSON.parse(options.body);
          if (deny.has(payload.provider)) {
            return Response.json({
              allowed: false,
              provider: payload.provider,
              used: 1000,
              limit: 1000,
              remaining: 0,
              error: { code: "provider_project_budget_exhausted" },
            }, { status: 429 });
          }
          const used = (counts.get(payload.provider) || 0) + 1;
          counts.set(payload.provider, used);
          return Response.json({ allowed: true, provider: payload.provider, used, limit: 1000, remaining: 1000 - used });
        },
      };
    },
  };
}

const title = "Bricks or cooks? Geographical and social determinants of the investment choices of mafia-type organized crime";
const doi = "10.1177/17488958241293927";
const abstractText = "Abstract This article studies legitimate businesses confiscated from mafia groups in Italy and explains geographic and social determinants of investment choices across sectors and territories. Introduction The article then presents data and methods.";

test("runtime provider registry stays aligned with the governed ontology registry", async () => {
  const governed = JSON.parse(await readFile(new URL("../../ontology/providers/web-capabilities.json", import.meta.url), "utf8"));
  assert.deepEqual(
    WEB_CAPABILITY_REGISTRY.map(({ id, layer }) => ({ id, layer })),
    governed.providers.map(({ id, layer }) => ({ id, layer })),
  );
});

test("credit providers require both free-only and dedicated-account guards", () => {
  const guarded = webCapabilityManifest({
    JINA_READER_FREE_ONLY: "true",
    TAVILY_FREE_ONLY: "true",
    TAVILY_API_KEY: "tvly-free-test-key",
    EXA_FREE_ONLY: "true",
    EXA_API_KEY: "exa-test-key",
    SERPER_FREE_ONLY: "true",
    SERPER_API_KEY: "serper-test-key",
  });
  assert.deepEqual(
    guarded.filter((provider) => provider.automaticEligible).map((provider) => provider.id),
    ["jina_reader", "tavily_basic"],
  );

  const ready = webCapabilityManifest({
    JINA_READER_FREE_ONLY: "true",
    TAVILY_FREE_ONLY: "true",
    TAVILY_API_KEY: "tvly-free-test-key",
    SERPER_FREE_ONLY: "true",
    SERPER_DEDICATED_FREE_ACCOUNT: "true",
    SERPER_API_KEY: "serper-test-key",
    EXA_FREE_ONLY: "true",
    EXA_DEDICATED_STARTER_ACCOUNT: "true",
    EXA_API_KEY: "exa-test-key",
  });
  assert.deepEqual(
    ready.filter((provider) => provider.automaticEligible).map((provider) => provider.id),
    ["jina_reader", "serper", "exa", "tavily_basic"],
  );
});

test("Jina Reader can resolve a DOI page before any search credit is consumed", async (context) => {
  withFetchMock(context, async (url) => {
    assert.equal(String(url), `https://r.jina.ai/https://doi.org/${doi}`);
    return new Response(`Title: ${title}\nURL Source: https://doi.org/${doi}\n\n${abstractText}`, { status: 200 });
  });
  const result = await resolveFreeWebCapabilities({
    title,
    doi,
    year: "2024",
    candidateId: "CAND-TEST-001",
    env: { JINA_READER_FREE_ONLY: "true" },
  });
  assert.equal(result.searchStatus, "found");
  assert.equal(result.result.provider, "Jina Reader");
  assert.equal(result.result.matchType, "free_page_reader");
  assert.equal(result.freeCreditsUsed, 0);
  assert.equal(result.freeRequestsUsed, 1);
  assert.deepEqual(result.providersTried, ["Jina Reader"]);
});

test("Jina Reader rejects a clearly mismatched resolved page", async (context) => {
  withFetchMock(context, async () => new Response(
    "Title: Completely unrelated biomedical trial\n\nAbstract This is a long abstract about an unrelated clinical intervention and patient outcomes that should never be attached to the requested organised crime paper. Introduction Methods follow.",
    { status: 200 },
  ));
  const result = await readKnownUrlWithJina({ title, doi });
  assert.equal(result, null);
});

test("Serper uses one bounded discovery query then delegates page reading to Jina", async (context) => {
  const calls = [];
  withFetchMock(context, async (url, options = {}) => {
    calls.push(String(url));
    if (String(url) === `https://r.jina.ai/https://doi.org/${doi}`) {
      return new Response(`Title: ${title}\n\nNo abstract exposed here.`, { status: 200 });
    }
    if (String(url) === "https://google.serper.dev/search") {
      assert.equal(options.headers["X-API-KEY"], "serper-free-key");
      const body = JSON.parse(options.body);
      assert.equal(body.num, 5);
      assert.match(body.q, /Exact scholarly publication/);
      return Response.json({ organic: [{ title, link: "https://repository.example/paper", snippet: `DOI ${doi}` }] });
    }
    if (String(url) === "https://r.jina.ai/https://repository.example/paper") {
      return new Response(`Title: ${title}\nURL Source: https://repository.example/paper\n\n${abstractText}`, { status: 200 });
    }
    throw new Error(`unexpected fetch ${url}`);
  });

  const result = await resolveFreeWebCapabilities({
    title,
    doi,
    year: "2024",
    candidateId: "CAND-TEST-002",
    env: {
      SUBMISSIONS: budgetNamespace(),
      JINA_READER_FREE_ONLY: "true",
      SERPER_FREE_ONLY: "true",
      SERPER_DEDICATED_FREE_ACCOUNT: "true",
      SERPER_API_KEY: "serper-free-key",
    },
  });
  assert.equal(result.result.provider, "Jina Reader");
  assert.equal(result.result.matchType, "discovered_page_reader");
  assert.deepEqual(calls, [
    `https://r.jina.ai/https://doi.org/${doi}`,
    "https://google.serper.dev/search",
    "https://r.jina.ai/https://repository.example/paper",
  ]);
  const usage = result.providerUsage.find((row) => row.provider === "serper");
  assert.equal(usage.quotaUnit, "query");
  assert.equal(usage.freeQuotaUsed, 1);
  assert.equal(usage.projectBudget.allowed, true);
});

test("Exa is Search-only, bounded, then delegates the discovered page to Jina", async (context) => {
  const calls = [];
  withFetchMock(context, async (url, options = {}) => {
    calls.push(String(url));
    if (String(url) === `https://r.jina.ai/https://doi.org/${doi}`) {
      return new Response(`Title: ${title}\n\nNo abstract exposed here.`, { status: 200 });
    }
    if (String(url) === "https://api.exa.ai/search") {
      assert.equal(options.headers["x-api-key"], "exa-starter-key");
      const body = JSON.parse(options.body);
      assert.equal(body.type, "fast");
      assert.equal(body.numResults, 5);
      assert.equal(body.category, "research paper");
      assert.equal(Object.hasOwn(body, "contents"), false);
      assert.equal(Object.hasOwn(body, "outputSchema"), false);
      return Response.json({
        costDollars: { total: 0.007 },
        results: [{ title, url: "https://author.example/paper" }],
      });
    }
    if (String(url) === "https://r.jina.ai/https://author.example/paper") {
      return new Response(`Title: ${title}\nURL Source: https://author.example/paper\n\n${abstractText}`, { status: 200 });
    }
    throw new Error(`unexpected fetch ${url}`);
  });

  const result = await resolveFreeWebCapabilities({
    title,
    doi,
    year: "2024",
    candidateId: "CAND-TEST-003",
    env: {
      SUBMISSIONS: budgetNamespace(),
      JINA_READER_FREE_ONLY: "true",
      EXA_FREE_ONLY: "true",
      EXA_DEDICATED_STARTER_ACCOUNT: "true",
      EXA_API_KEY: "exa-starter-key",
    },
  });
  assert.equal(result.result.provider, "Jina Reader");
  assert.equal(calls.includes("https://api.exa.ai/search"), true);
  const usage = result.providerUsage.find((row) => row.provider === "exa");
  assert.equal(usage.quotaUnit, "usd_credit");
  assert.equal(usage.freeQuotaUsed, 0.007);
  assert.equal(usage.projectBudget.allowed, true);
});

test("an exhausted persistent project budget prevents the external provider call", async (context) => {
  withFetchMock(context, async (url) => {
    if (String(url).startsWith("https://r.jina.ai/")) return new Response("Title: requested paper\nNo abstract.", { status: 200 });
    throw new Error("Serper must not be called after budget exhaustion");
  });
  const result = await resolveFreeWebCapabilities({
    title,
    doi,
    year: "2024",
    candidateId: "CAND-TEST-004",
    env: {
      SUBMISSIONS: budgetNamespace({ deny: new Set(["serper"]) }),
      JINA_READER_FREE_ONLY: "true",
      SERPER_FREE_ONLY: "true",
      SERPER_DEDICATED_FREE_ACCOUNT: "true",
      SERPER_API_KEY: "serper-free-key",
    },
  });
  assert.equal(result.providersTried.includes("Serper"), false);
  assert.match(result.providerErrors.join(" "), /provider_project_budget_exhausted/);
});

test("Tavily Basic remains the final content-search fallback", async (context) => {
  let calls = 0;
  withFetchMock(context, async (url, options = {}) => {
    calls += 1;
    assert.equal(String(url), "https://api.tavily.com/search");
    const body = JSON.parse(options.body);
    assert.equal(body.search_depth, "basic");
    assert.equal(body.auto_parameters, false);
    return Response.json({
      usage: { credits: 1 },
      results: [{ title, url: "https://publisher.example/paper", raw_content: abstractText }],
    });
  });
  const result = await resolveFreeWebCapabilities({
    title,
    doi,
    year: "2024",
    env: {
      JINA_READER_FREE_ONLY: "false",
      TAVILY_FREE_ONLY: "true",
      TAVILY_API_KEY: "tvly-free-test-key",
    },
  });
  assert.equal(calls, 1);
  assert.equal(result.result.provider, "Tavily Basic");
  assert.equal(result.freeCreditsUsed, 1);
  assert.equal(result.freeRequestsUsed, 1);
});

test("with no free-only guards the resolver makes no external request", async (context) => {
  withFetchMock(context, async () => {
    throw new Error("no provider should run");
  });
  const result = await resolveFreeWebCapabilities({ title, doi, year: "2024", env: {} });
  assert.equal(result.searchStatus, "needs_web_search");
  assert.deepEqual(result.providersTried, []);
  assert.equal(result.freeCreditsUsed, 0);
  assert.equal(result.freeRequestsUsed, 0);
});
