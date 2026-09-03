"use strict";

import assert from "node:assert/strict";
import test from "node:test";

import { providerReadiness } from "../src/provider-readiness.js";

function budgetNamespace(usage = {}) {
  return {
    getByName(name) {
      assert.equal(name, "web-provider-budget-v1");
      return {
        async fetch(url, options = {}) {
          assert.equal(String(url), "https://submission.internal/provider-budget-status");
          assert.equal(options.method, "GET");
          return Response.json({ usage });
        },
      };
    },
  };
}

test("readiness reports configured and guarded providers without external provider calls", async () => {
  const status = await providerReadiness({
    SUBMISSIONS: budgetNamespace({ serper: 12, exa: 3 }),
    JINA_READER_FREE_ONLY: "true",
    SERPER_FREE_ONLY: "true",
    EXA_FREE_ONLY: "true",
    TAVILY_FREE_ONLY: "true",
  });
  assert.equal(status.status, "ready");
  assert.equal(status.zeroSpendPolicy, "fail_closed");

  const jina = status.providers.find((provider) => provider.id === "jina_reader");
  assert.equal(jina.automaticEligible, true);
  assert.deepEqual(jina.blockingReasons, []);

  const serper = status.providers.find((provider) => provider.id === "serper");
  assert.equal(serper.automaticEligible, false);
  assert.ok(serper.blockingReasons.includes("api_key_missing"));
  assert.ok(serper.blockingReasons.includes("dedicated_free_account_not_attested"));
  assert.deepEqual(serper.budget, {
    used: 12,
    limit: 1000,
    remaining: 988,
    coordinated: true,
    maxTheoreticalCostUsd: 0,
  });

  const exa = status.providers.find((provider) => provider.id === "exa");
  assert.equal(exa.budget.used, 3);
  assert.equal(exa.budget.remaining, 497);
  assert.equal(exa.budget.maxTheoreticalCostUsd, 3.5);
});

test("dedicated free-account attestations plus keys make bounded discovery providers ready", async () => {
  const status = await providerReadiness({
    SUBMISSIONS: budgetNamespace(),
    JINA_READER_FREE_ONLY: "true",
    SERPER_FREE_ONLY: "true",
    SERPER_API_KEY: "serper-free-test",
    SERPER_DEDICATED_FREE_ACCOUNT: "true",
    EXA_FREE_ONLY: "true",
    EXA_API_KEY: "exa-free-test",
    EXA_DEDICATED_STARTER_ACCOUNT: "true",
  });
  for (const id of ["jina_reader", "serper", "exa"]) {
    const provider = status.providers.find((row) => row.id === id);
    assert.equal(provider.automaticEligible, true, id);
    assert.deepEqual(provider.blockingReasons, [], id);
  }
});

test("readiness does not reserve budget", async () => {
  let calls = 0;
  const namespace = {
    getByName() {
      return {
        async fetch(url, options = {}) {
          calls += 1;
          assert.equal(String(url), "https://submission.internal/provider-budget-status");
          assert.equal(options.method, "GET");
          return Response.json({ usage: { serper: 4, exa: 2 } });
        },
      };
    },
  };
  const status = await providerReadiness({ SUBMISSIONS: namespace, JINA_READER_FREE_ONLY: "true" });
  assert.equal(calls, 1);
  assert.equal(status.providers.find((row) => row.id === "serper").budget.used, 4);
  assert.equal(status.providers.find((row) => row.id === "exa").budget.used, 2);
});
