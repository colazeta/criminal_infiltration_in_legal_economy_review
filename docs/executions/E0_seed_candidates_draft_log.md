# E0 Seed Candidates Draft Log

## Scope of this artifact
This document governs review of `data/raw/e0_seed_candidates_draft.md` before any official registry update.

## How the draft should be reviewed
1. Verify bibliographic identity (title, authors, year, venue).
2. Confirm topical fit with the core eligibility criterion (criminal infiltration in legal economy).
3. Confirm whether each candidate is `core_seed`, `contextual_seed`, or remains `candidate_seed`.
4. Validate DOI only when confidently matched; otherwise keep blank.
5. Check duplication risk across variants/editions/reports.

## Promotion rule into `e0_seed_candidates.csv`
A candidate can be promoted only if:
- bibliographic fields are verified;
- rationale is specific and traceable;
- seed category matches one of the defined E0 strata;
- verification status is upgraded from `to_verify` to `verified`.

## Fields requiring verification prior to promotion
- `provisional title` (canonical title form)
- `authors` (full and ordered list)
- `year`
- `DOI` (if any)
- `source basis`
- `proposed seed status`

## Registry status note
The draft is a working document and is **not yet part of the official registry**.
No entries from this draft should be copied into registry CSVs until review approval.
