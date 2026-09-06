"use strict";

import assert from "node:assert/strict";
import test from "node:test";

import { reconcileMetadata } from "../src/metadata-reconciliation.js";

const requested = {
  title: "Mafia Infiltration and Ownership Dynamics during Covid",
  doi: "10.1234/example.2025.1",
  year: "2025",
  authors: "Anna Rossi; Marco Bianchi",
  venue: "Crime and Markets",
};

function obs(provider, overrides = {}) {
  return {
    provider,
    matchedTitle: requested.title,
    matchedDoi: requested.doi,
    matchedYear: 2025,
    authors: requested.authors,
    venue: requested.venue,
    relations: [],
    ...overrides,
  };
}

test("reconciliation records field-level support and high confidence agreement", () => {
  const result = reconcileMetadata({
    requested,
    observations: [obs("Crossref"), obs("OpenAlex"), obs("OpenCitations Meta")],
  });
  assert.equal(result.identityState, "verified");
  assert.equal(result.fields.doi.value, requested.doi);
  assert.equal(result.fields.doi.confidence, "high");
  assert.ok(result.fields.title.providers.includes("Crossref"));
  assert.ok(result.providerCount >= 3);
});

test("multiple strongly matching DOI manifestations are not silently collapsed", () => {
  const result = reconcileMetadata({
    requested,
    observations: [
      obs("Crossref"),
      obs("Zenodo", {
        matchedDoi: "10.5281/zenodo.1234567",
        sourceId: "zenodo:1234567",
        relations: [`isVersionOf:${requested.doi}`],
      }),
    ],
  });
  assert.equal(result.identityState, "manifestation_ambiguity");
  assert.equal(result.screeningReady, false);
  assert.ok(result.manifestation.manifestations.length >= 2);
  assert.ok(result.manifestation.reasons.some((reason) => /version|manifestation/i.test(reason)));
});

test("a material DOI conflict remains explicit when support is unresolved", () => {
  const result = reconcileMetadata({
    requested: { title: requested.title, year: requested.year },
    observations: [
      obs("Crossref", { matchedDoi: "10.1111/first" }),
      obs("OpenCitations Meta", { matchedDoi: "10.2222/second" }),
    ],
  });
  assert.ok(["manifestation_ambiguity", "conflict"].includes(result.identityState));
  assert.ok(result.fields.doi.alternatives.length >= 1);
});
