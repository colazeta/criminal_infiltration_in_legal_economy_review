import assert from "node:assert/strict";
import test from "node:test";

import worker, {
  CuratorAppError,
  SubmissionCoordinatorCore,
  decisionIssueBody,
  parseCandidateIssue,
  seal,
  unseal,
  validateDecision,
} from "../src/index.js";

const SESSION_SECRET = "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8=";
const ENV = {
  GITHUB_REPOSITORY: "colazeta/criminal_infiltration_in_legal_economy_review",
  GITHUB_REPOSITORY_ID: "1224850188",
  GITHUB_CLIENT_ID: "Iv1.test",
  GITHUB_CLIENT_SECRET: "secret",
  GITHUB_CALLBACK_URL: "https://curator.example.workers.dev/auth/callback",
  SITE_URL: "https://curator.example.workers.dev/curate.html",
  CURATOR_LOGIN: "colazeta",
  SESSION_SECRET,
};
const ORIGIN = "https://curator.example.workers.dev";

function coordinatorEnvironment(overrides = {}) {
  const env = { ...ENV, ...overrides };
  const objects = new Map();
  env.SUBMISSIONS = {
    getByName(name) {
      if (!objects.has(name)) {
        const values = new Map();
        const state = {
          blockConcurrencyWhile(callback) {
            return callback();
          },
          storage: {
            async get(key) {
              return values.get(key);
            },
            async put(key, value) {
              values.set(key, structuredClone(value));
            },
          },
        };
        objects.set(name, new SubmissionCoordinatorCore(state, env));
      }
      const instance = objects.get(name);
      return {
        fetch(input, init) {
          return instance.fetch(input instanceof Request ? input : new Request(input, init));
        },
      };
    },
  };
  return env;
}

function validDecision(overrides = {}) {
  return {
    candidateId: "E0-D002",
    candidateIssueNumber: 33,
    screeningStage: "full_text",
    decision: "eligible_contextual",
    exclusionReasonCode: "",
    topicCode: "conceptual_foundations",
    duplicateTarget: "",
    confidence: "high",
    evidence: "Full text, section 2.",
    rationale: "The work supplies a necessary conceptual contribution.",
    confirmed: true,
    submissionId: "c65db5c0-b505-47a9-9b40-36b094a0f837",
    ...overrides,
  };
}

function queueIssue(overrides = {}) {
  return {
    number: 33,
    state: "open",
    html_url: "https://github.com/colazeta/example/issues/33",
    labels: [{ name: "curation:queue" }, { name: "stage:manual-review" }],
    body: `<!-- curator-candidate:E0-D002 -->

## Candidate record

| Field | Value |
|---|---|
| Candidate ID | \`E0-D002\` |
| Title | Mafias on the Move: How Organized Crime Conquers New Territories |
| Authors | Varese, Federico |
| Year | 2011 |
| Venue | Princeton University Press |
| DOI | Not recorded |
| Source | clean pre-E0 draft (bibliographic integrity audit) |
| Current review stage | **Manual scope review** |

## Pilot provenance — not a decision

- Legacy signal: \`hold_for_manual_review\`
- Legacy scope label: \`contextual_seed\`
- Pilot note: Book-level metadata consistent; DOI not required. \\| contextual rationale may be weak
- Provenance: \`data/legacy/e0/promotion_audit.csv:E0-D002\`

The legacy signal above is retained only for audit.

## Curator action

Record an evidence-backed decision.
`,
    ...overrides,
  };
}

async function sessionToken() {
  return seal(
    {
      purpose: "curator-session",
      exp: Math.floor(Date.now() / 1000) + 3600,
      token: "ghu_test-token",
      login: "colazeta",
      userId: 47261299,
      csrf: "csrf-test",
    },
    SESSION_SECRET,
  );
}

test("sealed state is confidential, purpose-bound and recoverable", async () => {
  const value = await seal(
    { purpose: "oauth-state", exp: Math.floor(Date.now() / 1000) + 60, verifier: "secret-verifier" },
    SESSION_SECRET,
  );
  assert.equal(value.includes("secret-verifier"), false);
  const opened = await unseal(value, SESSION_SECRET, "oauth-state");
  assert.equal(opened.verifier, "secret-verifier");
  await assert.rejects(
    () => unseal(value, SESSION_SECRET, "curator-session"),
    (error) => error instanceof CuratorAppError && error.code === "invalid_session",
  );
});

test("candidate issue parser returns only the structured working record", () => {
  const parsed = parseCandidateIssue(queueIssue());
  assert.equal(parsed.candidateId, "E0-D002");
  assert.equal(parsed.title, "Mafias on the Move: How Organized Crime Conquers New Territories");
  assert.equal(parsed.provenanceKind, "legacy");
  assert.equal(parsed.stageLabel, "stage:manual-review");
  assert.equal(parsed.provenance[2].value.includes("contextual rationale"), true);
  assert.equal("body" in parsed, false);
});

