# Recorded customer decisions and project work — 2026-10-31

Branch: security/prelaunch-hardening-20261017
Baseline: ca1c5208edfa49b5356b70debd18ccdde4f5ec6b

## Delivered behavior
An owner can record manual sharing and an already-received customer response against a
specific quotation revision. Time, reference and note are required; sharing includes an
explicit future follow-up. These are staff-entered records, not verified message delivery,
agreement signing or a decision made for the customer.

Customer approval advances the inquiry to WON through current shared-revision evidence.
A dormant shared inquiry can follow the same evidence-bearing path; manual stage updates
still cannot claim approval. Changed/declined quotations retain history. Shared prices
cannot be silently revised; requested changes lead to a new reviewed revision.

An incorrect approval record can be corrected by an owner before conversion, retaining
original events and restoring follow-up. Once converted, this path is blocked so accepted
project baselines are preserved. Later changes need a separate scope-change workflow.

Owners can create one internal project per accepted revision/inquiry. Repeated conversion
returns the existing project. Accepted scope and prices remain linked to the preserved
revision. Project owners are active owners/coordinators; optional dates are planning data.

Owners/coordinators plan work, assign active studio staff, pause/resume/cancel projects and
cancel/reopen work with notes. Assigned staff record start, blocker, recovery and completion.
Derived daily tasks stay synchronized and cannot bypass the work workflow. Field project
responses include only assigned items/counts and omit financial/source/history fields.

## Verified
- 156 Django integration/migration tests pass.
- 19 pure domain/pricing tests pass.
- 29 DOM/utility tests pass (mocked API responses).
- Django system, migration consistency and JavaScript syntax checks pass.
- API flow: internally approved quotation -> recorded manual sharing -> recorded customer
  approval -> project plan -> assignment -> start -> blocker -> recovery -> completed work.
- Tests cover event chronology, references, source/version freshness, owner-only decisions,
  retained revision prices, approval corrections, unique conversion, cross-company IDs,
  inactive assignments, field data redaction, task bypass prevention, pause/cancellation,
  history preservation, rescheduled reminders and bounded daily-label lengths.
- Migration 0006 rehearsed forward/reverse/reapply with an existing approved quotation,
  revision amount and completed follow-up. It preserves old status/version/source values
  and creates no customer approval or project. Reverse removes new execution records;
  this is a disposable-data rehearsal, not a production rollback procedure.

## Remaining gates
Handover inspection, project completion, scope-change approval and aftercare are not
implemented in this slice. Completing work items does not complete the project.
Work planning does not amend the accepted quotation, purchase materials or hire anyone.
Authenticated/mobile browser QA and PostgreSQL concurrency remain unverified; existing
API/DOM checks are not substitutes for those tests.

No production database, deployment, outgoing communication or paid service used.
CI is skipped on the commit to avoid runner charges; checks above ran locally.
