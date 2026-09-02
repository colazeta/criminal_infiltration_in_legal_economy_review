"use strict";

import assert from "node:assert/strict";
import test from "node:test";

import {
  enrichCandidate,
  reconstructAbstract,
  stripJats,
  titleSimilarity,
} from "../src/enrichment.js";

function withFetchMock(context, implementation) {
  const original = globalThis.fetch;
  context.after(() => {
    globalThis.fetch = original;
  });
  globalThis.fetch = implementation;
}

test("OpenAlex inverted abstracts are reconstructed in word order", () => {
  const abstract = reconstructAbstract({
    organised: [2],
    Firms: [0],
    face: [1],
    crime: [3],
  });
  assert.equal(abstract, "Firms face organised crime");
});

test("Crossref JATS abstracts are converted to readable text", () => {
  assert.equal(
    stripJats("<jats:p>Organised <jats:italic>crime</jats:italic> enters firms.</jats:p>"),
    "Organised crime enters firms.",
  );
});

test("title similarity rewards the same bibliographic work", () => {
  const score = titleSimilarity(
    "Bricks or cooks? Geographical and social determinants of the investment choices of mafia-type organized crime",
    "Bricks or cooks: geographical and social determinants of the investment choices of mafia type organized crime",
  );
  assert.ok(score > 0.95);
  assert.ok(titleSimilarity("Mafia infiltration in firms", "Marine biology and coral reefs") < 0.2);
});

test("DOI enrichment prefers a verified OpenAlex abstract", async (context) => {
  withFetchMock(context, async (url) => {
    const value = String(url);
    if (value.startsWith("https://api.openalex.org/works/https://doi.org/10.1000/example")) {
      return Response.json({
        doi: "https://doi.org/10.1000/example",
        display_name: "Organised crime and firm ownership",
        publication_year: 2025,
        abstract_inverted_index: {
          Organised: [0],
          crime: [1],
          affects: [2],
          ownership: [3],
        },
        primary_location: { landing_page_url: "https://publisher.example/article" },
        open_access: { oa_url: null },
      });
    }
    if (value.startsWith("https://api.crossref.org/works/10.1000%2Fexample")) {
      return Response.json({ message: { DOI: "10.1000/example", title: ["Organised crime and firm ownership"] } });
    }
    throw new Error(`Unexpected fetch: ${value}`);
  });

  const result = await enrichCandidate({
    title: "Organised crime and firm ownership",
    doi: "10.1000/example",
    year: "2025",
  });
  assert.equal(result.abstract, "Organised crime affects ownership");
  assert.equal(result.abstractSource, "OpenAlex");
  assert.equal(result.matchType, "doi");
  assert.equal(result.articleUrl, "https://publisher.example/article");
});

test("Crossref abstract is used when the DOI match in OpenAlex has no abstract", async (context) => {
  withFetchMock(context, async (url) => {
    const value = String(url);
    if (value.startsWith("https://api.openalex.org/works/https://doi.org/10.1000/fallback")) {
      return Response.json({
        doi: "https://doi.org/10.1000/fallback",
        display_name: "Criminal infiltration and companies",
        publication_year: 2024,
        abstract_inverted_index: null,
        primary_location: { landing_page_url: "https://publisher.example/fallback" },
        open_access: { oa_url: null },
      });
    }
    if (value.startsWith("https://api.crossref.org/works/10.1000%2Ffallback")) {
      return Response.json({
        message: {
          DOI: "10.1000/fallback",
          title: ["Criminal infiltration and companies"],
          abstract: "<jats:p>This study examines criminal infiltration in companies.</jats:p>",
          URL: "https://doi.org/10.1000/fallback",
          published: { "date-parts": [[2024]] },
        },
      });
    }
    throw new Error(`Unexpected fetch: ${value}`);
  });

  const result = await enrichCandidate({
    title: "Criminal infiltration and companies",
    doi: "https://doi.org/10.1000/fallback",
    year: "2024",
  });
  assert.equal(result.abstractSource, "Crossref");
  assert.equal(result.abstract, "This study examines criminal infiltration in companies.");
});

test("title-year fallback refuses an unrelated bibliographic match", async (context) => {
  withFetchMock(context, async (url) => {
    const value = String(url);
    if (value.startsWith("https://api.openalex.org/works?")) {
      return Response.json({
        results: [{
          doi: "https://doi.org/10.1000/unrelated",
          display_name: "Marine biology and coral reefs",
          publication_year: 2025,
          abstract_inverted_index: { Coral: [0], reefs: [1] },
          primary_location: { landing_page_url: "https://example.org/coral" },
          open_access: { oa_url: null },
        }],
      });
    }
    if (value.startsWith("https://api.crossref.org/works?")) {
      return Response.json({
        message: {
          items: [{
            DOI: "10.1000/another",
            title: ["A history of medieval architecture"],
            abstract: "<jats:p>Unrelated text.</jats:p>",
            published: { "date-parts": [[2025]] },
          }],
        },
      });
    }
    throw new Error(`Unexpected fetch: ${value}`);
  });

  const result = await enrichCandidate({
    title: "Mafia infiltration and ownership dynamics in Italian companies",
    year: "2025",
  });
  assert.equal(result.abstract, "");
  assert.equal(result.matchType, "none");
});
