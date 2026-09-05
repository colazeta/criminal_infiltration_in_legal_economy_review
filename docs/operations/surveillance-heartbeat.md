# Daily surveillance heartbeat

The daily literature-surveillance search is executed by the external `Daily AML & CI Research` task. The repository therefore cannot infer that the search ran merely because repository CI is green.

`.github/workflows/surveillance-heartbeat.yml` provides a separate operational watchdog. Every day, after the normal external-search window, it checks issue #30 for the governed `ACADEMIC-YYYY-MM-DD` ledger entry.

If the entry is missing, the watchdog opens or updates one idempotent issue titled `[OPS] Daily surveillance heartbeat missing`. This issue has **no scientific meaning**: absence from the ledger is not converted into zero results, a failed provider, a completed search, or evidence of saturation. The watchdog never writes or reconstructs a surveillance run.

When the governed ledger entry later appears, the watchdog closes the operational incident. A historical run may be reconstructed only when its exact search window, provider outcomes, counts, intake manifest, and provenance can be reproduced under the normal surveillance contract.

This separation intentionally preserves three different states:

1. a recorded `completed`, `partial`, or `failed` surveillance run;
2. an operationally missing ledger heartbeat;
3. a deliberate no-op because the batch is already recorded.

The watchdog has `contents: read` and `issues: write` permissions only. It cannot change the corpus, review queue, scientific decisions, or publication state.
