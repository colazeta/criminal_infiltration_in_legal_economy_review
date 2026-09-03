# Provider economics snapshot — 2026-09-03

This note records the public free-tier facts used to configure `web-capabilities.json`. It is descriptive evidence, not permission to spend.

- **Jina Reader** — official rate-limit documentation reports 20 RPM without an API key and 500 RPM with a free API key for Reader.
- **Serper** — official site advertises 2,500 free queries and no credit card requirement.
- **Tavily Researcher** — official pricing advertises 1,000 API credits per month, no credit card required, with requests stopping when the monthly free allowance is exhausted unless the account is upgraded.
- **Exa Starter** — official pricing advertises $20 signup credit plus $10 monthly credit and no payment method requirement. Because the service also supports paid endpoints/balances, Exa is registered but not automatically callable.
- **Firecrawl Free** — official pricing advertises 1,000 free credits per month and no card. Paid/self-serve modes can later use paid balance/auto-reload, so automatic use remains disabled pending a technical free-only proof.
- **Cloudflare Browser Run** — official docs report 10 browser minutes per day and three concurrent browsers on Workers Free. Automatic use remains disabled until the production account/binding is proven to be the non-billing Free configuration.

Official locators are stored per provider in the machine-readable registry. Re-check this snapshot before changing an adapter from `automatic_allowed=false` to `true`.
