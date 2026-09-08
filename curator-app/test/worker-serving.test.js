import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import vm from "node:vm";

// Substitute only the platform superclass; exercise the real assembled router,
// generated config, asset allowlists and authentication boundaries.
const source = readFileSync(new URL("../src/worker.js", import.meta.url), "utf8")
  .replace('import { DurableObject } from "cloudflare:workers";', 'const DurableObject = class {};')
  .replace(/from "(\.\/[^\"]+)"/g, (_, path) => `from "${new URL(`../src/${path.slice(2)}`, import.meta.url).href}"`);
const worker = (await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}`)).default;
const env = { GITHUB_REPOSITORY: "colazeta/criminal_infiltration_in_legal_economy_review", GITHUB_REPOSITORY_ID: "1224850188", CURATOR_LOGIN: "colazeta", GITHUB_CLIENT_ID: "test", GITHUB_CLIENT_SECRET: "test", SESSION_SECRET: "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8=", SITE_URL: "https://test.workers.dev/curate.html", GITHUB_CALLBACK_URL: "https://test.workers.dev/auth/callback", ASSETS: { async fetch(request) {
  const path = new URL(request.url).pathname.slice(1);
  try { return new Response(readFileSync(new URL(`../../site/${path}`, import.meta.url)), { headers: { "Content-Type": path.endsWith("css") ? "text/css" : "text/javascript" } }); }
  catch { return new Response("missing", { status: 404 }); }
} } };
test("assembled Worker delivers its guided module and external CSP-compatible styles", async () => {
  const response = await worker.fetch(new Request("https://test.workers.dev/curator-config.js"), env);
  assert.equal(response.status, 200);
  const scripts = [];
  vm.runInNewContext(await response.text(), { window: {}, document: { querySelector: () => null, createElement: () => ({ dataset: {} }), head: { append: (s) => scripts.push(s.src) } } });
  assert.ok(scripts.includes("./curator-guided.js"));
  for (const path of [...scripts, "./curator-guided.css", "./curator-shell.css", "./application.css", "./review-v2.html", "./model.css"]) {
    assert.equal((await worker.fetch(new Request(new URL(path, "https://test.workers.dev/")), env)).status, 200, path);
  }
  const v2 = await worker.fetch(new Request("https://test.workers.dev/review-v2.html"), env);
  assert.ok(v2.headers.get("Content-Security-Policy").includes("script-src 'self'"));
  assert.equal(v2.headers.get("Cache-Control"), "no-store");
  assert.ok(scripts.indexOf("./curator-assisted-resolution.js") < scripts.indexOf("./curator-reading.js"));
});
test("new private V2 routes reject unauthenticated requests; public links reach Pages", async () => {
  for (const path of ["status", "candidate?id=TEST", "evidence?id=TEST", "daily"]) {
    assert.equal((await worker.fetch(new Request(`https://test.workers.dev/api/v2/${path}`), env)).status, 401);
  }
  const response = await worker.fetch(new Request("https://test.workers.dev/stats.html"), env);
  assert.equal(response.status, 302);
  assert.equal(response.headers.get("Location"), "https://colazeta.github.io/criminal_infiltration_in_legal_economy_review/stats.html");
});
