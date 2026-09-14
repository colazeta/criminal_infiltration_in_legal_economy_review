# Filtering papers by actual processing

Owner extension to issue #597, 13 September 2026: make papers already processed
by AI discoverable without opening every sheet. This is a read-only interface
filter, not a research decision, new extraction lane or scheduler.

## What the controls mean

The operational register keeps all existing search, author, year, venue, access,
review and sorting controls. Its additional content selector distinguishes:

- **Già elaborati: sintesi o analisi**: a non-empty public reading synopsis or a
  currently available structured research projection. No AI attribution is
  inferred for a synopsis whose production mode is not recorded.
- **Con sintesi disponibile**: an identity-matched reading aid of kind
  `verified_abstract_source`, `publisher_summary`, `full_text_intro` or
  `review_synopsis`, with nonblank synopsis text. `metadata_warning`, a DOI,
  retrieval confidence, an abstract-availability flag or a full-text URL do not
  qualify. An introductory synopsis does not establish a full-paper analysis.
- **Analizzati dall’AI** and its three source-coverage variants: the same public
  research projection used in the sheet must be `available`, have recorded
  `generation_kind=automated` and `assessment_state=unreviewed_proposal`, and
  retain its actual `abstract_only`, `partial_text` or `full_text` coverage.
  Unspecified generation is not recoded as AI or human review.
- **Stato non verificabile / analisi non aggiornata**: load/identity failures,
  stale projections and withheld analysis. These are not papers established as
  never analysed. Unchecked records stay unknown, not negative findings.

The second selector uses the existing six-class vocabulary. It matches a
recorded proposed primary or secondary class, never an alternative, topic code,
search keyword or inferred category. `insufficient_evidence` and
`outside_framework` are abstentions, not seventh/eighth classes. An extraction
that abstains can still be AI-processed without being assigned a class.

## Identity, freshness and limits

`site/paper-register.js` contains the independently tested read-only index and
control adapter. It reuses `CILEPaperSheetSupport.selectRecord` and
`CILEPaperResearch.selectRecord`; the filter never joins by approximate title or
silently applies another candidate's extraction. The browser retains only
summary availability, projection state, generation mode, consultation coverage,
proposed class keys and the recorded update date, not a duplicate research store.

The ordinary page initially makes only the shared support-data read. Selecting
an analysis/class filter, or pressing **Aggiorna stato delle analisi**, reads the
registered candidates through the existing public projection endpoint, with at
most four concurrent credential-free, no-store requests and a 12-second request
timeout. Four consecutive failures stop opening further requests. In-flight
reads may finish; untouched records remain unknown. Progress and failures are
explicit, and partial results never imply an exhaustive zero-result search.
Overlapping scans reuse one promise. A refresh clears old positive states before
reading again, so failed fresh reads cannot preserve a false current success.

The summary-only filter needs no full-register research scan. Class and content
filters compose with every existing register filter. Reset clears both new
selectors. Reloading the page or using Refresh observes changed enrichment even
when the candidate count is unchanged. Opening a sheet retains its independent
fresh read, accessible button and double-click behaviour.

## Semantic mapping and delivery

No governed field, taxonomy, review decision or access state is added. These
browser predicates derive exclusively from the existing closed support
projection and `ontology/modules/public-paper-research.json`: availability,
`prov:wasGeneratedBy`, `extraction_source_coverage`, `extraction_framework`,
`extraction_primary`, `extraction_secondary`, `extraction_category` and
`schema:creativeWorkStatus`. The display labels are not new scientific states.
The public-research boundary, history and calibration/curation gates are unchanged.

The existing archive workflow runs the new `paper-processing.test.js` cases and
its post-deployment verifier already compares the exact `paper-register.js`
bytes, including these controls. No additional deployment, scheduler, public API,
private-data permission or persistent index is introduced. The source-backed
public research audit remains responsible for verifying the underlying actual
research projections. Software fixture results must not be reported as actual
numbers of analysed papers.

## End-to-end completion audit — owner instruction, 14 September 2026

The owner's primary outcome is completed scientific enrichment, including
references and final QA, not retrieval or proposal throughput. The audit is
tracked in issue #676; the limited frontend subtask is #677. The existing
hourly enrichment task was updated in place to prioritise the missing
completion dependencies, resume partially processed papers, and report the
final outcome with an independent preparatory-stage breakdown. CILE-HOUR40-1
and the existing private namespace, history and calibration gates are unchanged.

**Completati e validati (end-to-end)** is a strict fail-closed control. The current
CILE-PUBLIC-RESEARCH-1 contract only exposes unreviewed proposals and contains
neither final enrichment adjudication receipts nor reference-completion
attestations. Therefore this version deliberately admits no record to that
filter, even if a record has full text, a summary, a proposed class or an
injected `completed` flag. The interface explicitly says that the final
percentage cannot be attested. This is not a claim that the missing backend
receipt path has been implemented, or that zero visible attestations is a
complete audit of private records. An accepted-receipt projection and its
versioned consumer remain prerequisites for a positive Completed result.

The prominent count uses registered CandidateRecords as its explicit archive
denominator, never a silently substituted eligible/canonical corpus. Stage
counts describe only checked public projections, with their checked/total
coverage visible. They are independent counts of proposals and consultation
coverage, not validated scientific achievements or a nested funnel. References
and final QA remain explicitly unavailable in this public contract, not zero.
A source locator, Crossref/OpenAlex edge count or provider-specific exhaustion
cannot satisfy the missing completion receipt.

Each paper sheet now shows this same proposal-only limitation, the document,
extraction, references, classification and QA stages, and controls to expand or
collapse every nested scientific field and provenance section. A diagnostic
field tally reports values linked to known public evidence spans and explicit
missingness in a full-text proposal. It does not assess correctness, accept
`not_reported`/`not_applicable`, or establish that empty study/dataset/analysis
collections are complete. Ambiguous or unverifiable values remain unresolved.
When the research projection is absent, stale or withheld, the expected
scientific sections remain visible as unavailable placeholders, not fabricated
extraction. Transport errors retain their separate error state.

The references panel explicitly distinguishes the bibliography and incoming
citations from the sources consulted for extraction. It does not expose the
private citation API, private IDs, reviewer notes or source bodies. The public
bibliography/coverage projection, immutable final receipt, independent
calibration/adjudication and matching statistics integration remain tracked
acceptance work in #676. Do not close that issue merely because these UI
safeguards pass tests or deploy successfully.

Targeted tests are in `curator-app/test/enrichment-completion-ui.test.js`; the
ordinary archive workflow already includes them in its wildcard Node test run.
Full mandatory validation, final-head CI and separate served Pages verification
remain required. No new persisted scientific concept or ontology state is
introduced by this UI-only diagnostic.
