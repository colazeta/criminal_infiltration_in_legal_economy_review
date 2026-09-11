# Hour-40 enrichment: delivery and completion contract

Owner mandate: 11 September 2026. Protocol `CILE-HOUR40-1`; semantic profile `0.4.1`.
This is an additive change to the existing private enrichment service. It does not reset
candidates, research sources, proposals, prior attempts or the existing storage namespace.

## Plan, ticket, attempt, result

`40 * * * *` is the configured Cloudflare Cron Trigger in UTC. In Rome/Frankfurt,
which have whole-hour UTC offsets, the minute remains :40 through daylight-saving
changes. This is a planned start, not a guarantee of exact wall-clock execution:
a late provider trigger or a still-running predecessor can delay the actual start.

At first verified activation, persist the first slot at or after activation and a
watermark for the next unmaterialised slot. Do not invent execution records for
hours before activation. Each due slot obtains a unique persistent ticket keyed
by schedule and UTC epoch milliseconds. Store the planned time, actual insertion
time, status, attempts, lease, actual start/finish and processor receipt separately.
An outage recovery records later materialisation, never a backdated invocation.

Every callback materialises due tickets **before** checking whether another
attempt is busy. Ticket insertion and watermark advance are one transaction.
Catch-up is paged in blocks of 168 slots with no truncated retention window: the
cursor advances only as far as inserted slots. Duplicate deliveries insert nothing.

The existing 15-minute supervisor and a Durable Object alarm recover missed
callbacks. The explicit :40 cron and the alarm can both arrive; idempotent tickets
prevent double work. The alarm is persisted before processing network work. When
work releases its lease, pending work receives an immediate alarm (approximately
one second later, subject to platform delivery), not a wait for the next full hour.

A live invocation is not cancelled or stolen. A database uniqueness constraint
prevents two active tickets. After a crash, reconcile any already completed
processor receipt before retrying: this avoids selecting a second paper when
only the acknowledgement was lost. Otherwise retain the interrupted attempt and
create a new fenced attempt. Stale tokens cannot acknowledge a newer attempt.
Infrastructure/lease failures return the ticket to pending with bounded exponential
backoff. Every terminal attempt is immutable. No ticket or attempt is deleted.

## What counts as completion

A ticket authorises one bounded operation in the existing work queue. The processor
may complete metadata, checkpoint a citation page, or establish that no job is due.
Those are distinct from having fully extracted or scientifically verified a paper.
A provider or identity failure for a selected paper is an explicit failed ticket
with the retained paper-job outcome, not successful enrichment. A failure before
any paper operation leaves the ticket pending for recovery.

The minute-40 delivery layer does not remove the scientific calibration gate.
Abstract-only pilot output stays labelled `abstract_only` and unreviewed. The pilot
generation schema now requires a non-null source-backed rationale whenever it
proposes a clinical category; abstention remains available. The native validator
still rejects ungrounded classification. No acceptance criterion is weakened to
turn a failed pilot into a green run.

## Ontology and storage

Migration `0004_enrichment_schedule.sql` adds three operational tables:
`enrichment_schedules`, `enrichment_iterations`, `enrichment_iteration_attempts`.
The original 0003 migration and all its hashes are unchanged. Both the normative
profile and `modules/review-v2.json` map the new classes/fields. The focused
`modules/enrichment-schedule.json` states their temporal and delivery semantics.
The public model explorer contains schema definitions only, never private tickets
or source/proposal text. The authenticated enrichment screen displays ticket history.

## Verification and limits

Deterministic tests cover boundaries at :39:59/:40:00, duplicates, concurrency,
long-running overlap, crash recovery, lost acknowledgement, old-token fencing,
immutable terminal attempts, reactivation and 401 overdue slots. These use an
in-memory database and a controlled clock. They are not observations of 401 real
production hours or substitutes for subsequent live :40 receipts.

Live deployment must separately demonstrate migration readback, the activation
receipt, current schedule configuration, real processor effects and later scheduled
tickets. The 12–18-paper content benchmark and scientific acceptance remain a
separate gate; passing software tests is not a claim of extraction accuracy.

Rollback: deactivate the existing master runner or use the authenticated pause
operation; retain storage, tickets, watermarks and evidence. Never delete tables or
reset the first-slot epoch to hide an outage. Reactivation resumes the retained queue.
