# Studio.OS domain and acceptance specification v1

Status: proposed design, not implemented or validated with customers. Target: small interior-design studio. No binding commitments, payments processing, contractor hiring, or automatic outbound communications.

## 1. Domain entities and relationships
- Organization (id, name, currency, timezone); Membership (organization, user, role, active). Every business-owned record has organization_id.
- Customer (organization, name, contacts, preferences, archived_at). A customer can have many Leads, Projects and Activities.
- Lead (organization, customer, source, brief, stage, owner, next_action_at); Consultation (lead, scheduled_at, location, outcome); Assessment (consultation, notes, measurements, attachments, completeness).
- Quote (organization, lead, customer, status, current_revision_id); QuoteRevision (quote, revision_number, line_items snapshot, subtotal, adjustments, tax, total, currency, issued_at, accepted_at). Issued revisions are immutable.
- Project (organization, customer, accepted_quote_revision nullable, status, owner, dates); WorkItem (project nullable, lead nullable, assignee, status, due_at, dependency); ProjectMilestone; ProgressUpdate; ChangeRequest; Issue; MaterialRequest; SupplierReference.
- Activity (organization, actor, subject_type, subject_id, event_type, before/after summary, occurred_at); NextAction (organization, subject, assignee, due_at, status, origin_event_id).
- Document (organization, linked subject, file metadata, version); MessageDraft (recipient, channel, text, approval_status, approved_by); DeliveryAttempt (draft, provider id, status, error); RecordedPayment (project, amount, date, verification_status, reference); Handover (project, checklist, status); AftercareRequest (project, status, due_at).
- WorkflowEvent (organization, type, subject, payload, idempotency_key, occurred_at); WorkflowRun (event, rule, status, attempts, last_error).

## 2. State machines and transitions
### Lead
NEW -> CONTACTED -> QUALIFIED -> CONSULTATION_BOOKED -> ASSESSED -> QUOTED -> WON. NEW/CONTACTED/QUALIFIED/QUOTED may -> LOST or DORMANT. DORMANT -> CONTACTED. WON requires a linked accepted quote; repeated WON action must not duplicate a project. Declined/unqualified leads use LOST with reason, not deletion.
### Consultation
PROPOSED -> CONFIRMED -> COMPLETED. PROPOSED/CONFIRMED -> RESCHEDULED -> CONFIRMED; CONFIRMED -> CANCELLED or NO_SHOW. COMPLETED requires outcome notes; no automatic quotation acceptance.
### Assessment
DRAFT -> READY_FOR_ESTIMATE; READY_FOR_ESTIMATE -> REOPENED -> READY_FOR_ESTIMATE. Missing required measurements block READY_FOR_ESTIMATE, but owner can document an explicit provisional estimate exception.
### Quote
DRAFT -> READY_FOR_REVIEW -> APPROVED_TO_SHARE -> SENT -> ACCEPTED/REJECTED/EXPIRED. SENT -> REVISION_REQUESTED -> DRAFT (new revision). No silent edits to issued revisions. APPROVED_TO_SHARE is internal review, ACCEPTED is customer acceptance recorded by an authorized person. No legal signing automation.
### Project
PLANNED -> ACTIVE -> PAUSED -> ACTIVE; ACTIVE -> READY_FOR_HANDOVER -> COMPLETED -> AFTERCARE. PLANNED/ACTIVE/PAUSED -> CANCELLED with reason. READY_FOR_HANDOVER -> ACTIVE if snag items remain. COMPLETED requires handover review, not simply all tasks checked.
### Work item
TODO -> IN_PROGRESS -> BLOCKED -> IN_PROGRESS -> DONE; DONE -> REOPENED -> IN_PROGRESS; TODO/IN_PROGRESS/BLOCKED -> CANCELLED. Dependencies block DONE where configured. Preserve correction history.
### Change request
PROPOSED -> ESTIMATED -> AWAITING_REVIEW -> APPROVED/REJECTED/WITHDRAWN. Only APPROVED may alter planned scope, and the original quote remains unchanged.
### Outbound draft
DRAFT -> READY_FOR_REVIEW -> APPROVED -> SENT/FAILED. FAILED -> READY_FOR_REVIEW or RETRY_PENDING only if owner permits. Opt-out blocks APPROVED/SENT. Preparing a draft never means it was sent.
### Handover and aftercare
Handover DRAFT -> INSPECTION -> SNAGGING -> INSPECTION -> ACKNOWLEDGED/CLOSED_WITH_NOTES. Aftercare OPEN -> TRIAGED -> ASSIGNED -> RESOLVED -> CLOSED; RESOLVED -> REOPENED.

## 3. Roles and permissions
- Owner/admin: manage organization, users, records, workflow settings; approve sharing and sensitive changes.
- Coordinator: leads, scheduling, tasks, draft communications; cannot change roles or approve financial commitments unless explicitly granted.
- Designer/estimator: assessments, designs, quote drafts and revisions; cannot unilaterally mark customer acceptance.
- Field staff: assigned tasks, progress, photos and issues; no access to unrelated private customer or finance data.
- Customer portal (future): only explicitly shared own-project data; never internal notes, other customers, staff finance or unapproved estimates.
- Server derives organization scope from authenticated membership. Never trust client-submitted organization_id, role, creator or approval actor. Check object permissions on reads, updates, exports, attachments and background jobs.

