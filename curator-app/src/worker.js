"use strict";

import { DurableObject } from "cloudflare:workers";

import { handleEnrichmentRequest } from "./enrichment.js";
import worker, { SubmissionCoordinatorCore } from "./index.js";

const READING_ASSETS = new Set(["/curator-reading.js", "/curator-reading.css"]);

function readingLoaderSource() {
  return `\n(() => {\n  if (!document.querySelector('script[data-curator-reading="true"]')) {\n    const script = document.createElement("script");\n    script.src = "./curator-reading.js";\n    script.defer = true;\n    script.dataset.curatorReading = "true";\n    document.head.append(script);\n  }\n})();\n`;
}

async function serveReadingAsset(request, env) {
  if (!env.ASSETS || typeof env.ASSETS.fetch !== "function") {
    return new Response("Asset non disponibile.", { status: 503 });
  }
  const response = await env.ASSETS.fetch(request);
  const headers = new Headers(response.headers);
  headers.set("Cache-Control", "no-cache");
  headers.set("Referrer-Policy", "no-referrer");
  headers.set("X-Content-Type-Options", "nosniff");
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

async function enrichedConfig(request, env) {
  const response = await worker.fetch(request, env);
  if (!response.ok) return response;
  const headers = new Headers(response.headers);
  return new Response(`${await response.text()}${readingLoaderSource()}`, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

async function authenticatedEnrichment(request, env) {
  if (request.method !== "GET") {
    return new Response(JSON.stringify({ error: { code: "method_not_allowed", message: "Metodo non consentito." } }), {
      status: 405,
      headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  }
  const sessionUrl = new URL("/api/session", request.url);
  const validationRequest = new Request(sessionUrl, {
    method: "GET",
    headers: request.headers,
  });
  const validation = await worker.fetch(validationRequest, env);
  if (!validation.ok) return validation;
  return handleEnrichmentRequest(request, env);
}

export class SubmissionCoordinator extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.core = new SubmissionCoordinatorCore(ctx, env);
  }

  fetch(request) {
    return this.core.fetch(request);
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && READING_ASSETS.has(url.pathname)) {
      return serveReadingAsset(request, env);
    }
    if (url.pathname === "/curator-config.js" && request.method === "GET") {
      return enrichedConfig(request, env);
    }
    if (url.pathname === "/api/enrichment") {
      return authenticatedEnrichment(request, env);
    }
    return worker.fetch(request, env);
  },
};
