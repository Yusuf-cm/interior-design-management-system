# Team, review register and print controls — 2026-10-29

Branch: security/prelaunch-hardening-20261017
Baseline: 771b838973e2cfc53dffdceef53f641b4bdf0ba5

## Changes
Owner-only teammate account creation, role/access management with membership versions,
last-owner protection, company audit events and preserved assignment history.
Existing accounts cannot be attached/reset by username and no Django admin privileges are
granted. Team passwords are never included in responses or activity records.
Self-service password change verifies current credentials, validates new passwords,
refreshes the current session hash and rotates CSRF. Strong-password validators now apply
to local setup/team creation/password changes; existing passwords are not silently reset.

Added quotation register/search/status filters and consistent pending review count.
Authenticated printable current/archived revisions retain Decimal amounts and labels;
private notes and staff outcomes are omitted. Viewing/printing never changes status.

## Checks
- 119 Django integration/migration tests pass.
- 17 pure domain/pricing tests pass.
- 22 DOM/utility tests pass.
- Django system check, migration consistency and JavaScript syntax checks pass.
- Migration 0005 rehearses forward/reverse/reapply on existing inactive membership data,
  preserving organization, user, role and access state; version starts at one.
- Tests cover owner boundaries, global username collisions, privilege injection, weak
  passwords, other-company access, last-owner handoff, disabled owner accounts, stale edits,
  preserved assignments, reactivation history and self-service password verification.
- Printing tests cover role/company isolation, escaping, internal-note omission, exact totals,
  changed assessments, lost inquiries and preservation of archived revision values.

## Browser verification and limits
A disposable preview used its own SQLite test database. The desktop sign-in screen was
opened and visually inspected in the real browser; static assets and module rendering worked.
Authentication requires secure browser sign-in handoff, so no authenticated browser pass was
completed. Do not treat mock DOM tests as live browser verification. Mobile viewport,
keyboard/focus and native print-dialog checks remain outstanding.

No production data, deployment or paid service used. Temporary QA database/runtime and
credentials are not part of the commit. CI skipped on this commit; checks ran locally.
