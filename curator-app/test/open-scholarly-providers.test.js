"use strict";

import assert from "node:assert/strict";
import test from "node:test";

import {
  arxiv,
  doaj,
  hal,
  openCitationsMeta,
  openMetadataProviderManifest,
  zenodo,
} from "../src/open-scholarly-providers.js";

function withFetchMock(context, implementation) {
  const original = globalThis.fetch;
  context.after(() => {
    globalThis.fetch = original;
  });
  globalThis.fetch = implementation;
}

const requested = {
  title: "Mafia Infiltration and Ownership Dynamics during Covid",
  doi: "10.1234/example.2025.1",
  year: "2025",
};

test("arXiv adapter parses Atom metadata and related DOI", async (context) => {
  withFetchMock(context, async (url) => {
    assert.equal(new URL(String(url)).hostname, "export.arxiv.org");
    return new Response(`<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom"><entry><id>http://arxiv.org/abs/2501.01234</id><published>2025-01-04T00:00:00Z</published><title>${requested.title}</title><summary>This paper studies ownership changes in firms exposed to organised-crime infiltration during the pandemic using administrative company data.</summary><author><name>Anna Rossi</name></author><author><name>Marco Bianchi</name></author><arxiv:doi>${requested.doi}</arxiv:doi><arxiv:journal_ref>Journal of Economic Crime</arxiv:journal_ref></entry></feed>`, { headers: { "Content-Type": "application/atom+xml" } });
  });
  const result = await arxiv(requested);
  assert.equal(result.provider, "arXiv");
  assert.equal(result.matchedDoi, requested.doi);
  assert.match(result.abstract, /ownership changes/);
  assert.match(result.authors, /Anna Rossi/);
  assert.ok(result.relations.some((value) => value.startsWith("arxiv:")));
});

test("Zenodo adapter exposes repository manifestation metadata", async (context) => {
  withFetchMock(context, async (url) => {
    assert.equal(new URL(String(url)).pathname, "/api/records");
    return Response.json({ hits: { hits: [{
      id: 12345,
      doi: requested.doi,
      metadata: {
        title: requested.title,
        publication_date: "2025-03-01",
        doi: requested.doi,
        description: "<p>This paper studies criminal infiltration and ownership dynamics in legal firms.</p>",
        creators: [{ name: "Rossi, Anna" }],
        publisher: "Zenodo",
        related_identifiers: [{ relation: "isVersionOf", identifier: requested.doi }],
      },
      links: { html: "https://zenodo.org/records/12345" },
      files: [{ links: { self: "https://zenodo.org/api/records/12345/files/paper.pdf/content" } }],
    }] } });
  });
  const result = await zenodo(requested);
  assert.equal(result.provider, "Zenodo");
  assert.match(result.abstract, /criminal infiltration/);
  assert.ok(result.relations.some((value) => value.includes("isVersionOf")));
});

test("HAL adapter uses public search metadata", async (context) => {
  withFetchMock(context, async (url) => {
    const parsed = new URL(String(url));
    assert.equal(parsed.hostname, "api.archives-ouvertes.fr");
    assert.match(parsed.searchParams.get("fl"), /doiId_s/);
    return Response.json({ response: { docs: [{
      halId_s: "hal-05000000",
      title_s: [requested.title],
      authFullName_s: ["Anna Rossi", "Marco Bianchi"],
      producedDateY_i: 2025,
      doiId_s: [requested.doi],
      abstract_s: ["This study examines organised-crime infiltration into firms and ownership changes."],
      journalTitle_s: ["Crime and Markets"],
      uri_s: "https://hal.science/hal-05000000",
    }] } });
  });
  const result = await hal(requested);
  assert.equal(result.provider, "HAL");
  assert.equal(result.sourceId, "hal:hal-05000000");
  assert.match(result.abstract, /ownership changes/);
});

test("DOAJ adapter reads article abstract and identifiers", async (context) => {
  withFetchMock(context, async (url) => {
    assert.ok(new URL(String(url)).pathname.startsWith("/api/search/articles/"));
    return Response.json({ results: [{
      id: "doaj-record",
      bibjson: {
        title: requested.title,
        year: "2025",
        abstract: "This article analyses mafia infiltration and corporate ownership using Italian firm data.",
        author: [{ name: "Anna Rossi" }],
        journal: { title: "Open Crime Research" },
        identifier: [{ type: "doi", id: requested.doi }],
        link: [{ type: "fulltext", url: "https://journal.example/article.pdf" }],
      },
    }] });
  });
  const result = await doaj(requested);
  assert.equal(result.provider, "DOAJ");
  assert.equal(result.matchedDoi, requested.doi);
  assert.equal(result.articleUrl, "https://journal.example/article.pdf");
});

test("OpenCitations Meta verifies DOI-linked bibliographic identity", async (context) => {
  withFetchMock(context, async (url) => {
    assert.ok(String(url).includes("/metadata/doi:"));
    return Response.json([{
      id: `omid:br/1 doi:${requested.doi}`,
      title: requested.title,
      author: "Anna Rossi; Marco Bianchi",
      pub_date: "2025-04-01",
      venue: "Crime and Markets [issn:1234-5678]",
    }]);
  });
  const result = await openCitationsMeta(requested);
  assert.equal(result.provider, "OpenCitations Meta");
  assert.equal(result.matchedDoi, requested.doi);
  assert.match(result.venue, /Crime and Markets/);
});

test("open metadata provider manifest is credential-free and zero-cost", () => {
  const manifest = openMetadataProviderManifest();
  assert.equal(manifest.length, 5);
  assert.ok(manifest.every((provider) => provider.billing === "none" && provider.credential === "none" && provider.enabled));
});
