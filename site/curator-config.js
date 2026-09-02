"use strict";

// GitHub Pages never receives the curator API origin or reusable credentials.
// The public curator page only links to the isolated, production-verified Worker console.
window.CURATOR_APP_CONFIG = Object.freeze({
  apiBaseUrl: "",
  secureAppUrl: "https://criminal-infiltration-curator.colazeta-research.workers.dev/curate.html",
});

function loadCuratorComponent(src, marker) {
  if (document.querySelector(`script[data-${marker}="true"]`)) return;
  const script = document.createElement("script");
  script.src = src;
  script.defer = true;
  script.dataset[marker.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] = "true";
  document.head.append(script);
}

loadCuratorComponent("./curator-reading.js", "curator-reading");
loadCuratorComponent("./curator-queue.js", "curator-queue");
loadCuratorComponent("./curator-resolved-link.js", "curator-resolved-link");
