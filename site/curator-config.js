"use strict";

// GitHub Pages never receives the curator API origin or reusable credentials.
// The public curator page only links to the isolated, production-verified Worker console.
window.CURATOR_APP_CONFIG = Object.freeze({
  apiBaseUrl: "",
  secureAppUrl: "https://criminal-infiltration-curator.colazeta-research.workers.dev/curate.html",
});

function loadCuratorStylesheet(src, marker) {
  if (document.querySelector(`link[data-${marker}="true"]`)) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = src;
  link.dataset[marker.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] = "true";
  document.head.append(link);
}

function loadCuratorComponent(src, marker) {
  if (document.querySelector(`script[data-${marker}="true"]`)) return;
  const script = document.createElement("script");
  script.src = src;
  script.async = false;
  script.dataset[marker.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] = "true";
  document.head.append(script);
}

// The focus stylesheet is deliberately last in the cascade so it can simplify
// the older dashboard-oriented rules without changing the governed controls.
loadCuratorStylesheet("./curator-focus.css", "curator-focus");

// Interceptors load before the reading surface so they can clone and reuse the same
// enrichment / issue responses without issuing duplicate provider or GitHub requests.
loadCuratorComponent("./curator-consensus.js", "curator-consensus");
loadCuratorComponent("./curator-assisted-resolution.js", "curator-assisted-resolution");
loadCuratorComponent("./curator-reading.js", "curator-reading");
loadCuratorComponent("./curator-queue.js", "curator-queue");
loadCuratorComponent("./curator-resolved-link.js", "curator-resolved-link");
loadCuratorComponent("./curator-focus.js", "curator-focus");
