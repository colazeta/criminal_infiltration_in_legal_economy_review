# Extraordinary surveillance executions

Owner-authorised operational amendment, 8 September 2026. This resolves the
requested same-day restart without replacing the morning's historical run.

## Identity and execution

- Scheduled execution keeps `ACADEMIC-YYYY-MM-DD`, once per Rome date.
- A separately requested manual execution uses
  `ACADEMIC-YYYY-MM-DD-EXTRA-<12 lowercase hexadecimal characters>`.
  Generate the suffix once with `secrets.token_hex(6)` before the first query;
  retain it through all retries. Check all paginated ledger comments and intake
  issues for this exact ID before searching and again before writing. A collision
  before starting needs a new suffix; an existing executed batch is a no-op.
- An extra run may start after the reset timestamp on the reset day. It cannot
  predate reset, replay a legacy intake, reuse a daily ID, or move its actual
  timestamps to another date. A run crossing midnight cannot be recorded as one
  completed run: close the current date's incomplete run and explicitly start a
  separate execution on the next date.
- The schema-v2 source set, seven Exa workstreams W1–W7, result caps, receipts,
  status/null semantics, exact source commit and existing scientific safeguards
  all apply. The operational protocol remains CILE-DAILY-v3 with this additive
  execution-identity amendment; historical schema-v1 is not widened.
- Use the same immutable envelope in ledger #30 and the same intake form/title,
  substituting the exact extra batch ID throughout. One batch has at most one
  intake issue and one terminal ledger comment. Never edit the terminal comment.
- Check active registry, active queue and all post-reset intake issues, including
  unmerged intakes, for DOI, stable IDs and conservative title/year identity.
  Rediscovery is a known result, not another candidate. An unresolved collision
  is not merged or silently counted twice. Do not execute simultaneous discovery
  writers: a user-requested extra run must check for an existing active run;
  ambiguous concurrent state blocks intake rather than guessing exclusivity.
- Write the terminal ledger immediately after any intake issue. The importer
  validates the live issue and ledger and preserves original receipts. It cannot
  assign scientific approval or publish candidates. The existing staging workflow
  may persist validated pending queue rows under the owner’s maintenance authority.

## Statistics

Public statistics format 3 adds `extraRuns`, a closed aggregate projection.
The scheduled series, completeness denominator, missing-day watchdog and its
07:00 Europe/Rome cadence remain separate. A successful extra run does not erase
a failed or missing scheduled day. An owner-created terminal comment in ledger #30 triggers validation and a Pages
refresh; unrelated comments cannot trigger that deployment. The website shows each extra execution's
time, status, completed/planned queries, unique results and new intake candidates.
Across executions, result counts are not unique-work population counts and must
not be added into the daily completeness measure. New candidates still require
cross-execution deduplication before intake.

## OA acquisition

`config/oa-acquisition.json` is the reviewed exact-host allowlist for anonymous,
candidate-bound full-text and rights evidence acquisition. It includes selected
publishers and institutional repositories, extending the former Zenodo-only
permission. No domain wildcard, search-engine badge or DOI redirect authorises
another origin. Adding a host requires a reviewed source-policy change.

`python3 scripts/oa_acquisition.py --url <observed-pdf-url> --output <private-scratch.pdf>`
acquires one PDF, follows at most five redirects through approved hosts, pins
public DNS addresses, verifies TLS, enforces a 32 MiB limit and computes SHA-256
over actual response bytes. It refuses repository output paths, overwrites,
login/challenge responses and non-PDF responses. It does not bypass a paywall,
CAPTCHA, authentication, network restriction or publisher refusal, and carries
no credentials or paid fallback. Requests are sequential and candidate-bound;
stop on a rate limit or refusal instead of increasing concurrency.

A PDF signature/end marker and hash are transport checks, not proof of correct
identity, complete scholarly content, accepted/version-of-record status or
lawful deposit. Inspect the actual document, landing page and explicit rights
evidence before constructing the unchanged OA-1 receipt. A working-paper
version is not a later journal article. A successful search with no usable OA
receipt has zero intake, not invented OA confirmations.

## Rollback

Before rolling back code, pause new writers. Preserve every extra ledger
comment, intake issue and immutable receipt. Older daily-only readers cannot
consume the new IDs; use a compatible repair or temporarily keep the last valid
site, never delete extra history or rewrite IDs to make an old reader pass.
The change creates no scientific decision, corpus reset or private V2 activation.
