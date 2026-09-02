"use strict";

import assert from "node:assert/strict";
import test from "node:test";

import {
  extractAbstractFromDocument,
  extractDocumentTitle,
  resolveAbstractFromRetrieval,
  safePublicHttpsUrl,
} from "../src/resolved-abstract.js";

function withFetchMock(context, implementation) {
  const original = globalThis.fetch;
  context.after(() => {
    globalThis.fetch = original;
  });
  globalThis.fetch = implementation;
}

test("publisher citation metadata exposes an abstract", () => {
  const source = `<!doctype html><html><head>
    <meta name="citation_title" content="Bricks or cooks? Geographical and social determinants of mafia investment">
    <meta name="citation_abstract" content="This article studies legitimate businesses confiscated from mafia groups in Italy and examines their investment patterns across industries and places.">
  </head><body></body></html>`;
  assert.match(extractAbstractFromDocument(source), /^This article studies legitimate businesses/);
  assert.match(extractDocumentTitle(source), /^Bricks or cooks/);
});

test("full-text XML abstract is extracted without persisting markup", () => {
  const source = `<?xml version="1.0"?><article><front><article-meta>
    <title-group><article-title>Organised crime and companies</article-title></title-group>
    <abstract><p>We study how organised crime enters legitimate firms and affects their financing, survival and ownership structures.</p></abstract>
  </article-meta></front></article>`;
  assert.equal(
    extractAbstractFromDocument(source),
    "We study how organised crime enters legitimate firms and affects their financing, survival and ownership structures.",
  );
});

test("resolved-paper fallback uses a governed landing page and verifies title", async (context) => {
  withFetchMock(context, async (url) => {
    assert.equal(String(url), "https://publisher.example/article");
    return new Response(`<!doctype html><html><head>
      <meta name="citation_title" content="Criminal infiltration and companies">
      <meta name="citation_abstract" content="This study examines criminal infiltration in companies using administrative and judicial data on firm ownership and control.">
    </head></html>`, { headers: { "content-type": "text/html" } });
  });
  const result = await resolveAbstractFromRetrieval({
    title: "Criminal infiltration and companies",
    retrieval: {
      landingUrl: "https://publisher.example/article",
      bestUrl: "https://publisher.example/article",
    },
  });
  assert.equal(result.matchType, "resolved_url");
  assert.equal(result.abstractSource, "publisher.example");
  assert.match(result.abstract, /^This study examines criminal infiltration/);
});

test("resolved-paper fallback rejects an unrelated landing page", async (context) => {
  withFetchMock(context, async () => new Response(`<!doctype html><html><head>
    <meta name="citation_title" content="Marine biology and coral reefs">
    <meta name="citation_abstract" content="This study examines coral reef ecosystems, marine biodiversity, fish populations and ecological change across tropical regions.">
  </head></html>`, { headers: { "content-type": "text/html" } }));
  const result = await resolveAbstractFromRetrieval({
    title: "Mafia infiltration and ownership dynamics in Italian companies",
    retrieval: { landingUrl: "https://publisher.example/wrong" },
  });
  assert.equal(result.abstract, "");
  assert.equal(result.matchType, "resolved_url_none");
});

test("resolved-paper fetch refuses local and private literal targets", () => {
  assert.equal(safePublicHttpsUrl("http://publisher.example/article"), "");
  assert.equal(safePublicHttpsUrl("https://localhost/article"), "");
  assert.equal(safePublicHttpsUrl("https://127.0.0.1/article"), "");
  assert.equal(safePublicHttpsUrl("https://10.0.0.5/article"), "");
  assert.equal(safePublicHttpsUrl("https://192.168.1.2/article"), "");
  assert.equal(safePublicHttpsUrl("https://publisher.example/article"), "https://publisher.example/article");
});
