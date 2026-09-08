# Exa-only source amendment — 2026-09-08

The owner explicitly requested removal of Consensus from the process. This
amendment applies to future discovery, not to recorded historical outcomes.

| Boundary | Current behaviour |
|---|---|
| Daily discovery | Exa only; all seven W1–W7 windows |
| Work task | Existing Daily AML & CI Research; 07:00 Europe/Rome |
| Operational protocol | CILE-DAILY-v3 |
| Run and intake manifests | schema_version 2; source set exactly Exa |
| Historical decoder | v1 retains Consensus + Exa, original counts and status |
| New OA calendar | One expected source per date; seven baseline planned queries |
| Failure | Some usable queries: partial; none: failed; unknown totals stay null |
| Candidate attribution | Exa hits and exclusives both equal the persisted intake total |
| Worker | No Consensus adapter call, binding or readiness requirement |
| V2 startup | Still requires Exa access/budget, current query manifest and private infrastructure |
| Scientific boundary | OA-1, CILE-4PT-OA-v3, human screening and publication approval unchanged |

Exa discovery is not a peer-review or OA attestation. Verify the publication
and its lawful full-text manifestation against primary evidence. Losing an
independent discovery channel narrows coverage; formal source calibration and
backward/forward citation work remain necessary. Daily completion means the
declared Exa queries finished, not that the literature was exhaustively searched.

The existing pre-reset 2026-09-08 run remains partial. It is not rewritten,
upgraded or replayed. The current calendar starts on 2026-09-09; the watchdog
uses that same scope. This amendment does not add extraordinary-run identities,
seed membership, scientific decisions, corpus rows or database activation.

Historical v1 and current v2 projections remain separate. The publisher rejects
a v1 run in the current cycle instead of silently dropping it; the marker,
source set, manifests, candidate attribution and W1–W7 coverage must agree.
Missing days still appear and reduce calendar completeness. Metadata agreement
is labelled “Concordanza bibliografica” in the curator UI and continues to
compare authorised metadata providers; it is unrelated to the retired service.

Rollback is a reviewed code/prompt change. Preserve all v2 ledger comments and
intake provenance before any rollback. An older two-source deployment cannot
decode new v2 runs and must not be restored over the live statistics pipeline
without a compatible reader. Re-enabling Consensus requires a new owner-approved
source-policy change; it is not an automatic response to Exa failure.
