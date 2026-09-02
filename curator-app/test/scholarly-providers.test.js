"use strict";

import assert from "node:assert/strict";
import test from "node:test";

import {
  core,
  datacite,
  europePmc,
  plainTextAbstract,
  providerManifest,
  searchFreeWebProvider,
  semanticScholar,
  tavily,
  unpaywall,
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

test("Semantic Scholar can supply an abstract by DOI without requiring a key", async (context) => {
  withFetchMock(context, async (url, options) => {
    const parsed = new URL(String(url));
    assert.ok(decodeURIComponent(parsed.pathname).includes("/paper/DOI:10.1177/17488958241293927"));
    assert.ok(parsed.pathname.includes("DOI%3A10.1177%2F17488958241293927"));
    assert.equal(options?.headers?.["x-api-key"], undefined);
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

test("DataCite abstracts are read from public metadata", async (context) => {
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

test("Unpaywall is skipped without the required free contact email", async (context) => {
  withFetchMock(context, async () => {
    throw new Error("Unpaywall must not be called without email");
  });
  assert.equal(await unpaywall(requested, ""), null);
});

test("Unpaywall can contribute a free OA location", async (context) => {
  withFetchMock(context, async (url) => {
    const parsed = new URL(String(url));
    assert.equal(parsed.searchParams.get("email"), "curator@example.org");
    return Response.json({
      title: requested.title,
      year: 2024,
      doi: requested.doi,
      doi_url: `https://doi.org/${requested.doi}`,
      best_oa_location: {
        url_for_pdf: "https://repository.example/paper.pdf",
        url_for_landing_page: "https://repository.example/item",
      },
    });
  });
  const result = await unpaywall(requested, "curator@example.org");
  assert.equal(result.provider, "Unpaywall");
  assert.equal(result.articleUrl, "https://repository.example/paper.pdf");
});

test("CORE works keyless and can supply abstracts from repository search", async (context) => {
  withFetchMock(context, async (url, options) => {
    const parsed = new URL(String(url));
    assert.equal(parsed.origin, "https://api.core.ac.uk");
    assert.equal(parsed.pathname, "/v3/search/works");
    assert.equal(options?.headers?.Authorization, undefined);
    return Response.json({
      results: [{
        title: requested.title,
        yearPublished: 2024,
        doi: requested.doi,
        abstract: "This article studies legitimate businesses confiscated from mafia groups and their geographic investment patterns across industries.",
        downloadUrl: "https://core.example/paper.pdf",
      }],
    });
  });
  const result = await core(requested);
  assert.equal(result.abstractSource, "CORE");
  assert.match(result.abstract, /legitimate businesses/);
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

test("Tavily web fallback is hard-wired to one-credit Basic search", async (context) => {
  withFetchMock(context, async (url, options) => {
    assert.equal(String(url), "https://api.tavily.com/search");
    assert.equal(options.method, "POST");
    assert.equal(options.headers.Authorization, "Bearer tvly-free-test-key");
    const body = JSON.parse(options.body);
    assert.equal(body.search_depth, "basic");
    assert.equal(body.auto_parameters, false);
    assert.equal(body.include_answer, false);
    assert.equal(body.max_results, 5);
    return Response.json({
      usage: { credits: 1 },
      results: [{
        title: requested.title,
        url: "https://publires.unicatt.it/example",
        raw_content: "Abstract This article studies legitimate businesses confiscated from mafia groups in Italy to assess whether investment patterns across industries depend on the geographical environment. Introduction We then present data and methods.",
      }],
    });
  });

  const result = await tavily(requested, "tvly-free-test-key");
  assert.equal(result.abstractSource, "Tavily / web");
  assert.equal(result.matchType, "free_web_search");
  assert.match(result.abstract, /legitimate businesses/);
});

test("Tavily credit guard rejects responses consuming more than one credit", async (context) => {
  withFetchMock(context, async () => Response.json({ usage: { credits: 2 }, results: [] }));
  await assert.rejects(() => tavily(requested, "tvly-free-test-key"), /tavily_credit_guard/);
});

test("free web provider makes no external call when no free key is configured", async (context) => {
  withFetchMock(context, async () => {
    throw new Error("web provider must remain disabled without a free key");
  });
  const response = await searchFreeWebProvider({ ...requested, tavilyApiKey: "" });
  assert.equal(response.configured, false);
  assert.equal(response.creditsUsed, 0);
  assert.deepEqual(response.providersTried, []);
});

test("provider manifest exposes only zero-cost or free-hard-cap modules", () => {
  const manifest = providerManifest({ tavilyApiKey: "tvly-free-test-key", unpaywallEmail: "curator@example.org" });
  assert.ok(manifest.some((provider) => provider.id === "core" && provider.billing === "none"));
  assert.ok(manifest.some((provider) => provider.id === "unpaywall" && provider.enabled));
  assert.ok(manifest.some((provider) => provider.id === "tavily" && provider.billing === "free_hard_cap"));
  assert.equal(manifest.some((provider) => provider.id === "exa"), false);
});
