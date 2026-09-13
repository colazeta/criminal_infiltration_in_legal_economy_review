# Residual intake recovery — 13 September 2026

## Scope and evidence boundary

This owner-directed maintenance continues the candidate-publication audit; it does
not reset the archive or change scientific eligibility. The live read-only snapshot
at 2026-09-13T14:12:25Z found 245 served candidate records and one open candidate
intake, #225. The discovery task was disabled and was re-enabled at 14:07Z with its
existing hourly :40 Europe/Rome schedule. An open maintenance issue is not evidence
that a recovery workflow is running.

## Historical intake #225

The original owner-authored issue has batch
`ACADEMIC-2026-09-09-EXTRA-4d1777fe93be` and fourteen candidates. Its original body
is preserved; the audited UTF-8 SHA-256 is
`2851f8e186032f7bf13c015c8f9c83670ee41a5e2558cc1949682c9dbe5163bd`.
No authenticated completed terminal exists for that original search. This repair
must not invent one, add retrospective discovery yields or change the old issue
body. Eleven source occurrences were already reconcilable under the existing
operational matching rules. The remaining three require different treatment.

### Candidate 003: genuinely missing operational record

The publisher identifies *Mafia infiltration, public administration and local
institutions: A comparative study in Northern Italy*, DOI
`10.1177/1477370818803050`, by Joselle Dagnes, Davide Donatiello, Valentina Moiso,
Davide Pellegrino, Rocco Sciarrone and Luca Storti. The journal issue is dated
2020; first online publication was 8 October 2018.

Primary evidence: https://journals.sagepub.com/doi/10.1177/1477370818803050

This candidate is **not** placed in the exception map. A new, actually executed
seven-query W1–W7 recovery acquisition created intake #579, batch
`ACADEMIC-2026-09-13-EXTRA-4b57a3081215`, and authenticated terminal
https://github.com/colazeta/criminal_infiltration_in_legal_economy_review/issues/30#issuecomment-5653865699 .
Its final source was Parallel Search after the documented Exa HTTP 402 credit
limit. This independently observed accession is a recovery of a known orphan,
not a claim of new scientific discovery or completion of the old search.
Only its normal validated persistence can make the old DOI occurrence represented.
The same acquisition retains six additional, previously unregistered plausible
scholarly candidates with explicit partial metadata and pending scientific review.

### Candidate 006: same UNICRI report, different repository locator

The original 2019-10 locator and the registered 2021-06 locator both identify
*Organized Crime and the Legal Economy: The Italian Case*. The UNICRI publication
catalogue lists the report as Turin, 2016. The publisher document title and
copyright page agree. These are bibliographic observations, **not** a claim of
byte-identical PDFs or a newly verified OA receipt.

Evidence:
- https://unicri.org/services/library_documentation/publications/unicri_series
- https://unicri.org/sites/default/files/2019-10/UNICRI_Organized_Crime_and_Legal_Economy_report.pdf
- https://unicri.org/sites/default/files/2021-06/UNICRI_Organized_Crime_and_Legal_Economy_report.pdf

The existing operational target is
`CAND-ACADEMIC-2026-09-13-EXTRA-a6766e6649ed-004` from intake #473.
No new CandidateRecord, copied full text or canonical work relation is created.
Unknown fields on the existing candidate are not silently filled.

### Candidate 011: historical author-name variant

The original source states `Helene Rönnblom`; the publisher's contents list for
*Organised Crime in European Businesses* identifies the chapter *Social welfare
fraud and criminal infiltration in Sweden* by Johanna Skinnari, Lars Korsell and
**Helena Rönnblom**. The already registered author spelling matches the publisher.

Evidence: https://www.routledge.com/Organised-Crime-in-European-Businesses/Savona-Riccardi-Berlusconi/p/book/9781138499478

The existing target is `CAND-ACADEMIC-2026-09-09-EXTRA-6b5b5e038ac4-024` from #226.
The original name variant and parent-book identifier remain in the immutable
source issue. A parent-book DOI is not used as a general chapter identity key.

### Closed exception, not a fuzzy matching rule

`scripts/curation/audited_intake_reconciliation.py` permits only these two
reviewed occurrence correspondences. It pins the original owner, issue number,
batch title and full source-body hash. Each target must exist exactly once and
match a SHA-256 fingerprint of its candidate ID, title, authors, year, venue, DOI,
other identifiers and source links. A changed source, changed bibliography,
missing target or ambiguous target fails closed and requires renewed review.

Every remaining source candidate must still pass the normal reconciler. In
particular, candidate 003 cannot disappear via the exception. This helper never
writes the queue and never supplies a missing run terminal. Once all fourteen
occurrences are accounted for, #225 may close as **reconciled**, with
`terminal_absent: true`, not as a retrospectively successful research run.

This is technical preservation evidence about existing CandidateRecords. The
CandidateRecord / provenance boundary in ontology profile 0.4.1 is unchanged.
No governed table, semantic field, canonical ScholarlyWork relation, decision,
review status, access state or scientific publication is introduced.

## Recovery request that can actually be retriggered

Use existing owner-authored maintenance issue **#362** as the canonical request.
The exact owner comment `/recover-intake` now triggers the existing sole writer,
even when the issue is already open or closed. Comments on another issue, from
another author, or with another command cannot activate this lane. Existing
terminal, periodic :55 and dispatch triggers remain unchanged. Concurrency stays
serial, queued and non-cancelling; no second writer or scheduler is introduced.

Before commenting, check actual queued/in-progress `Recover intake backlog` runs.
A merely open issue is not a running lease. Conversely, an active recovery is not
cancelled because another request arrives. Reuse #362 instead of creating another
maintenance issue. Requests #484, #486, #488 and #492 are historical duplicates;
consolidate them only after the canonical recovery is verified.

The workflow reports comment-triggered requests and retains its structured
candidate-conservation receipt as an Actions artifact, including when a batch
remains blocked. Retention is 30 days; the immutable intake, ledger and reviewed
source/evidence pins remain the durable project history. Main persistence and
live-site publication remain separate checks. No workflow dispatch alone is
reported as successful publication.

## Validation and rollback

Regression tests cover exact correspondence, changed source/target evidence,
wrong author/title/issue, missing or ambiguous target, unaffected enrichment,
read-only behaviour and continued blocking of the genuinely missing article.
The complete repository, ontology, Python/JavaScript and deterministic-site suite
must pass before merge, followed by actual recovery and served-register read-back.

Rollback the helper import/call and its two guarded entries together to restore
strict automatic matching. This reopens the historical reconciliation question;
it does not delete any candidate or edit an intake/terminal. The command trigger
can independently be removed; the existing periodic recovery remains available.
