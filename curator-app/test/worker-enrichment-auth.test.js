"use strict";

import assert from "node:assert/strict";
import test from "node:test";

import worker from "../src/worker.js";

const ORIGIN = "https://curator.example.workers.dev";
const SESSION_SECRET = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";
const ENV = {
  GITHUB_REPOSITORY: "colazeta/criminal_infiltration_in_legal_economy_review",
  GITHUB_REPOSITORY_ID: "1224850188",
  GITHUB_CLIENT_ID: "Iv1.test",
  GITHUB_CLIENT_SECRET: "secret",
  GITHUB_CALLBACK_URL: `${ORIGIN}/auth/callback`,
  SITE_URL: `${ORIGIN}/curate.html`,
  CURATOR_LOGIN: "colazeta",
  SESSION_SECRET,
};

test("enrichment endpoint is not usable without a curator session", async () => {
  const target = new URL(`${ORIGIN}/api/enrichment`);
  target.searchParams.set("title", "Mafia infiltration in firms");
  const response = await worker.fetch(new Request(target), ENV);
  assert.equal(response.status, 401);
  const payload = await response.json();
  assert.equal(payload.error.code, "authentication_required");
});
