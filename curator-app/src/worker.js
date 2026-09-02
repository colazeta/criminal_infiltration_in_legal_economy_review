"use strict";

import { DurableObject } from "cloudflare:workers";

import { handleEnrichmentRequest } from "./enrichment.js";
import { handleFreeWebSearchRequest } from "./free-web-search.js";
import { handleResolvedAbstractRequest } from "./resolved-abstract.js";
import worker, { SubmissionCoordinatorCore } from "./index.js";

const CURATOR_COMPONENT_ASSETS = new Set([
  "/curator-reading.js",
  "/curator-reading.css",
  "/curator-queue.js",
  "/curator-queue.css",
  "/curator-resolved-link.js",
]);

function componentLoaderSource() {
  return `\n(() => {\n  function load(src, marker) {\n    if (document.querySelector('script[data-' + marker + '=\"true\"]')) return;\n    const script = document.createElement(\"script\");\n    script.src = src;\n    script.defer = true;\n    script.dataset[marker.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] = \"true\";\n    document.head.append(script);\n  }\n  load(\"./curator-reading.js\", \"curator-reading\");\n  load(\"./curator-queue.js\", \"curator-queue\");\n  load(\"./curator-resolved-link.js\", \"curator-resolved-link\");\n})();\n`;
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

async function requireCuratorSession(request, env) {
  const sessionUrl = new URL("/api/session", request.url);
  const validationRequest = new Request(sessionUrl, {
    method: "GET",
    headers: request.headers,
  });
  return worker.fetch(validationRequest, env);
}

async function authenticatedEnrichment(request, env) {
  if (request.method !== "GET") {
    return new Response(JSON.stringify({ error: { code: "method_not_allowed", message: "Metodo non consentito." } }), {
      status: 405,
      headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  }
  const validation = await requireCuratorSession(request, env);
  if (!validation.ok) return validation;
  return handleEnrichmentRequest(request, env);
}

function validCandidateId(value) {
  return /^[A-Z0-9][A-Z0-9-]{2,59}$/.test(String(value || ""));
}

function cleanRetrievalValue(value) {
  const clean = String(value || "")
    .replace(/^<|>$/g, "")
    .replace(/^`|`$/g, "")
    .trim();
  return /^not resolved$/i.test(clean) ? "" : clean;
}

function safeHttpsUrl(value) {
  const clean = cleanRetrievalValue(value);
  if (!clean) return "";
  try {
    const url = new URL(clean);
    return url.protocol === "https:" ? url.toString() : "";
  } catch {
    return "";
  }
}

function parseMechanicalSection(source, heading) {
  const start = source.indexOf(heading);
  if (start < 0) return {};
  const remainder = source.slice(start + heading.length);
  const nextHeading = remainder.search(/\n##\s/);
  const section = nextHeading >= 0 ? remainder.slice(0, nextHeading) : remainder;
  const fields = {};
  for (const line of section.split("\n")) {
    const match = line.match(/^- ([^:]+):\s*(.*)$/);
    if (match) fields[match[1].trim()] = cleanRetrievalValue(match[2]);
  }
  return fields;
}

function parseRetrievalCoverage(body, candidateId) {
  const source = String(body || "");
  if (!source.includes(`<!-- curator-candidate:${candidateId} -->`)) return null;
  const fields = parseMechanicalSection(source, "## Retrieval coverage — mechanical");
  if (!Object.keys(fields).length) return null;
  const access = parseMechanicalSection(source, "## Access status — mechanical");
  return {
    candidateId,
    resolutionStatus: fields["Resolution status"] || "",
    bestUrl: safeHttpsUrl(fields["Best URL"]),
    bestUrlKind: fields["Best URL kind"] || "",
    fullTextUrl: safeHttpsUrl(fields["Direct full text"]),
    openAccessUrl: safeHttpsUrl(fields["Open-access location"]),
    landingUrl: safeHttpsUrl(fields["Landing page"]),
    doiUrl: safeHttpsUrl(fields["DOI URL"]),
    resolutionSources: fields["Resolver sources"] || "",
    matchMethod: fields["Match method"] || "",
    matchConfidence: fields["Match confidence"] || "",
    checkedAt: fields["Last checked"] || "",
    accessStatus: access["Access status"] || "",
    accessKind: access["Access kind"] || "",
    accessUrl: safeHttpsUrl(access["Access URL"]),
    accessEvidenceSource: access["Evidence source"] || "",
    accessEvidenceDetail: access["Evidence detail"] || "",
    accessCheckedAt: access["Last checked"] || "",
  };
}

async function authenticatedRetrieval(request, env) {
  if (request.method !== "GET") {
    return new Response(JSON.stringify({ error: { code: "method_not_allowed", message: "Metodo non consentito." } }), {
      status: 405,
      headers: { "Cache-Control": "no-store", "Content-Type": "application/json; charset=utf-8" },
    });
  }
  const validation = await requireCuratorSession(request, env);
  if (!validation.ok) return validation;

  const url = new URL(request.url);
  const candidateId = String(url.searchParams.get("candidate") || "").trim();
  const issueNumber = Number(url.searchParams.get("issue"));
  if (!validCandidateId(candidateId) || !Number.isInteger(issueNumber) || issueNumber <= 0) {
    return new Response(JSON.stringify({ error: { code: "invalid_retrieval_target", message: "Scheda di retrieval non valida." } }), {
      status: 400,
      headers: { "Cache-Control": "no-store", "Content-Type": "application/json; charset=utf-8" },
    });
  }

  const upstream = await fetch(
    `https://api.github.com/repos/${env.GITHUB_REPOSITORY}/issues/${issueNumber}`,
    {
      headers: {
        Accept: "application/vnd.github+json",
        "User-Agent": "criminal-infiltration-curator-retrieval",
        "X-GitHub-Api-Version": "2022-11-28",
      },
    },
  );
  if (!upstream.ok) {
    return new Response(JSON.stringify({ error: { code: "retrieval_record_unavailable", message: "Il record di retrieval non è disponibile." } }), {
      status: 502,
      headers: { "Cache-Control": "no-store", "Content-Type": "application/json; charset=utf-8" },
    });
  }
  const issue = await upstream.json();
  const retrieval = parseRetrievalCoverage(issue?.body, candidateId);
  if (!retrieval) {
    return new Response(JSON.stringify({ error: { code: "retrieval_record_missing", message: "La copertura di retrieval non è ancora materializzata." } }), {
      status: 404,
      headers: { "Cache-Control": "no-store", "Content-Type": "application/json; charset=utf-8" },
    });
  }
  return new Response(JSON.stringify(retrieval), {
    status: 200,
    headers: {
      "Cache-Control": "no-store",
      "Content-Type": "application/json; charset=utf-8",
      "Referrer-Policy": "no-referrer",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

async function authenticatedResolvedAbstract(request, env) {
  if (request.method !== "GET") {
    return new Response(JSON.stringify({ error: { code: "method_not_allowed", message: "Metodo non consentito." } }), {
      status: 405,
      headers: { "Cache-Control": "no-store", "Content-Type": "application/json; charset=utf-8" },
    });
  }
  const retrievalResponse = await authenticatedRetrieval(request, env);
  if (!retrievalResponse.ok) return retrievalResponse;
  const retrieval = await retrievalResponse.json();
  return handleResolvedAbstractRequest(request, retrieval);
}

async function authenticatedFreeWebSearch(request, env) {
  if (request.method !== "GET") {
    return new Response(JSON.stringify({ error: { code: "method_not_allowed", message: "Metodo non consentito." } }), {
      status: 405,
      headers: { "Cache-Control": "no-store", "Content-Type": "application/json; charset=utf-8" },
    });
  }
  const retrievalResponse = await authenticatedRetrieval(request, env);
  if (!retrievalResponse.ok) return retrievalResponse;
  return handleFreeWebSearchRequest(request, env);
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
    if (url.pathname === "/api/retrieval") {
      return authenticatedRetrieval(request, env);
    }
    if (url.pathname === "/api/resolved-abstract") {
      return authenticatedResolvedAbstract(request, env);
    }
    if (url.pathname === "/api/free-web-search") {
      return authenticatedFreeWebSearch(request, env);
    }
    return worker.fetch(request, env);
  },
};
