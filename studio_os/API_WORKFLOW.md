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

## Consultation scheduling
| Method | Route | Behavior |
| --- | --- | --- |
| GET | /api/consultations/ | Office staff list company visits; field staff see assigned visits |
| POST | /api/leads/{id}/consultations/ | Propose a site visit for qualified/booked inquiry |
| POST | /api/consultations/{id}/command/ | Confirm, reschedule, cancel, complete or record no-show |

Create proposal:
```json
{"starts_at": "2026-10-22T10:00:00+03:00", "ends_at": "2026-10-22T11:00:00+03:00",
 "location": "Customer site", "assignee": 4}
```
Dates must be in the future, with end after start. Assignee must be an active user with
active membership in the company. Owners/coordinators can assign colleagues; designers
can propose visits for themselves.

Proposals do not reserve time or advance the inquiry.
Confirm with:
```json
{"expected_version": 1, "command": "confirm", "note": "Staff and customer agreed to this visit"}
```
Confirmation blocks overlaps with that assignee's confirmed visits in the selected company.
The interval uses start-inclusive/end-exclusive boundaries, so adjacent visits are allowed.
Conflict errors contain no other customer's details. Availability is company-scoped;
this does not inspect other companies or an external calendar.

Confirmation changes QUALIFIED to CONSULTATION_BOOKED and creates one linked visit action.
Generic action completion/rescheduling endpoints reject linked visit actions, which must
be managed through this workflow.

Reschedule requires all four scheduling fields plus expected_version, command=reschedule
and a nonblank note. It records the old/new plan, releases the old confirmed slot, and
cancels the visit action until re-confirmation. Re-confirmation checks availability again.
Only PROPOSED/RESCHEDULED visits can be confirmed.

Cancel requires expected_version, command=cancel and note. Proposed, confirmed and
rescheduled visits may be cancelled. The action is cancelled and an internal review
follow-up is created.

Complete/no_show require a confirmed visit, its current expected_version and nonblank
note. Outcomes cannot be recorded before the start time. Assigned field staff can record
outcomes; only office staff can schedule, confirm, cancel or reschedule.
Completion stores outcome notes, completes the visit action and adds an assessment
preparation action. No-show cancels the visit action and creates a missed-visit follow-up.
Terminal commands reject retries with 409 and do not duplicate follow-ups.

Completing a visit does not mark an inquiry ASSESSED. CONSULTATION_BOOKED denotes the
inquiry stage reached; cancelling/no-show does not erase this historical stage. A
replacement visit can be proposed. Losing an inquiry cancels all nonterminal visits
and open actions in the same transaction, without erasing completed visit history.

Visit history appears in inquiry detail. Scheduling changes record actor, reason and
before/after snapshots. Row locking serializes confirmations per staff membership on
databases supporting it; concurrent PostgreSQL requests have not been tested locally.

## Site assessment and internal quotation drafting

| Method | Route | Behavior |
| --- | --- | --- |
| POST | /api/consultations/{id}/assessment/ | Record one assessment for a completed visit |
| GET/PATCH | /api/assessments/{id}/ | Read or edit draft/reopened observations |
| POST | /api/assessments/{id}/command/ | Mark ready or reopen for correction |
| POST | /api/assessments/{id}/quote/ | Create first internal quotation revision |
| GET | /api/quotes/{id}/ | Read current draft and revision history |
| POST | /api/quotes/{id}/revisions/ | Append a new revision and revoke prior approval |
| POST | /api/quotes/{id}/review/ | Submit, approve sharing internally, or return to draft |

Only active office memberships can use these routes. Field staff cannot read quotation
amounts, assessments or internal review records. Company ownership is derived from the
header and membership; unavailable cross-company IDs return 404. Closed inquiries reject
mutations but retain history.

### Assessment content
POST assessment:
```json
{"scope": "Paint living room walls",
 "notes": "Protect existing flooring",
 "measurements": [
   {"label": "Living room length", "value": "4.200", "unit": "m", "required": true},
   {"label": "Living room width", "value": null, "unit": "m", "required": true}
 ]}
```
A null measurement is explicitly unknown. Labels must be distinct. Values are positive
decimals with up to three places. Units: mm, cm, m, m2, count. At most 100 entries.
Scope/notes can be incomplete in a draft. PATCH accepts scope, notes and/or the full
measurement list, and requires expected_version plus a nonblank note.

POST command:
```json
{"expected_version": 1, "command": "ready", "note": "Checked site observations"}
```
Readiness requires a nonblank scope, at least one required measurement, and values for
all required measurements. Responses include missing_information rather than inventing
dimensions. Only an owner may supply provisional_reason to authorize a preliminary estimate
despite missing measurements; scope itself cannot be omitted. The exception remains visible
and is copied into quotation snapshots. There is no assumed measurement checklist:
the studio must explicitly identify the measurements required for this job.

