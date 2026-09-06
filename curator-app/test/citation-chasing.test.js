"use strict";

import assert from "node:assert/strict";
import test from "node:test";

import { citationFrontier } from "../src/citation-chasing.js";

function withFetchMock(context, implementation) {
  const original = globalThis.fetch;
  context.after(() => {
    globalThis.fetch = original;
  });
  globalThis.fetch = implementation;
}

test("citation frontier merges E2 and E3 evidence across two providers", async (context) => {
  const seed = "10.1234/seed";
  withFetchMock(context, async (url) => {
    const parsed = new URL(String(url));
    if (parsed.hostname === "api.opencitations.net" && parsed.pathname.includes("/references/")) {
      return Response.json([
        { cited: "doi:10.1111/backward-a", oci: "oci:1" },
        { cited: "doi:10.2222/backward-b", oci: "oci:2" },
      ]);
    }
    if (parsed.hostname === "api.opencitations.net" && parsed.pathname.includes("/citations/")) {
      return Response.json([
        { citing: "doi:10.3333/forward-a", oci: "oci:3" },
      ]);
    }
    if (parsed.hostname === "api.semanticscholar.org" && parsed.pathname.endsWith("/references")) {
      return Response.json({ data: [
        { citedPaper: { paperId: "S2A", title: "Backward A", year: 2020, authors: [{ name: "A Author" }], externalIds: { DOI: "10.1111/backward-a" } } },
        { citedPaper: { paperId: "S2C", title: "Backward C", year: 2019, authors: [{ name: "C Author" }], externalIds: { DOI: "10.4444/backward-c" } } },
      ] });
    }
    if (parsed.hostname === "api.semanticscholar.org" && parsed.pathname.endsWith("/citations")) {
      return Response.json({ data: [
        { citingPaper: { paperId: "S2F", title: "Forward A", year: 2026, authors: [{ name: "F Author" }], externalIds: { DOI: "10.3333/forward-a" } } },
      ] });
    }
    throw new Error(`unexpected fetch ${url}`);
  });

  const frontier = await citationFrontier({ doi: seed });
  assert.equal(frontier.status, "completed");
  assert.equal(frontier.backward.length, 3);
  assert.equal(frontier.forward.length, 1);
  const sharedBackward = frontier.backward.find((row) => row.doi === "10.1111/backward-a");
  assert.deepEqual(sharedBackward.providers.sort(), ["OpenCitations", "Semantic Scholar"].sort());
  assert.equal(frontier.summary.backward.providerAgreement, 1);
  assert.equal(frontier.summary.forward.providerAgreement, 1);
  assert.match(frontier.methodologicalNote, /not treated as a complete citation graph/);
});

test("citation frontier requires a DOI and performs no speculative title traversal", async (context) => {
  withFetchMock(context, async () => {
    throw new Error("network must not be called without DOI");
  });
  const frontier = await citationFrontier({ doi: "" });
  assert.equal(frontier.status, "doi_required");
  assert.deepEqual(frontier.backward, []);
  assert.deepEqual(frontier.forward, []);
});
