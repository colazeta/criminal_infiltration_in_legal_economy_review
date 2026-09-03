"use strict";

import assert from "node:assert/strict";
import test from "node:test";

import {
  BUDGET_DURABLE_OBJECT_NAME,
  PROVIDER_PROJECT_BUDGETS,
  reserveProjectProviderBudget,
} from "../src/provider-budget.js";

test("provider budgets stay below verified free allowances", () => {
  assert.equal(PROVIDER_PROJECT_BUDGETS.serper.maxRequests, 1000);
  assert.equal(PROVIDER_PROJECT_BUDGETS.exa.maxRequests, 500);
  assert.equal(PROVIDER_PROJECT_BUDGETS.exa.maxTheoreticalCostUsd, 3.5);
  assert.ok(PROVIDER_PROJECT_BUDGETS.exa.maxTheoreticalCostUsd < 20);
});

test("budget reservation uses the single persistent durable object namespace", async () => {
  let seenName = "";
  const env = {
    SUBMISSIONS: {
      getByName(name) {
        seenName = name;
        return {
          async fetch(url, options) {
            assert.equal(String(url), "https://submission.internal/provider-budget");
            const body = JSON.parse(options.body);
            assert.equal(body.provider, "serper");
            assert.equal(body.candidateId, "CAND-TEST-001");
            return Response.json({ allowed: true, provider: "serper", used: 1, limit: 1000, remaining: 999 });
          },
        };
      },
    },
  };
  const result = await reserveProjectProviderBudget(env, "serper", "CAND-TEST-001");
  assert.equal(seenName, BUDGET_DURABLE_OBJECT_NAME);
  assert.equal(result.allowed, true);
  assert.equal(result.remaining, 999);
});

test("budget reservation fails closed when coordination is unavailable", async () => {
  const result = await reserveProjectProviderBudget({}, "exa", "CAND-TEST-002");
  assert.equal(result.allowed, false);
  assert.equal(result.reason, "provider_budget_coordination_unavailable");
});