Ready assessments cannot be edited. Use command=reopen with current version/note, then
PATCH and mark ready again. Reopening clears the exception, revokes review/approval of
the related quotation and requires a fresh revision before resubmission. Lead ASSESSED
records the stage reached; current readiness is always checked on the assessment itself.

### Quotation draft and revisions
POST first draft:
```json
{"expected_assessment_version": 2,
 "items": [{"description": "Paint", "quantity": "2.000", "unit_price": "1000.00"},
           {"description": "Labour", "quantity": "1.000", "unit_price": "500.00"}],
 "discount": "100.00", "tax_rate": "0.160000"}
```
The tax rate above is only an arithmetic example, not a configured tax rule.
Discount and rate default to zero. Currency is copied from the organization and retained
by all revisions of that quotation. Client-supplied totals/currency/status/organization
cannot override server calculations and ownership.

Each line amount rounds quantity × unit price to two places using ROUND_HALF_UP.
Subtotal is the sum of rounded line amounts. Tax is rounded after subtracting the discount.
Total = subtotal - discount + tax. Discount cannot exceed subtotal; rate must be 0–1.
One to 100 lines; positive quantities, nonnegative prices. Decimal precision/size limits
are validated. All response monetary values are decimal strings.

One quotation exists per assessment. A second create request returns 409. POST revisions
uses the same calculation payload plus expected_version for the quotation and a note.
Every revision snapshots scope, notes, measurements, exception, currency and totals.
Old revisions remain unchanged. Model instance saves reject updates to existing revisions;
the API exposes no revision mutation/delete route. This is application-level immutability,
not a database trigger against arbitrary direct SQL writes.

A quotation's source_current flag reports whether its current revision matches the
current ready assessment. A source version mismatch prevents submission and approval.
New revisions always return the quotation to DRAFT and require review again.

### Internal review
POST review:
```json
{"expected_version": 1, "command": "submit", "note": "Ready for owner review"}
```
submit moves DRAFT to READY_FOR_REVIEW and queues one task for an active owner.
approve requires an owner, a current assessment snapshot, a current quotation version
and READY_FOR_REVIEW status. It sets APPROVED_TO_SHARE and completes the review task.
return_to_draft withdraws a pending/approved draft and cancels its pending review task.
Retries with stale versions return 409 without duplicate reviews or revisions.

Approval is an internal record only. Sending, signature and payment endpoints do not exist. Internal approval does not mark
an inquiry QUOTED or WON. Owner-recorded sharing/customer responses and project conversion
use the dedicated endpoints below.

### Workflow tasks
New assessment-preparation, estimate-preparation, recheck and owner-review tasks have
server-generated origin_key values unique within their company. Their source workflows
settle/reuse them instead of duplicating reminders. Generic action completion rejects
these tasks, preventing manual completion from bypassing assessment/review requirements.
Existing tasks without a reliable origin remain unchanged during migration; they are
not guessed or matched by title.

Reopening a source revokes quotation approval with an explicit audit event. Losing an
inquiry revokes pending/approved quotations, cancels open tasks and records affected
quotation IDs in its stage-change audit.

## Workspace session and staff context
The local interface is served at /. Same-origin session endpoints:
- GET /api/session/: CSRF token, authentication state and the signed-in user's active
  company memberships. Anonymous callers receive no company data.
- POST /api/session/login/: username/password; requires the bootstrap CSRF token.
  Successful login rotates the token and returns updated session context.
- POST /api/session/logout/: requires CSRF, clears authentication and returns anonymous context.
- GET /api/staff/: active office members read active assignee IDs/names/roles in the
  selected company only. Field staff cannot read the directory.

Workspace/session responses are marked no-store. Browser requests opt out of caching and
send credentials to the same origin only. Only the non-secret company preference is kept
in sessionStorage. Cookie sessions use HttpOnly and SameSite=Lax; local settings are not
production HTTPS/authentication configuration.

Designers cannot reschedule/reassign another staff member's consultation to themselves.
Completed field visits route assessment preparation to active office staff, or leave it
unassigned for office review when no office membership exists.

## Owner team management
- GET/POST /api/team/: owners list studio memberships or create a new account/membership.
  Creation fields: username, name, role, password. Existing usernames return 409 without
  attaching or changing the account. Password is write-only and never audited.
- PATCH /api/team/{membership_id}/: owner supplies expected_version, note, and role
  and/or active. Cross-company IDs return 404. Last-active-owner removal returns 409.
- Responses include membership id, user_id, username, name, role, active, version,
  account_active and company-scoped open_actions count. Deactivation preserves work.
- POST /api/session/password/: authenticated cookie session and CSRF required. Supply
  current_password/new_password. Validated change rotates CSRF and refreshes the current
  session hash; returns updated session bootstrap. No username/password reset targeting
  another account is supported.