test("decision validation enforces governed field combinations", () => {
  const eligible = validateDecision(validDecision());
  assert.equal(eligible.topicCode, "conceptual_foundations");
  assert.throws(
    () => validateDecision(validDecision({ topicCode: "", confirmed: false })),
    /conferma esplicita/i,
  );
  assert.throws(
    () =>
      validateDecision(
        validDecision({
          decision: "not_eligible",
          topicCode: "",
          exclusionReasonCode: "DUPLICATE_RECORD",
        }),
      ),
    /motivo governato/i,
  );
  const duplicate = validateDecision(
    validDecision({
      decision: "duplicate",
      topicCode: "",
      duplicateTarget: "P000002",
      exclusionReasonCode: "",
    }),
  );
  assert.equal(duplicate.exclusionReasonCode, "DUPLICATE_RECORD");
});

test("generated issue body preserves the existing parser contract", () => {
  const values = validateDecision(validDecision());
  const body = decisionIssueBody(values);
  for (const heading of [
    "Candidate ID",
    "Screening stage",
    "Decision",
    "Exclusion reason",
    "Topic code",
    "Duplicate target",
    "Confidence",
    "Evidence basis and locator",
    "Record-specific rationale",
    "Confirmation",
  ]) {
    assert.match(body, new RegExp(`^### ${heading}$`, "m"));
  }
  assert.match(body, /### Confirmation\n\nAPPLY$/);
  assert.match(body, /<!-- curator-submission:c65db5c0-b505-47a9-9b40-36b094a0f837 -->/);
});

test("login uses OAuth web flow with PKCE and a repository-bound state", async () => {
  const response = await worker.fetch(
    new Request("https://curator.example.workers.dev/auth/login?candidate=E0-D002"),
    ENV,
  );
  assert.equal(response.status, 302);
  const target = new URL(response.headers.get("Location"));
  assert.equal(target.origin, "https://github.com");
  assert.equal(target.pathname, "/login/oauth/authorize");
  assert.equal(target.searchParams.get("code_challenge_method"), "S256");
  assert.equal(target.searchParams.get("redirect_uri"), ENV.GITHUB_CALLBACK_URL);
  const state = await unseal(target.searchParams.get("state"), SESSION_SECRET, "oauth-state");
  assert.equal(state.candidate, "E0-D002");
  assert.ok(state.verifier.length >= 43);
});

test("OAuth callback attributes the user and returns only a sealed browser session", async (context) => {
  const loginResponse = await worker.fetch(
    new Request("https://curator.example.workers.dev/auth/login?candidate=E0-D002"),
    ENV,
  );
  const authorization = new URL(loginResponse.headers.get("Location"));
  const stateValue = authorization.searchParams.get("state");
  const originalFetch = globalThis.fetch;
  context.after(() => {
    globalThis.fetch = originalFetch;
  });
  globalThis.fetch = async (url) => {
    const value = String(url);
    if (value === "https://github.com/login/oauth/access_token") {
      return Response.json({
        access_token: "ghu_callback-token",
        expires_in: 28800,
        refresh_token: "ghr_ignored",
        token_type: "bearer",
      });
    }
    if (value === "https://api.github.com/user") {
      return Response.json({ login: "colazeta", id: 47261299 });
    }
    if (value.endsWith("/repos/colazeta/criminal_infiltration_in_legal_economy_review")) {
      return Response.json({
        full_name: ENV.GITHUB_REPOSITORY,
        id: Number(ENV.GITHUB_REPOSITORY_ID),
      });
    }
    throw new Error(`Unexpected fetch: ${url}`);
  };
  const callback = new URL(ENV.GITHUB_CALLBACK_URL);
  callback.searchParams.set("code", "temporary-code");
  callback.searchParams.set("state", stateValue);
  const response = await worker.fetch(new Request(callback), ENV);
  assert.equal(response.status, 302);
  const target = new URL(response.headers.get("Location"));
  assert.equal(target.origin, ORIGIN);
  assert.equal(target.searchParams.get("candidate"), "E0-D002");
  assert.equal(target.searchParams.has("curator_session"), false);
  const fragment = new URLSearchParams(target.hash.slice(1));
  const session = await unseal(
    fragment.get("curator_session"),
    SESSION_SECRET,
    "curator-session",
  );
  assert.equal(session.login, "colazeta");
  assert.equal(session.token, "ghu_callback-token");
  assert.equal(fragment.get("curator_csrf"), session.csrf);
});

test("the Worker serves only the isolated curator asset surface", async () => {
  const env = {
    ...ENV,
    ASSETS: {
      async fetch(request) {
        return new Response(`asset:${new URL(request.url).pathname}`, {
          headers: { "Content-Type": "text/html; charset=utf-8" },
        });
      },
    },
  };
  const configResponse = await worker.fetch(
    new Request("https://curator.example.workers.dev/curator-config.js"),
    env,
  );
  assert.equal(configResponse.status, 200);
  assert.match(await configResponse.text(), /apiBaseUrl: "https:\/\/curator\.example\.workers\.dev"/);

  const consoleResponse = await worker.fetch(
    new Request("https://curator.example.workers.dev/curate.html"),
    env,
  );
  assert.equal(consoleResponse.status, 200);
  assert.match(consoleResponse.headers.get("Content-Security-Policy"), /connect-src 'self'/);

  const unrelated = await worker.fetch(
    new Request("https://curator.example.workers.dev/index.html"),
    env,
  );
  assert.equal(unrelated.status, 404);
});

test("authenticated candidate list is returned only to the configured site", async (context) => {
  const originalFetch = globalThis.fetch;
  context.after(() => {
    globalThis.fetch = originalFetch;
  });
  globalThis.fetch = async (url) => {
    assert.match(String(url), /labels=curation%3Aqueue/);
    return Response.json([queueIssue()]);
  };
  const token = await sessionToken();
  const response = await worker.fetch(
    new Request("https://curator.example.workers.dev/api/candidates", {
      headers: { Origin: ORIGIN, Authorization: `Bearer ${token}` },
    }),
    ENV,
  );
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("Access-Control-Allow-Origin"), ORIGIN);
  const payload = await response.json();
  assert.equal(payload.candidates.length, 1);
  assert.equal(payload.candidates[0].candidateId, "E0-D002");

  const denied = await worker.fetch(
    new Request("https://curator.example.workers.dev/api/candidates", {
      headers: { Origin: "https://attacker.example", Authorization: `Bearer ${token}` },
    }),
    ENV,
  );
  assert.equal(denied.status, 403);
  assert.equal(denied.headers.get("Access-Control-Allow-Origin"), null);
});

