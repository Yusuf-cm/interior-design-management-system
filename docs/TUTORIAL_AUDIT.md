# Studio.OS tutorial code audit and replacement plan

Status: repository source review only, not runtime verification. Reviewed branch: security/prelaunch-hardening-20261017 (2026-10-17).

## Disposition matrix
| Existing component | Decision | Evidence and reason | Replacement |
|---|---|---|---|
| Django 5 / DRF stack | REUSE technology | Suitable for relational workflow APIs; no requirement to retain tutorial app layout | New domain modules with scoped services and tests |
| React/Vite/Mantine | REUSE technology | UI toolkit can serve mobile-friendly workspace | New navigation and task-first screens |
| accounts.User with role admin/STAFF | REWRITE | Global role, inconsistent case, no organization membership | Identity plus Organization/Membership with scoped roles |
| accounts.RegisterView | REWRITE | Checks global admin string rather than organization permission | Invite/manage organization members |
| accounts.UserProfileView | REWRITE | Keep profile concept; privilege protections must be tested | Safe profile updates and explicit role management |
| customers.Customer | REWRITE | Email globally unique, no tenant, created_by is not organization ownership | Tenant-scoped customer, contact methods, optional duplicates |
| customers.CustomerViewSet | REWRITE | Staff only sees customers they personally created; unsuitable for shared small team | Organization-scoped access with membership permissions |
| jobs.Job | DISCARD as domain foundation | One record mixes project, quote estimate and payment total; no accepted scope, milestones or revisions | Project, QuoteRevision, WorkItem, RecordedPayment |
| jobs.JobViewSet | REWRITE | Staff assignment as ownership; creation forces assigned_staff=request.user; no workflow transitions | Explicit project commands and permission checks |
| dashboard.DashboardSummaryView | REWRITE | Totals and revenue do not surface next actions; role filtering is not tenant isolation | Action queue with derived status and overdue signals |
| frontend App.jsx | REWRITE | Dashboard/customers/projects CRUD navigation mirrors tutorial objects | Today, Inbox, Customers, Quotes, Projects, Follow-ups |
| frontend Projects.jsx | DISCARD as workflow UI | CRUD editor and financial progress bar, USD labels, editable money totals | Project overview, milestones, blockers and owner decisions |
| frontend api.js | REUSE concept / REWRITE implementation | Axios client works; localStorage token and session handling need deliberate security design | Auth-aware client with explicit error handling |
| core/settings.py | REWRITE configuration | ALLOWED_HOSTS=* and CORS_ALLOW_ALL_ORIGINS=True; environment controls incomplete | Environment-specific security defaults, narrow hosts/origins |
| existing migrations | PRESERVE as history, NOT as new design | Tutorial data/schema may matter to running deployment | New isolated implementation; migration plan only after data inventory |
| tutorial README / demo accounts | DISCARD as release material | Tutorial deployment references and demo credentials are not production readiness | New onboarding docs; rotate any still-valid demo credentials |

## Architecture dependency graph
Organization + Membership -> Customer + Activity -> Lead + NextAction -> Consultation + Assessment -> Quote + immutable revisions -> Accepted quote conversion -> Project + WorkItem -> Progress + ChangeRequest -> Handover -> Aftercare. Automation consumes domain events across these boundaries and cannot bypass approval gates.

## Target boundaries
- Identity & organizations: membership, authorization, data ownership.
- CRM: customers, leads, contacts, consultations, assessments.
- Estimates: price catalog references, quote revisions, approvals.
- Delivery: projects, milestones, tasks, blockers, changes.
- Work coordination: next actions, activities, reminders, review queue.
- Aftercare: snag lists, handover, service follow-ups.
- Integrations: drafts, human approval, delivery logs, retry-safe adapters.

## Data rules
All business-owned records carry organization_id. Cross-reference validation requires same organization. User roles are organization membership attributes. Customer email is not globally unique; possible duplicates are flagged rather than silently merged. Issued quotes are immutable snapshots. Money uses Decimal, currency configured per organization. Project creation from an accepted quote is idempotent. External communication remains draft until explicitly approved and sent. Payment entries are bookkeeping notes, not funds movement.

## Build isolation
Preserve the existing tutorial application and deployment unchanged. Build the new backend in a separate source tree (proposed: studio_os/) and the new frontend separately (proposed: studio_web/), with no automatic reuse of old migrations or production database. Start with isolated test configuration and synthetic data. Deploy separately only using approved free resources.

## Audit limitations
Static review of the identified files only. No runtime tests, migration execution, vulnerability scan, live deployment checks or complete dependency inventory performed. These are required before release.

## Immediate implementation tasks
1. Create isolated backend skeleton and configuration; add test runner.
2. Implement Organization, Membership, tenant-scoped Customer, Activity and NextAction with tests for cross-tenant isolation.
3. Add lead capture and daily queue, then quotation workflow.
4. Test scenario AT01, AT02, AT09, AT10, AT28 before expanding scope.
