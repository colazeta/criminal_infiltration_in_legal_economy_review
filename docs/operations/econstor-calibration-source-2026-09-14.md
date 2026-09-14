# EconStor candidate-bound calibration source — 14 September 2026

This reviewed maintenance change extends only the exact-host OA acquisition
allowlist used by `scripts/oa_acquisition.py`. It does not create a CandidateRecord,
change identity, establish scientific eligibility, accept a six-class label or
write a calibration/adjudication receipt.

## Source and purpose

EconStor (`https://www.econstor.eu`) is the open-access repository operated by the
ZBW – Leibniz Information Centre for Economics. ZBW describes EconStor as an open
access repository for economics literature and a non-commercial public service.
The repository is added as `host_type: repository` for bounded, anonymous,
candidate-bound full-text and rights-page acquisition under the existing OA-1
controls.

The immediate existing-record use case is
`CAND-ACADEMIC-2026-09-08-EXTRA-a6caf5d7567b-002`, *The Economic Impact of
Organized Crime Infiltration in the Legal Economy: Evidence from the Judicial
Administration of Organized Crime Firms*. Candidate-bound retrieval identified
the exact EconStor manifestation
`https://www.econstor.eu/bitstream/10419/216340/1/dp13028.pdf`. The title agrees
with the already registered work. This reviewed host amendment is required before
the repository's byte-level OA acquisition client may fetch that manifestation.

## Data, automation and limits

The existing acquisition client may request only an exact HTTPS URL on the listed
host, with public-DNS validation, TLS hostname verification, a 32 MiB bound,
redirect revalidation and a complete-PDF check. Redirects to unlisted origins,
login/challenge responses, paywalls, non-PDF pages, incomplete bytes and excessive
sizes fail closed. There is no search crawl, domain wildcard, credential, paid
fallback or new scheduler.

A successful byte fetch proves only that exact bytes were anonymously retrievable
and supplies a SHA-256 acquisition observation. It does **not** by itself establish
identity, licence, retention rights, source sufficiency or scientific acceptance.
The caller must still inspect the record/rights evidence and use the governed
private ingestion route with hash/provenance/readback before the source may support
a full-text proposal or calibration case. Full text and rights evidence remain
private; no PDF or long text enters GitHub or Pages.

## Rate/terms risk and first execution

Risk is bounded by one candidate-specific repository manifestation rather than a
crawl. The first approved execution is the exact existing-record manifestation
above, after this amendment is merged and final-head validation is green. A
refusal, challenge, redirect outside the allowlist or ambiguous rights statement
is recorded as a blocker; it does not authorise retries through alternate paid or
credentialled channels.

The source does not enter daily W1–W7 discovery and cannot nominate additional
papers. `CILE-HOUR40-1`, the active private namespace, prior receipts and
calibration history are unchanged.
