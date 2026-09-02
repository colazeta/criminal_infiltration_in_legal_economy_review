"use strict";

// GitHub Pages never receives the curator API origin or reusable credentials.
// The public curator page only links to the isolated, production-verified Worker console.
window.CURATOR_APP_CONFIG = Object.freeze({
  apiBaseUrl: "",
  secureAppUrl: "https://criminal-infiltration-curator.colazeta-research.workers.dev/curate.html",
});
