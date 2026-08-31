"use strict";

// These URLs remain empty on GitHub Pages until the isolated Worker origin has
// been deployed and verified. The Worker serves this path dynamically with its
// own origin, so reusable curator credentials never enter colazeta.github.io.
window.CURATOR_APP_CONFIG = Object.freeze({
  apiBaseUrl: "",
  secureAppUrl: "",
});