Membership edits lock the company before checking owner availability where row locking
is supported, and use version comparison. PostgreSQL concurrency is still unverified.

## Quotation register and printable copies
- GET /api/quotes/: office members receive studio-scoped estimates with lead and
  customer_name. Optional status accepts a current Quote.Status value, including DRAFT,
  READY_FOR_REVIEW, APPROVED_TO_SHARE, SENT, ACCEPTED, REJECTED or REVISION_REQUESTED.
- GET /quotes/{id}/print/?organization={company_id}: authenticated office-only printable
  current revision. Optional revision={number} selects an archived revision belonging to
  the same quotation/company. Another company's IDs remain unavailable.
- Print responses are no-store. Only a current approved revision with a ready/current
  assessment and non-lost lead receives the discussion-copy label. All other copies are
  internal drafts or archived revisions. Internal notes/visit outcomes are never included.
- Print is a read-only browser page. There is no issuing, sending or acceptance side effect.


## Recorded quote events (staff-entered history only)
POST /api/quotes/{id}/events/ is owner-only. Fields: expected_version, kind, occurred_at,
reference, note. Kinds: SHARED, ACCEPTED, REJECTED, REVISION_REQUESTED. SHARED additionally
requires future follow_up_due_at. These routes send/sign nothing and do not independently
verify a customer communication. Event time must be past/current and not predate the
revision's creation minute. Responses cannot predate recorded sharing.

SHARED requires current approved source/revision, records SENT and moves ASSESSED to
QUOTED. A response requires SENT. ACCEPTED records WON only with current shared-revision
evidence and a quoted/dormant inquiry; manual stage updates cannot claim acceptance.
REJECTED records decline and queues internal review without automatically closing the
whole inquiry. REVISION_REQUESTED enables a new immutable revision from customer feedback.
SENT/ACCEPTED cannot be silently revised. Customer events and their references are returned
in quotation detail, preserving prior responses across revisions.

POST /api/quotes/{id}/approval-correction/ is owner-only. Supply expected_version,
reference, note and future follow_up_due_at. It corrects an ACCEPTED record only while
no project exists, appends APPROVAL_CORRECTED, returns the quote to SENT and inquiry to
QUOTED, and restores follow-up. Original events remain. After conversion this is blocked.

Quote responses include project_id and customer_follow_up (id/time/version/assignee_id).
Owners/coordinators may reschedule the internal reminder via ordinary action PATCH;
it does not create another customer event. Version conflicts reject stale retries.

## Projects and assigned work
| Method | Route | Scope |
| --- | --- | --- |
| POST | /api/quotes/{id}/project/ | Owner converts recorded accepted revision once |
| GET | /api/projects/ | Office: studio projects; field: assigned projects only |
| GET | /api/projects/{id}/ | Project baseline/history for office; field data redacted |
| POST | /api/projects/{id}/command/ | Owner/coordinator: start, pause, resume, cancel |
| POST | /api/projects/{id}/work/ | Owner/coordinator plans work |
| GET/PATCH | /api/work/{id}/ | Assigned field/office reads; manager edits planning |
| POST | /api/work/{id}/command/ | Assigned staff progress; manager cancels/reopens |

Conversion fields: expected_version (quote), title, owner (active owner/coordinator),
optional start_date/target_date and note. The quote must have an ACCEPTED event for its
current revision and a WON inquiry. Unique accepted-revision and inquiry links prevent
duplicate projects. Repeated conversion returns the existing project (200); first use 201.

Project command fields: expected_version, command, note. PLANNED -> start -> ACTIVE;
ACTIVE -> pause -> PAUSED -> resume -> ACTIVE. Cancel preserves completed work and cancels
open work/reminders. Completion/handover is deliberately gated behind future workflows.

Work creation fields: title, optional description, assignee (active studio user or null),
due_at (datetime or null), note. Planning PATCH requires expected_version/note and at least
one editable field. Completed/cancelled work must be reopened before planning changes.

Work commands require expected_version, command, note: start (TODO -> IN_PROGRESS), block
(TODO/IN_PROGRESS -> BLOCKED), unblock (BLOCKED -> IN_PROGRESS), done (IN_PROGRESS -> DONE),
cancel, reopen. Start/unblock/done require an ACTIVE project. Cancel/reopen require a
manager. Project cancellation prevents further updates. Blocker notes are retained as
current blocker_reason and all transitions are audited with actor/project/work references.

Work reminders have a unique work_item link and stable origin. They are synchronized from
work state; generic task completion/editing cannot bypass the work workflow. Field project
responses omit accepted prices/currency, quotation/revision links, full accepted scope and
project audit history, and include only that person's assigned items/counts. Office users
can read studio work; non-managers can progress only their own assignment.

Project/quote/work ownership is always server-derived. Source snapshots remain unchanged;
work planning does not authorize extra scope, purchase materials or hire contractors.
