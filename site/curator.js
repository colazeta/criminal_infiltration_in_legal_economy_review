"use strict";

const byId = (id) => document.getElementById(id);

function setText(id, value) {
  const element = byId(id);
  if (element) element.textContent = value;
}

function formatDate(value) {
  if (!value) return "Nessuna esecuzione registrata";
  const parsed = new Date(`${value}T00:00:00Z`);
  return new Intl.DateTimeFormat("it-IT", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(parsed);
}

function renderQueue(stats) {
  const counts = stats.byStage || {};
  const origins = stats.openByOrigin || {};
  const metadata = Number(counts.metadataFix || 0);
  const manual = Number(counts.manualReview || 0);
  const abstractReview = Number(counts.abstractReview || 0);
  const legacyRejected = Number(counts.legacyRejectionReview || 0);
  setText("queue-total", Number(stats.open || 0));
  setText("queue-metadata", metadata);
  setText("queue-manual", manual);
  setText("queue-abstract", abstractReview);
  setText("queue-legacy-rejected", legacyRejected);
  setText(
    "queue-origin-summary",
    `${Number(origins.legacy || 0)} legacy · ${Number(origins.daily || 0)} da intake · ${Number(stats.completed || 0)} completate`,
  );
}

function renderRun(metrics) {
  const status = metrics.summary?.lastRunStatus;
  const labels = {
    completed: "Completata",
    partial: "Parziale",
    failed: "Fallita",
  };
  setText("last-run-status", labels[status] || "Non ancora eseguita");
  setText("last-run-date", formatDate(metrics.dataThrough));
  const dot = byId("run-health-dot");
  if (dot) dot.dataset.status = status || "none";
}

function renderUnavailable() {
  for (const id of [
    "queue-total",
    "queue-metadata",
    "queue-manual",
    "queue-abstract",
    "queue-legacy-rejected",
    "queue-origin-summary",
  ]) {
    setText(id, "n.d.");
  }
  setText("last-run-status", "Dati non disponibili");
  setText("last-run-date", "Riprova o consulta GitHub Actions");
}

Promise.all([
  fetch("./data/curator-stats.json").then((response) => {
    if (!response.ok) throw new Error("curator statistics unavailable");
    return response.json();
  }),
  fetch("./data/research-stats.json").then((response) => {
    if (!response.ok) throw new Error("research statistics unavailable");
    return response.json();
  }),
])
  .then(([stats, metrics]) => {
    renderQueue(stats);
    renderRun(metrics);
  })
  .catch(renderUnavailable);
