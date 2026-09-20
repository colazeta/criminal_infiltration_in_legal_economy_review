"use strict";

import assert from "node:assert/strict";
import test from "node:test";

import { JevClientError, evaluateJev, validateJevResponse } from "../src/jev-client.js";

const questions = {
  supported: { type: "noul", instructions: "Is it supported?" },
  relation: { type: "choice", instructions: "Choose", criteria: { same: "Same", different: "Different" } },
  strength: { type: "score", instructions: "Score", criteria: ["Low", "High"] },
};

const validPayload = {
  model: "jev-1.13.0",
  answers: {
    supported: { type: "noul", noul: 0.9 },
    relation: { type: "choice", choice: "same", confidence: 0.8, probabilities: { same: 0.9, different: 0.1 } },
    strength: { type: "score", score: 0.75, confidence: 0.5, legend: { "0": "Low", "1": "High" }, probabilities: { "0": 0.25, "1": 0.75 } },
  },
  usage: { input_tokens: 100, output_tokens: 12 },
};

test("validates a pinned Jev response exactly", () => {
  assert.equal(validateJevResponse(structuredClone(validPayload), questions, { expectedModel: "jev-1.13.0" }).model, "jev-1.13.0");
});

test("rejects model drift, missing answers, and invalid probabilities", () => {
  assert.throws(() => validateJevResponse({ ...structuredClone(validPayload), model: "jev-1.14.0" }, questions, { expectedModel: "jev-1.13.0" }), /different from the pinned model/);
  const missing = structuredClone(validPayload);
  delete missing.answers.supported;
  assert.throws(() => validateJevResponse(missing, questions, { expectedModel: "jev-1.13.0" }), /exactly match/);
  const invalid = structuredClone(validPayload);
  invalid.answers.relation.probabilities = { same: 0.8, different: 0.8 };
  assert.throws(() => validateJevResponse(invalid, questions, { expectedModel: "jev-1.13.0" }), /sum to one/);
});

test("fails closed when the API key is absent", async () => {
  await assert.rejects(() => evaluateJev({ state: {}, questions, apiKey: "" }), (error) => error instanceof JevClientError && error.code === "api_key_missing");
});

test("sends only the configured request and validates the response", async () => {
  let observed;
  const payload = await evaluateJev({
    state: { candidate: { title: "Example" } },
    questions,
    apiKey: "secret-test-key",
    fetchImpl: async (url, options) => {
      observed = { url, options };
      return new Response(JSON.stringify(validPayload), { status: 200, headers: { "content-type": "application/json" } });
    },
  });
  assert.equal(payload.model, "jev-1.13.0");
  assert.equal(observed.url, "https://api.typesafe.ai/v1/systemone");
  assert.equal(observed.options.method, "POST");
  assert.equal(observed.options.headers.Authorization, "Bearer secret-test-key");
  const body = JSON.parse(observed.options.body);
  assert.equal(body.model, "jev-1.13.0");
  assert.deepEqual(body.questions, questions);
});

test("retries only documented transient statuses and then succeeds", async () => {
  const statuses = [429, 529, 200];
  let calls = 0;
  const slept = [];
  const result = await evaluateJev({
    state: "x",
    questions,
    apiKey: "secret-test-key",
    fetchImpl: async () => {
      const status = statuses[calls++];
      if (status === 200) return new Response(JSON.stringify(validPayload), { status });
      return new Response(JSON.stringify({ error: "busy" }), { status, headers: { "retry-after": "0" } });
    },
    sleepImpl: async (ms) => { slept.push(ms); },
  });
  assert.equal(result.model, "jev-1.13.0");
  assert.equal(calls, 3);
  assert.deepEqual(slept, [0, 0]);
});

test("does not retry an authentication failure or expose provider body", async () => {
  let calls = 0;
  await assert.rejects(() => evaluateJev({
    state: "x",
    questions,
    apiKey: "secret-test-key",
    fetchImpl: async () => {
      calls += 1;
      return new Response("PRIVATE PROVIDER ERROR BODY", { status: 401 });
    },
  }), (error) => error instanceof JevClientError && error.code === "provider_unauthorized" && !error.message.includes("PRIVATE"));
  assert.equal(calls, 1);
});
