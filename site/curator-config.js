"use strict";

// GitHub Pages never receives the curator API origin or reusable credentials.
// The public curator page only links to the isolated, production-verified Worker console.
window.CURATOR_APP_CONFIG = Object.freeze({
  apiBaseUrl: "",
  secureAppUrl: "https://criminal-infiltration-curator.colazeta-research.workers.dev/curate.html",
});

(() => {
  if (document.querySelector('script[data-curator-reading="true"]')) return;
  const script = document.createElement("script");
  script.src = "./curator-reading.js";
  script.defer = true;
  script.dataset.curatorReading = "true";
  document.head.append(script);
})();