test("decision submission verifies the queue issue and creates an attributed instruction", async (context) => {
  const originalFetch = globalThis.fetch;
  context.after(() => {
    globalThis.fetch = originalFetch;
  });
  const calls = [];
  globalThis.fetch = async (url, init = {}) => {
    calls.push({ url: String(url), init });
    if (String(url).includes("state=all")) return Response.json([]);
    if (String(url).endsWith("/issues/33")) return Response.json(queueIssue());
    if (String(url).endsWith("/issues") && init.method === "POST") {
      const payload = JSON.parse(init.body);
      assert.deepEqual(payload.labels, ["curation:decision"]);
      assert.match(payload.body, /### Confirmation\n\nAPPLY$/);
      assert.match(payload.body, /### Candidate ID\n\nE0-D002/);
      return Response.json(
        { number: 91, html_url: "https://github.com/colazeta/example/issues/91" },
        { status: 201 },
      );
    }
    throw new Error(`Unexpected fetch: ${url}`);
  };
  const token = await sessionToken();
  const decision = validDecision();
  const response = await worker.fetch(
    new Request("https://curator.example.workers.dev/api/decisions", {
      method: "POST",
      headers: {
        Origin: ORIGIN,
        Authorization: `Bearer ${token}`,
        "X-CSRF-Token": "csrf-test",
        "Idempotency-Key": decision.submissionId,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(decision),
    }),
    coordinatorEnvironment(),
  );
  assert.equal(response.status, 201);
  assert.deepEqual(await response.json(), {
    issueNumber: 91,
    issueUrl: "https://github.com/colazeta/example/issues/91",
    replayed: false,
  });
  assert.equal(calls.length, 3);
});

test("concurrent retries reserve one submission atomically", async (context) => {
  const originalFetch = globalThis.fetch;
  context.after(() => {
    globalThis.fetch = originalFetch;
  });
  let creations = 0;
  globalThis.fetch = async (url, init = {}) => {
    if (String(url).includes("state=all")) return Response.json([]);
    if (String(url).endsWith("/issues/33")) return Response.json(queueIssue());
    if (String(url).endsWith("/issues") && init.method === "POST") {
      creations += 1;
      await new Promise((resolve) => setTimeout(resolve, 15));
      return Response.json(
        { number: 92, html_url: "https://github.com/colazeta/example/issues/92" },
        { status: 201 },
      );
    }
    throw new Error(`Unexpected fetch: ${url}`);
  };
  const env = coordinatorEnvironment();
  const token = await sessionToken();
  const decision = validDecision();
  const request = () =>
    worker.fetch(
      new Request("https://curator.example.workers.dev/api/decisions", {
        method: "POST",
        headers: {
          Origin: ORIGIN,
          Authorization: `Bearer ${token}`,
          "X-CSRF-Token": "csrf-test",
          "Idempotency-Key": decision.submissionId,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(decision),
      }),
      env,
    );
  const responses = await Promise.all([request(), request()]);
  assert.deepEqual(
    responses.map((response) => response.status).sort(),
    [200, 201],
  );
  assert.equal(creations, 1);
  const payloads = await Promise.all(responses.map((response) => response.json()));
  assert.deepEqual(
    payloads.map((payload) => payload.replayed).sort(),
    [false, true],
  );
});
