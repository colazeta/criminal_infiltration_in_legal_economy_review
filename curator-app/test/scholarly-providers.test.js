"use strict";

import assert from "node:assert/strict";
import test from "node:test";

import {
  datacite,
  europePmc,
  exa,
  plainTextAbstract,
  semanticScholar,
} from "../src/scholarly-providers.js";

function withFetchMock(context, implementation) {
  const original = globalThis.fetch;
  context.after(() => {
    globalThis.fetch = original;
  });
  globalThis.fetch = implementation;
}

const requested = {
  title: "Bricks or cooks? Geographical and social determinants of the investment choices of mafia-type organized crime",
  doi: "10.1177/17488958241293927",
  year: "2024",
};

test("Semantic Scholar can supply an abstract by DOI", async (context) => {
  withFetchMock(context, async (url) => {
    const parsed = new URL(String(url));
    assert.ok(decodeURIComponent(parsed.pathname).includes("/paper/DOI:10.1177/17488958241293927"));
    assert.ok(parsed.pathname.includes("DOI%3A10.1177%2F17488958241293927"));
    return Response.json({
      title: requested.title,
      year: 2024,
      abstract: "This article studies legitimate businesses confiscated from mafia groups in Italy and the geography of investment choices.",
      url: "https://www.semanticscholar.org/paper/example",
      externalIds: { DOI: requested.doi },
      openAccessPdf: { url: "https://example.org/paper.pdf" },
    });
  });

  const result = await semanticScholar(requested);
  assert.equal(result.abstractSource, "Semantic Scholar");
  assert.equal(result.matchType, "doi");
  assert.match(result.abstract, /legitimate businesses/);
});

test("DataCite abstracts are read from descriptions with descriptionType Abstract", async (context) => {
  withFetchMock(context, async (url) => {
    assert.ok(String(url).includes("api.datacite.org/dois/"));
    return Response.json({
      data: {
        id: requested.doi,
        attributes: {
          doi: requested.doi,
          publicationYear: 2024,
          titles: [{ title: requested.title }],
          descriptions: [{
            descriptionType: "Abstract",
            description: "This study examines mafia investment patterns and legitimate firms across Italian territories.",
          }],
          url: "https://repository.example/item",
        },
      },
    });
  });

  const result = await datacite(requested);
  assert.equal(result.abstractSource, "DataCite");
  assert.match(result.abstract, /mafia investment patterns/);
});

test("Europe PMC core results can contribute abstracts", async (context) => {
  withFetchMock(context, async (url) => {
    const value = String(url);
    assert.ok(value.includes("europepmc"));
    assert.ok(value.includes("resultType=core"));
    return Response.json({
      resultList: {
        result: [{
          title: requested.title,
          pubYear: "2024",
          doi: requested.doi,
          abstractText: "This article analyses confiscated firms, organised crime and geographic investment choices using spatial methods.",
        }],
      },
    });
  });

  const result = await europePmc(requested);
  assert.equal(result.abstractSource, "Europe PMC");
  assert.match(result.abstract, /confiscated firms/);
});

test("plain-text web extraction requires an explicit abstract section", () => {
  const text = "Article title Abstract This paper studies criminal infiltration into legal firms using administrative data and network evidence. Introduction The rest of the paper follows.";
  assert.match(plainTextAbstract(text), /criminal infiltration/);
  assert.equal(plainTextAbstract("A generic page description without an abstract heading even if it is fairly long and descriptive for readers."), "");
});

test("Exa web search uses publication category and accepts only strong title matches", async (context) => {
  withFetchMock(context, async (url, options) => {
    assert.equal(String(url), "https://api.exa.ai/search");
    assert.equal(options.method, "POST");
    assert.equal(options.headers["x-api-key"], "exa-test-key");
    const body = JSON.parse(options.body);
    assert.equal(body.category, "publication");
    assert.equal(body.numResults, 8);
    return Response.json({
      results: [{
        title: requested.title,
        url: "https://publires.unicatt.it/example",
        text: "Abstract This article studies legitimate businesses confiscated from mafia groups in Italy to assess whether investment patterns across industries depend on the geographical environment. Introduction We then present data and methods.",
      }],
    });
  });

  const result = await exa(requested, "exa-test-key");
  assert.equal(result.abstractSource, "Exa / web");
  assert.equal(result.matchType, "web_search");
  assert.match(result.abstract, /legitimate businesses/);
});
