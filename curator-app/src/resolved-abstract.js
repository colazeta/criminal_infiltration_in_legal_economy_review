"use strict";

const MAX_DOCUMENT_LENGTH = 2_000_000;
const MAX_ABSTRACT_LENGTH = 12_000;
const MIN_ABSTRACT_LENGTH = 60;

function cleanText(value, maximum = MAX_ABSTRACT_LENGTH) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, maximum);
}

function decodeEntities(value) {
  return String(value || "")
    .replace(/&#x([0-9a-f]+);/gi, (_, code) => String.fromCodePoint(Number.parseInt(code, 16)))
    .replace(/&#([0-9]+);/g, (_, code) => String.fromCodePoint(Number.parseInt(code, 10)))
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&quot;/gi, '"')
    .replace(/&apos;/gi, "'")
    .replace(/&#39;/gi, "'")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">");
}

function stripMarkup(value, maximum = MAX_ABSTRACT_LENGTH) {
  return cleanText(
    decodeEntities(String(value || ""))
      .replace(/<script\b[\s\S]*?<\/script>/gi, " ")
      .replace(/<style\b[\s\S]*?<\/style>/gi, " ")
      .replace(/<[^>]+>/g, " "),
    maximum,
  );
}

function normaliseTitle(value) {
  return cleanText(value, 1000)
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function titleTokens(value) {
  return new Set(normaliseTitle(value).split(" ").filter((token) => token.length > 2));
}

function titleSimilarity(left, right) {
  const a = titleTokens(left);
  const b = titleTokens(right);
  if (!a.size || !b.size) return 0;
  let overlap = 0;
  for (const token of a) if (b.has(token)) overlap += 1;
  return (2 * overlap) / (a.size + b.size);
}

function attributes(tag) {
  const result = {};
  const pattern = /([:\w.-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))/g;
  for (const match of String(tag || "").matchAll(pattern)) {
    result[match[1].toLowerCase()] = decodeEntities(match[2] ?? match[3] ?? match[4] ?? "");
  }
  return result;
}

function usableAbstract(value) {
  const text = stripMarkup(value);
  return text.length >= MIN_ABSTRACT_LENGTH ? text : "";
}

function metaValues(source) {
  const preferred = new Map();
  const generic = new Map();
  const preferredKeys = new Set([
    "citation_abstract",
    "dc.description",
    "dcterms.abstract",
    "dcterms.description",
    "eprints.abstract",
    "bepress_citation_abstract",
    "abstract",
  ]);
  const genericKeys = new Set(["description", "og:description", "twitter:description"]);
  for (const match of String(source || "").matchAll(/<meta\b[^>]*>/gi)) {
    const fields = attributes(match[0]);
    const key = String(fields.name || fields.property || fields.itemprop || "").toLowerCase();
    const content = fields.content || "";
    if (!key || !content) continue;
    if (preferredKeys.has(key) && !preferred.has(key)) preferred.set(key, content);
    if (genericKeys.has(key) && !generic.has(key)) generic.set(key, content);
  }
  return { preferred, generic };
}

function jsonLdCandidates(value) {
  const results = [];
  const visit = (node) => {
    if (!node || typeof node !== "object") return;
    if (Array.isArray(node)) {
      for (const item of node) visit(item);
      return;
    }
    for (const key of ["abstract", "description"]) {
      if (typeof node[key] === "string") results.push(node[key]);
    }
    if (node["@graph"]) visit(node["@graph"]);
    if (node.mainEntity) visit(node.mainEntity);
  };
  visit(value);
  return results;
}

function extractJsonLdAbstract(source) {
  const pattern = /<script\b[^>]*type\s*=\s*["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi;
  for (const match of String(source || "").matchAll(pattern)) {
    try {
      const payload = JSON.parse(decodeEntities(match[1]).trim());
      for (const candidate of jsonLdCandidates(payload)) {
        const abstract = usableAbstract(candidate);
        if (abstract) return abstract;
      }
    } catch {
      // Invalid JSON-LD is ignored; other document signals can still be used.
    }
  }
  return "";
}

function extractXmlAbstract(source) {
  const patterns = [
    /<(?:jats:)?abstract\b[^>]*>([\s\S]*?)<\/(?:jats:)?abstract>/i,
    /<div\b[^>]*(?:class|id)\s*=\s*["'][^"']*abstract[^"']*["'][^>]*>([\s\S]*?)<\/div>/i,
    /<section\b[^>]*(?:class|id)\s*=\s*["'][^"']*abstract[^"']*["'][^>]*>([\s\S]*?)<\/section>/i,
  ];
  for (const pattern of patterns) {
    const match = String(source || "").match(pattern);
    const abstract = usableAbstract(match?.[1] || "");
    if (abstract) return abstract;
  }
  return "";
}

function extractAbstractFromDocument(source) {
  const meta = metaValues(source);
  for (const value of meta.preferred.values()) {
    const abstract = usableAbstract(value);
    if (abstract) return abstract;
  }
  const xml = extractXmlAbstract(source);
  if (xml) return xml;
  const jsonLd = extractJsonLdAbstract(source);
  if (jsonLd) return jsonLd;
  for (const value of meta.generic.values()) {
    const abstract = usableAbstract(value);
    if (abstract) return abstract;
  }
  return "";
}

function extractDocumentTitle(source) {
  for (const match of String(source || "").matchAll(/<meta\b[^>]*>/gi)) {
    const fields = attributes(match[0]);
    const key = String(fields.name || fields.property || fields.itemprop || "").toLowerCase();
    if (!["citation_title", "dc.title", "dcterms.title", "og:title"].includes(key)) continue;
    const title = stripMarkup(fields.content || "", 1000);
    if (title) return title;
  }
  const title = String(source || "").match(/<title\b[^>]*>([\s\S]*?)<\/title>/i)?.[1] || "";
  return stripMarkup(title, 1000);
}

function safePublicHttpsUrl(value) {
  try {
    const url = new URL(String(value || ""));
    if (url.protocol !== "https:") return "";
    const host = url.hostname.toLowerCase();
    if (!host || host === "localhost" || host.endsWith(".localhost") || host.endsWith(".local")) return "";
    if (host.includes(":")) return "";
    const ipv4 = host.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
    if (ipv4) {
      const octets = ipv4.slice(1).map(Number);
      if (octets.some((value) => value > 255)) return "";
      if (
        octets[0] === 10 || octets[0] === 127 || octets[0] === 0 ||
        (octets[0] === 169 && octets[1] === 254) ||
        (octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31) ||
        (octets[0] === 192 && octets[1] === 168)
      ) return "";
    }
    return url.toString();
  } catch {
    return "";
  }
}

function looksLikePdf(url) {
  try {
    const parsed = new URL(url);
    return parsed.pathname.toLowerCase().endsWith(".pdf") || /(?:^|[?&])download=(?:pdf|1)(?:&|$)/i.test(parsed.search);
  } catch {
    return false;
  }
}

function retrievalUrls(retrieval) {
  const ordered = [
    retrieval?.landingUrl,
    retrieval?.openAccessUrl,
    retrieval?.fullTextUrl,
    retrieval?.bestUrl,
  ];
  const seen = new Set();
  const result = [];
  for (const value of ordered) {
    const url = safePublicHttpsUrl(value);
    if (!url || seen.has(url) || looksLikePdf(url) || new URL(url).hostname.toLowerCase() === "doi.org") continue;
    seen.add(url);
    result.push(url);
  }
  return result.slice(0, 4);
}

async function fetchResolvedDocument(url) {
  const response = await fetch(url, {
    redirect: "follow",
    headers: {
      Accept: "text/html,application/xhtml+xml,application/xml,text/xml;q=0.9,*/*;q=0.2",
      Range: `bytes=0-${MAX_DOCUMENT_LENGTH - 1}`,
      "User-Agent": "criminal-infiltration-curator/1.0",
    },
  });
  if (!response.ok) return { status: "unavailable" };
  const contentType = String(response.headers.get("content-type") || "").toLowerCase();
  if (contentType.includes("pdf") || contentType.includes("octet-stream")) return { status: "unsupported" };
  const source = (await response.text()).slice(0, MAX_DOCUMENT_LENGTH);
  return {
    status: "ok",
    source,
    url: safePublicHttpsUrl(response.url) || url,
  };
}

async function resolveAbstractFromRetrieval({ title, retrieval }) {
  const requestedTitle = cleanText(title, 1000);
  const urls = retrievalUrls(retrieval);
  let successfulDocument = false;
  for (const url of urls) {
    let document;
    try {
      document = await fetchResolvedDocument(url);
    } catch {
      continue;
    }
    if (document.status !== "ok") continue;
    successfulDocument = true;
    const abstract = extractAbstractFromDocument(document.source);
    if (!abstract) continue;
    const matchedTitle = extractDocumentTitle(document.source);
    const score = matchedTitle ? titleSimilarity(requestedTitle, matchedTitle) : 1;
    if (matchedTitle && score < 0.72) continue;
    let source = "Paper risolto";
    try {
      source = new URL(document.url).hostname.replace(/^www\./, "");
    } catch {
      // Keep the generic source label.
    }
    return {
      abstract,
      abstractSource: source,
      articleUrl: document.url,
      matchedTitle,
      matchedYear: null,
      matchedDoi: "",
      matchType: "resolved_url",
      matchScore: Number(score.toFixed(3)),
    };
  }
  return {
    abstract: "",
    abstractSource: "",
    articleUrl: safePublicHttpsUrl(retrieval?.bestUrl) || "",
    matchedTitle: "",
    matchedYear: null,
    matchedDoi: "",
    matchType: successfulDocument ? "resolved_url_none" : "unavailable",
    matchScore: 0,
  };
}

function json(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Cache-Control": "no-store",
      "Content-Type": "application/json; charset=utf-8",
      "Referrer-Policy": "no-referrer",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

async function handleResolvedAbstractRequest(request, retrieval) {
  const url = new URL(request.url);
  const title = cleanText(url.searchParams.get("title"), 1000);
  if (!title) return json({ error: { code: "title_required", message: "Titolo mancante." } }, 400);
  const result = await resolveAbstractFromRetrieval({ title, retrieval });
  return json(result);
}

export {
  extractAbstractFromDocument,
  extractDocumentTitle,
  handleResolvedAbstractRequest,
  resolveAbstractFromRetrieval,
  safePublicHttpsUrl,
  titleSimilarity,
};
