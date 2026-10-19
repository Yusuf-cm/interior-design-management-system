# Connected workspace verification — 2026-10-19

Branch: security/prelaunch-hardening-20261017
Baseline: bed3a52299dc4faf8ea795e2d53cee4c496dff6f

## Delivered
Same-origin Django workspace with session sign-in/out, active company selection and
scoped staff context. Vanilla JavaScript/CSS; no runtime Node build or external assets.

Screens cover Today, customer directory, inquiry register/search, inquiry details and
history, visit scheduling/outcomes, structured assessment entry/readiness, quotation
line editing, revision history and owner review. Forms send existing API contracts and
versions; server errors retain entered data. Company changes discard displayed records.
Scheduling explicitly uses Nairobi time and monetary strings retain decimal precision.

Local setup prompts for credentials and creates an owner membership, not a Django
superuser. Default/demo passwords are not embedded. Development SQLite data is ignored.

The interface exposed a handoff gap: assessment preparation after a field visit was
assigned to field staff who could not access assessments. It now routes to active office
staff or remains unassigned for office review. Designers also cannot take over another
staff member's visit through rescheduling.

## Checks
- 100 backend integration/migration tests pass.
- 17 pure domain/pricing tests pass.
- 17 DOM/utility tests pass (jsdom; mocked API responses).
- Django system check: no issues; migration/model check: no changes.
- JavaScript module syntax checks pass.
- Session tests cover CSRF-protected login/logout, token rotation, active company scoping,
  inactive accounts/memberships, cookie flags, staff restrictions and actual authenticated writes.
- DOM tests cover sign-in, queue navigation, company switching, escaped customer content,
  inquiry submission, stale edits, unknown dimensions, decimal line values, quote details,
  role-specific approval controls and failed data loads.

## Limits
Browser automation is unavailable here. No real-browser visual, keyboard-focus or mobile
viewport QA was performed. DOM tests do not establish visual layout correctness or replace
an end-to-end real-browser test against Django. The main existing API workflow test still
covers inquiry through reviewed estimate using the actual database.

No production database, deployment or paid service used. CI is skipped on the commit;
checks were run locally. Production security and hosting remain separate work.
