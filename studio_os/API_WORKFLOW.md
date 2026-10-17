# Inquiry and daily action API

Development API only. Authenticated Django session and active membership required.
Every route requires X-Organization-ID. POST/PATCH session requests require a valid CSRF
token. There is no login UI or outbound delivery integration in this slice.

| Method | Route | Behavior |
| --- | --- | --- |
| GET/POST | /api/customers/ | Office staff list/create customers in selected company |
| GET/POST | /api/leads/ | Office staff list/create inquiries; creation adds response action |
| GET | /api/leads/{id}/ | Office staff read inquiry, actions and activity history |
| POST | /api/leads/{id}/transition/ | Office staff record an allowed stage change and note |
| POST | /api/leads/{id}/actions/ | Office staff plan another action |
| GET | /api/today/ | Open actions due before next local midnight, including overdue/undated |
| PATCH | /api/actions/{id}/ | Owner/coordinator changes assignment, title or due date |
| POST | /api/actions/{id}/complete/ | Complete assigned work with note and optional follow-up |

Owner/coordinator can assign active colleagues in the same company. Designers can
create actions for themselves. Field staff see and complete only their assigned actions;
they cannot list customer/inquiry directories, plan new actions, or reschedule work.
The queue orders dated work earliest first, followed by undated work.
Future work remains visible in inquiry detail.

## Stage changes
POST transition payload:
```json
{"expected_version": 1, "status": "CONTACTED", "note": "Customer described their living room"}
```
The response includes the new version. NEW -> CONTACTED -> QUALIFIED is supported.
NEW/CONTACTED/QUALIFIED can become LOST or DORMANT; DORMANT can return to CONTACTED
or become LOST. A nonblank note is required for every change. LOST cancels open actions
and preserves completed work/history. DORMANT preserves follow-ups for a later revisit.
Consultation, assessment, quotation and won stages cannot be set through this endpoint;
their evidence-bearing workflows must be implemented first.

## Plan and update actions
POST /api/leads/{id}/actions/:
```json
{"title": "Call about measurements", "due_at": "2026-10-20T10:00:00+03:00", "assignee": 4}
```
Assignee defaults to caller. due_at is required, but null explicitly means undated.
Historical/overdue dates are accepted when planning or correcting work.

PATCH /api/actions/{id}/:
```json
{"expected_version": 1, "note": "Customer requested tomorrow", "due_at": "2026-10-21T10:00:00+03:00"}
```
Title, due_at and assignee are individually optional; at least one must be supplied.
Version and nonblank note are always required. Completed/cancelled actions cannot be edited.
Closed inquiries cannot receive new actions.

## Complete and follow up
POST completion:
```json
{"expected_version": 2, "note": "Customer will send measurements",
 "follow_up_title": "Check measurements arrived", "follow_up_due_at": "2026-10-22T10:00:00+03:00"}
```
Both follow-up fields are optional together; the follow-up date must be in the future.
Follow-up inherits the action assignee, who must still have active membership.
The entire operation rolls back on invalid follow-up data.
Repeating completion of an already completed action returns its current state without
another note or follow-up. A different desired action must use the planning endpoint.
Completion does not automatically change inquiry stage or send a message.

## Conflicts and audit
Read responses include version. Stage changes, action edits and first completion require
expected_version. A stale value returns 409; refresh and review before resubmitting.
Invalid transitions/payloads return 400; unavailable company membership returns 403;
cross-company detail/action IDs return 404. Cancellation and closed-action changes return 409.
Changes record the authenticated actor and note. Action edits retain before/after snapshots.
Row locks use a consistent lead-first order where supported; parallel-request behavior
on PostgreSQL has not been tested. SQLite verification covers sequential stale edits.
