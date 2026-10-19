# Assessment-to-estimate implementation and verification

Date: 2026-10-19
Branch: security/prelaunch-hardening-20261017
Baseline: 6c4e8fcbd7640e4621ab9223bd02c5fe96d247ae

## Result
A completed visit now leads to structured site observations, explicit measurement
completeness checks, a versioned internal quotation and owner review.

Assessments retain unknown measurements and optional owner-authorized preliminary-estimate
reasons. Reopening revokes approval and requires a refreshed quotation revision.
Quotation revisions preserve scope, notes, dimensions, exception, currency, line prices
and computed totals. Money uses Decimal with explicit per-line/tax half-up rounding.
No payment, contract, outbound message, acceptance or project conversion is implemented.

Stable origin keys connect new workflow tasks to their assessment/quotation actions.
They close/reopen with source state, are unique per company, and cannot bypass review
through generic task completion. Existing tasks are preserved without guessing origins.

## Verification performed
- Django system check: no issues.
- makemigrations --check --dry-run: no changes detected.
- 86 Django integration/migration tests pass.
- 17 pure domain/pricing tests pass.
- Complete API scenario: customer -> inquiry -> contacted -> qualified -> booked visit ->
  completed visit -> assessment -> ready -> draft quotation -> submitted -> internally approved.
- Cross-company object access, field staff restrictions, inactive membership, stale edits,
  missing dimensions, provisional authority and source changes tested.
- Monetary tests cover fractional rounding, discounts/tax, zero values, invalid rates,
  nonfinite inputs, size limits and preservation of original revision values.
- Migration 0004 rehearsed forward/reverse/reapply on disposable existing visit/action data.
  Earlier consultation migration tests now use historical models so future fields do
  not invalidate their verification.
- Existing ownership, consultation outcomes, task completion and versions survive migration.
  Reverse removes this slice's assessment/quote data; this is not a production rollback plan.

## Practical boundaries
The verified path is an API workflow, not a completed user interface.
No deployment, production database or paid resources used. CI is skipped on this commit
to avoid runner charges; the checks above were run locally.
No file uploads, PDFs, customer portal or external calendar added.
PostgreSQL concurrency and backup/restore drills remain unverified; SQLite tests validate
transactions and sequential stale-write detection.
Measurement plans and line prices are staff-entered; dimensions, rates and budgets
are not invented by automation.
