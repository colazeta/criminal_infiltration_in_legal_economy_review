# Scientific enrichment completion gate

Protocol **CILE-ENRICH-1** remains proposal-first. This document defines the
separate, additive gate that may attest an already registered CandidateRecord as
fully enriched. It creates no candidate, eligibility decision, canonical work or
automatic scientific approval.

## Completion is an accepted receipt, not a heuristic

A paper is `completed=true` only when the active private enrichment store contains
an immutable `enrichment_adjudication_receipts` row for the **current** candidate
input and current immutable proposal, and that receipt still validates against:

1. full-text private evidence selected by the proposal, with every retained byte
   re-hashed before acceptance;
2. a complete structured CILE-ENRICH-1 proposal with no mandatory
   `ambiguous`/`not_verifiable` facts and a grounded proposal in one of the six
   contribution classes;
3. a finite, dated incoming/outgoing reference snapshot. Provider-specific
   `provider_complete` remains only a provider/snapshot statement, never an
   assertion of a complete real-world citation graph;
4. a separately accepted 12–18-paper heterogeneous calibration receipt for the
   exact model and prompt used by the proposal; and
5. an independent human exact-head GitHub approval whose closed checklist covers
   source evidence, extraction, framework, bibliography, incoming citations and
   limitations.

Engineering can generate the review packet, but its checklist values are `null`.
Only a merged PR with an `APPROVED` review by the configured human curator on the
exact PR head may import `true` decisions. A later `CHANGES_REQUESTED` review,
wrong head, unmerged PR, different repository or altered manifest fails closed.
The imported receipt is append-only and stores the exact reviewed commit and human
review provenance privately.

## Calibration receipt

Calibration approval is also immutable and exact-head human-gated. Its manifest
must record the selected model/prompt, benchmark and metrics digests, 12–18
independently reference-checked cases, at least one full-text case and at least one
hard case, and explicit checks for heterogeneous designs, source fidelity,
omissions, classification agreement, field accuracy and cost/call limits.
Synthetic software fixtures cannot create this receipt.

The private manifests are deliberately small decision artefacts under
`scientific-approvals/` on a reviewed PR:

- `enrichment-calibration-<calibration_id>.json`
- `enrichment-completion-<CandidateRecord ID>.json`

They contain hashes and decisions, not source text or quotations.

## Public boundary

The existing `CILE-PUBLIC-RESEARCH-1` projection remains proposal-only and keeps
`assessment_state=unreviewed_proposal`. It is not repurposed as a scientific
acceptance channel.

A separate closed projection, `CILE-PUBLIC-COMPLETION-1`, is available from the
same public endpoint with `view=completion`. It exposes only:

- candidate identity;
- accepted/not-attested/stale/withheld state and completion time;
- protocol/codebook and the exact public-research revision;
- bounded provider/direction citation-coverage metadata; and
- bounded outgoing reference identifiers with an explicit total/truncation flag.

It never exposes reviewer identity, receipt/proposal/source IDs, private storage
keys, evidence bodies or private offsets. Even an accepted private receipt is
withheld from `completed=true` when the current public research projection cannot
be safely served. Candidate input changes make the old receipt stale rather than
silently transferring it.

The public completion predicate is therefore suitable for the archive KPI,
Completed filter, paper badge and statistics only after the Worker deployment and
served projection have been verified. Until a real calibration and paper-specific
human approval exist, the correct completed numerator is zero; software fixtures
are never counted.

## Rollback and recovery

Migration `0005_enrichment_adjudication.sql` is additive. Rollback reverts
application code while preserving the two receipt tables and their append-only
history. Never delete a receipt to repair a changed paper: a changed candidate
input or proposal simply stops matching the old receipt and requires a new human
adjudication.
