"use strict";

import { DurableObject } from "cloudflare:workers";

import { handleEnrichmentRequest } from "./enrichment.js";
import worker, { SubmissionCoordinatorCore } from "./index.js";

const CURATOR_COMPONENT_ASSETS = new Set([
  "/curator-reading.js",
  "/curator-reading.css",
  "/curator-queue.js",
  "/curator-queue.css",
]);

function componentLoaderSource() {
  return `\n(() => {\n  function load(src, marker) {\n    if (document.querySelector('script[data-' + marker + '=\"true\"]')) return;\n    const script = document.createElement(\"script\");\n    script.src = src;\n    script.defer = true;\n    script.dataset[marker.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] = \"true\";\n    document.head.append(script);\n  }\n  load(\"./curator-reading.js\", \"curator-reading\");\n  load(\"./curator-queue.js\", \"curator-queue\");\n})();\n`;
}

async function serveCuratorComponentAsset(request, env) {
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
  return new Response(`${await response.text()}${componentLoaderSource()}`, {
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
    if (request.method === "GET" && CURATOR_COMPONENT_ASSETS.has(url.pathname)) {
      return serveCuratorComponentAsset(request, env);
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
