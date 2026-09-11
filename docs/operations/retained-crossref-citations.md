# Outgoing references from retained Crossref metadata

Owner-authorised enrichment continuation, 11 September 2026. This is a mechanical derivation of references for existing candidates, not literature discovery, canonical reconciliation or scientific acceptance.

## Source and execution boundary

Crossref is already authorised in `docs/governance/sources.md` for automated candidate-bound DOI metadata. The metadata adapter already retains the exact matched Crossref work object privately. This module uses its deposited `reference` list and `reference-count`; it performs **no external requests**, introduces no new domain/provider, and retains the original identity match and SHA-256 verification. First production derivation is permitted only after this implementation passes CI and is merged.

The beginning of a citations job first checks for a retained current-input Crossref metadata source. If found, it processes at most 100 reference entries per operation with a persistent cursor. The checkpoint binds the specific immutable source ID, offset, returned entry count, unresolved entry count and coverage state. The next hourly ticket resumes it; a crash can replay the same chunk without duplicate citation observations. If no such source exists, the existing OpenAlex adapter may run unchanged. Sources are never relabelled or regenerated.

Outgoing observations use the existing tables `enrichment_citation_observations` and `enrichment_citation_coverage`, provider `Crossref`, direction `outgoing`, identifiers `doi:<normalised DOI>` and a source-ID-bound snapshot. The existing checkpoint JSON field carries processing state; no new ontology entity, semantic field, migration or public export is added. Provider error codes stay operational diagnostics rather than scientific classifications.

## Coverage and unresolved references

Entries without a valid DOI are not guessed or discarded from the evidence: they remain in the exact original metadata and count as unresolved in the checkpoint. A deposited unstructured reference is not a verified identity. The page's returned count is its number of distinct valid DOI observations, whereas the provider count is the declared number of reference entries. Do not sum page counts to obtain unique references, because a deposited DOI may repeat across pages.

`provider_complete` requires the available list to be exhausted, every entry to have a valid DOI and the declared entry count to match its length. Unknown or inconsistent totals and unresolved entries remain `partial`, even when the local cursor is exhausted. An absent list is `not_returned`, not a claim that the paper has no bibliography. An explicitly empty list with declared count zero is distinguishable. No status certifies the completeness of the real-world citation graph.

OpenAlex outgoing/incoming collection still follows as a separate stage. Its rate limits and authentication errors remain visible; already indexed Crossref observations survive them. Crossref here provides outgoing references only: it does not supply incoming citations. DOI and OpenAlex identifier observations cannot be blindly summed as unique works; cross-provider canonical resolution remains a separate unresolved task. None of these linked identifiers is automatically admitted to the review.

## Validation and observed starting state

Seven synthetic tests cover source/target identity, exact private-source hashes, 100-entry chunks and replay, unstructured references, missing versus measured zero, checkpoint isolation, oversized input, and retained outgoing references when the next provider returns 429. Existing citation-provider tests remain unchanged.

A read-only production observation at 18:42 UTC (run `34628074357`, job `103380176124`) showed three real :40 tickets: 16:40 failed `identifier_resolution_required`, 17:40 completed, 18:40 failed `rate_limited`; the next persisted slot was 19:40 UTC. It showed 174 targets, five sources, one unreviewed proposal and zero citation observations. These are the pre-change observations, not claimed effects of this module. All three tickets and the original schedule epoch are preserved. General scientific extraction remains blocked after the failed content benchmark.

Reference: official Crossref REST API documentation, repository `Crossref/rest-api-doc`, work metadata and reference fields. The source is the private already-retained work response, not this documentation or an inferred bibliography.
