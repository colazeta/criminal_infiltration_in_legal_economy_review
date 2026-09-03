"use strict";

import { readProjectProviderBudgets } from "./provider-budget.js";
import { webCapabilityManifest } from "./web-capability-resolver.js";

function present(value) {
  return Boolean(String(value || "").trim());
}

function trueFlag(value) {
  return String(value || "").trim().toLowerCase() === "true";
}

function blockingReasons(provider, env = {}) {
  const reasons = [];
  if (!provider.implemented) reasons.push("adapter_not_implemented");
  if (!provider.automaticAllowed) reasons.push("automatic_use_not_allowed");
  if (!trueFlag(env?.[provider.guard])) reasons.push("free_only_guard_disabled");

  if (provider.id === "tavily_basic" && !present(env?.TAVILY_API_KEY)) {
    reasons.push("api_key_missing");
  }
  if (provider.id === "serper") {
    if (!present(env?.SERPER_API_KEY)) reasons.push("api_key_missing");
    if (!trueFlag(env?.SERPER_DEDICATED_FREE_ACCOUNT)) reasons.push("dedicated_free_account_not_attested");
  }
  if (provider.id === "exa") {
    if (!present(env?.EXA_API_KEY)) reasons.push("api_key_missing");
    if (!trueFlag(env?.EXA_DEDICATED_STARTER_ACCOUNT)) reasons.push("starter_free_account_not_attested");
  }
  if (provider.id === "firecrawl" && !present(env?.FIRECRAWL_API_KEY) && !trueFlag(env?.FIRECRAWL_KEYLESS_CONFIRMED)) {
    reasons.push("free_execution_not_configured");
  }
  if (provider.id === "cloudflare_browser_run" && !env?.BROWSER) {
    reasons.push("browser_binding_missing");
  }
  return [...new Set(reasons)];
}

async function providerReadiness(env = {}) {
  const [manifest, budgets] = await Promise.all([
    Promise.resolve(webCapabilityManifest(env)),
    readProjectProviderBudgets(env),
  ]);
  const providers = manifest.map((provider) => {
    const budget = budgets[provider.id] || null;
    const reasons = blockingReasons(provider, env);
    return {
      id: provider.id,
      label: provider.label,
      layer: provider.layer,
      capabilities: provider.capabilities,
      mode: provider.mode,
      implemented: provider.implemented,
      automaticAllowed: provider.automaticAllowed,
      configured: provider.configured,
      automaticEligible: provider.automaticEligible,
      blockingReasons: reasons,
      budget: budget ? {
        used: budget.used,
        limit: budget.limit,
        remaining: budget.remaining,
        coordinated: budget.coordinated,
        maxTheoreticalCostUsd: budget.maxTheoreticalCostUsd,
      } : null,
    };
  });
  return {
    status: providers.some((provider) => provider.automaticEligible) ? "ready" : "guarded",
    zeroSpendPolicy: "fail_closed",
    providers,
  };
}

async function handleProviderReadinessRequest(request, env = {}) {
  if (request.method !== "GET") {
    return Response.json({ error: { code: "method_not_allowed" } }, { status: 405 });
  }
  return Response.json(await providerReadiness(env), {
    status: 200,
    headers: {
      "Cache-Control": "no-store",
      "Referrer-Policy": "no-referrer",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

export { blockingReasons, handleProviderReadinessRequest, providerReadiness };
