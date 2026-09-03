# Governed web providers

`web-capabilities.json` is the machine-readable inventory for external web-search, page-reading, rendering and agentic-browsing capabilities considered by the review.

The registry is broader than the automatic runtime. `automatic_allowed=false` is intentional: it records a useful provider without granting the Worker permission to call it.

Provider metadata is re-verified when an adapter is added or when pricing/free-tier behaviour materially changes. A provider should be downgraded to non-automatic whenever a zero-spend hard stop can no longer be established.
