# Studio.OS backend verification — 2026-10-17

Scope: isolated studio_os backend on security/prelaunch-hardening-20261017.
The tutorial application remains non-authoritative. No production database, hosted service,
deployment, outbound messaging or paid resource was used.

## Repairs
- Fixed invalid URL imports and missing customer view import.
- Enabled Django sessions and session middleware so configured session authentication works.
- Denied field staff access to customer/inquiry directories and inquiry histories;
  daily actions and completion are restricted to their assignments.

## Working inquiry/action flow
- Create customer, record inquiry, automatically create response action and activity.
- Read inquiry with its action history and recorded activities.
- Today queue includes overdue, undated and remaining local-calendar-day actions;
  completed actions and future dates are excluded.
- Complete an action with a required recorded note and optional paired follow-up title/date.
- Invalid follow-up payload rolls back; repeated completion creates no duplicate follow-up.
- Completion is transactional and locks the action where the database supports row locking.
  Parallel completion guarantees have not been verified on PostgreSQL; SQLite does not
  provide equivalent row locks.

## Verification
Python 3.12, Django 5.2.18, DRF 3.18.3.
- Django system check passes.
- makemigrations --check --dry-run reports no changes.
- Fresh local SQLite database: apply all migrations, unapply operations to zero,
  reapply operations successfully. Rollback was tested only on disposable data.
- Integration tests cover tenant headers, cross-tenant references, private detail/action IDs,
  inactive membership, field assignments, session authentication/CSRF, queue dates,
  completion validation, retries and customer-to-response history.
- Pure domain tests pass separately.

## Boundaries
This is an API development slice, not a finished interface or production launch.
No authentication/login UI, lead-stage mutation, consultation booking, reassignment UI,
communications delivery, quotation acceptance or project conversion is added here.
Workflow completion records the action outcome; it does not invent a lead-stage change.
