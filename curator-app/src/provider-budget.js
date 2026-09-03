"use strict";

const PROVIDER_PROJECT_BUDGETS = Object.freeze({
  serper: Object.freeze({
    maxRequests: 1000,
    freeAllowanceBasis: "2,500 signup queries; project lifetime cap intentionally remains below the free grant.",
  }),
  exa: Object.freeze({
    maxRequests: 500,
    maxUnitCostUsd: 0.007,
    maxTheoreticalCostUsd: 3.5,
    freeAllowanceBasis: "$20 signup credit; Search-only cap remains far below the initial free credit at the verified $7/1k Search price.",
  }),
});

const BUDGET_DURABLE_OBJECT_NAME = "web-provider-budget-v1";

function budgetFor(providerId) {
  return PROVIDER_PROJECT_BUDGETS[String(providerId || "")] || null;
}

function durableStub(namespace, name) {
  if (!namespace) return null;
  if (typeof namespace.getByName === "function") return namespace.getByName(name);
  if (typeof namespace.idFromName === "function" && typeof namespace.get === "function") {
    return namespace.get(namespace.idFromName(name));
  }
  return null;
}

async function reserveProjectProviderBudget(env, providerId, candidateId = "") {
  const budget = budgetFor(providerId);
  if (!budget) {
    return { allowed: false, provider: providerId, reason: "provider_budget_unknown" };
  }
  const stub = durableStub(env?.SUBMISSIONS, BUDGET_DURABLE_OBJECT_NAME);
  if (!stub) {
    return {
      allowed: false,
      provider: providerId,
      limit: budget.maxRequests,
      reason: "provider_budget_coordination_unavailable",
    };
  }
  const response = await stub.fetch("https://submission.internal/provider-budget", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider: providerId, candidateId: String(candidateId || "").slice(0, 200) }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    return {
      allowed: false,
      provider: providerId,
      limit: budget.maxRequests,
      used: Number(payload.used || 0),
      remaining: Number(payload.remaining || 0),
      reason: payload.error?.code || "provider_budget_reservation_failed",
    };
  }
  return payload;
}

export {
  BUDGET_DURABLE_OBJECT_NAME,
  PROVIDER_PROJECT_BUDGETS,
  budgetFor,
  reserveProjectProviderBudget,
};
