# Consultation workflow verification — 2026-10-18

Development branch: security/prelaunch-hardening-20261017.
Source baseline: 9941d30b06ca3f186f708b27771b9380982af8db.

## Implemented
- Isolated Consultation model, company ownership, assignee, visit interval/location,
  explicit status, outcome, version, positive-duration database constraint and index.
- Proposal, confirmation, rescheduling, cancellation, completed outcome and no-show.
- Company/staff availability checks at confirmation; adjacent visits permitted.
- Inquiry advances to CONSULTATION_BOOKED only on confirmation.
- Linked daily action follows visit date/assignment and cannot bypass visit commands.
- Outcomes require notes and cannot be recorded before start. Internal assessment,
  cancellation-review and missed-visit follow-ups are generated once.
- Company isolation, field assignment restrictions, stale edit detection and audit snapshots.
- Lost inquiries cancel active visits and actions; completed history remains.

## Verification
Django system check and migration/model consistency check.
57 isolated Django tests pass, including 21 consultation workflow tests and one migration
rehearsal. All 11 pure domain tests pass separately. Django reports no system issues
and no pending model/migration changes.

Migration 0003 rehearsed from 0002 with existing lead/action data, reversed to 0002 and
reapplied. Existing ownership, action completion/version and inquiry brief preserved.
Reverse migration removes consultation records and links; it is a disposable-data
verification only, not a production rollback plan.

## Limits
No production database, paid services, deployment or external calendar/messages used.
Confirmed-time overlap enforcement is application-level with staff membership row locking
where supported; parallel PostgreSQL requests are not verified by SQLite tests.
Cancelled/no-show visits retain the reached inquiry stage; replacement bookings are explicit.
Assessment records, measurements, quote generation and a usable frontend remain future work.
See studio_os/API_WORKFLOW.md for commands, payloads and permission rules.