## 4. Workflow automations and approval boundaries
1. Lead created -> create response NextAction; suggest duplicate contacts; no outbound message.
2. Consultation confirmed -> prepare staff reminder; scheduling conflict flagged before confirmation.
3. Assessment ready -> enable quote draft from recorded scope; missing measurements highlighted.
4. Quote revision calculated -> calculate totals deterministically; owner review before share.
5. Quote accepted -> prepare project conversion; unique constraint on accepted_quote_revision prevents duplicates; preserve linkage.
6. Work item blocked/delayed -> surface on daily queue and prepare optional update draft.
7. Progress updates recorded -> prepare owner-editable customer summary, never claim unreported progress.
8. Payment recorded -> update *recorded* balance; unverified payments are excluded from confirmed totals.
9. Project ready for handover -> prepare checklist; unresolved snag items block ordinary completion.
10. Project completed -> propose aftercare reminder and review request only when appropriate.
11. Task completed -> cancel stale reminders at execution time, not just when scheduled.
12. Any automation failure -> retry safely when possible, log attempts, surface persistent failures to owner.

## 5. Acceptance tests (Given / When / Then)
| ID | Given | When | Then |
|---|---|---|---|
| AT01 | New inquiry with missing budget | Coordinator saves lead | Lead saved and next action created; no fabricated budget |
| AT02 | Existing customer email/phone | Second inquiry recorded | Possible duplicate flagged; history retained; no automatic merge |
| AT03 | Staff booked at 11:00 | Another overlapping visit requested | Conflict shown before confirmation |
| AT04 | Assessment missing a required dimension | User marks it ready | Validation blocks, or documented provisional exception recorded |
| AT05 | Quote has material 1000 and labor 500 | Draft calculated | Total computed by decimal arithmetic using configured adjustments |
| AT06 | Quote revision 1 was issued | Supplier changes rate | New revision created; issued revision 1 unchanged |
| AT07 | Quote not internally approved | User attempts to send | Action rejected and draft remains unsent |
| AT08 | Accepted quote revision | Project conversion invoked twice | Exactly one linked project exists |
| AT09 | Staff from organization A | They request org B customer/job/file | 403 or 404, with no leaked fields |
| AT10 | Regular staff account | Role/admin flag changed in profile request | Privilege escalation rejected |
| AT11 | Client asks for extra wardrobe | Field worker records request | Change request created, scope/budget unchanged until review |
| AT12 | Supplier delivery delayed | Coordinator records blocker | Dependent work flagged and update draft prepared, not sent |
| AT13 | Worker has stale task data | Update arrives after owner changes task | Conflict surfaced; no silent overwrite |
| AT14 | Client reports unverified deposit | Staff enters it | Marked unverified, not counted as confirmed receipt |
| AT15 | Payment reference already recorded | Same reference added again | Duplicate flagged for human review |
| AT16 | Client disputes an amount | Reminder becomes due | Reminder withheld pending review |
| AT17 | Task marked complete | Old scheduled reminder executes | Reminder cancelled/skipped after current-state check |
| AT18 | Draft client update prepared | No approval given | No external message transmitted |
| AT19 | Client opted out | Reminder is approved | Delivery blocked; preference respected |
| AT20 | Document generation fails | User retries | Same revision and source data retained; no phantom document |
| AT21 | Project has open snag items | Owner attempts ordinary completion | Blocked or documented override with reason and audit trail |
| AT22 | Aftercare request created | Staff resolves and client reopens | History preserved and status reopens |
| AT23 | Employee deactivated | They attempt login/access | Access denied and assignments remain visible for reassignment |
| AT24 | Automation event delivered twice | Rule executes | Idempotent outcome, single NextAction/document/project as applicable |
| AT25 | Two staff edit same quote revision | Second saves stale version | Conflict detected; issued version unchanged |
| AT26 | Owner searches old client | Query by project, name or date | Related quotes, visits, tasks and activity history retrievable |
| AT27 | Project cancelled | Customer returns later | Historical project preserved; new lead can link to customer |
| AT28 | Owner opens daily dashboard | Overdue tasks and pending reviews exist | Prioritized action queue shows accurate assignee and status |
| AT29 | Organization has many records | User requests export | Only authorized tenant records exported |
| AT30 | Customer requests an after-hours update | Inquiry recorded | Internal follow-up queued without promising immediate reply |

## 6. Non-functional gates
- Tests for all state transitions, authorization checks, money calculations, and duplicate event handling.
- Query-level tenant isolation, including dashboard aggregates and document downloads.
- Data minimization and clear retention/deletion policy before production customer data.
- Logs and audit trail distinguish proposed, approved, attempted and delivered actions.
- Backup and restore drills; no production rollout before migrations and rollback strategy are verified.
- Pilot measures time spent entering data, preparing quotes, searching history, and handling follow-ups; compare against manual baseline.

## 7. Engineering order
A. Inventory current Django models and migrations; add characterization tests for existing behavior.
B. Add Organization/Membership and scope existing customers/jobs/dashboard, with migration and role compatibility tests.
C. Introduce Lead, Consultation, Assessment, Activity and NextAction; build daily action queue.
D. Add Quote/QuoteRevision and deterministic calculation; accepted quote -> project conversion.
E. Add project execution and aftercare records, then notification drafts and workflow jobs.
F. Run scenario-based end-to-end tests and usability pilot. No live outbound communications or paid services without separate authorization.

## 8. Open questions for customer validation (not blockers for specification)
How many quotes are produced weekly? Who records site measurements? Which tasks are currently lost in WhatsApp? How many people need access? What information should field workers see? Which customer messages should remain fully manual? What pricing model feels worthwhile relative to hours saved?
