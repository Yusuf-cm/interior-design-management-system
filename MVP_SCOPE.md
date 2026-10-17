# Studio.OS product blueprint

## Product thesis
Studio.OS is an operations automation platform for renovation, interior-design, and fit-out companies. Automate the manual administrative lifecycle from first inquiry through consultation, quotation, execution, handover, warranty and repeat business. The goal is fewer manual handoffs and less duplicated work, not merely more screens.

## Customer journey and capabilities
1. **Lead intake:** website/manual inquiry, source, contact, job description, attachments, ownership, follow-up queue and lead history.
2. **Consultation and site survey:** appointment scheduling, measurements, photos, requirements, scope, constraints and visit outcomes.
3. **Estimating and quotations:** reusable rate cards, labor/material line items, taxes/discounts, revisions, approvals, PDF and expiration dates; preserve quotation versions.
4. **Project conversion:** approved quote becomes a linked project with agreed scope, budget, milestones, assignments and initial tasks. Conversion must be idempotent.
5. **Delivery:** task assignments, materials and purchase requests, subcontractors, daily updates, change orders, issues, dependencies and milestones.
6. **Client collaboration:** progress timeline, approvals, variation sign-off, communications and payment requests with explicit consent and audit history.
7. **Handover:** snag/punch list, inspection, sign-off, completion pack and final account.
8. **Aftercare:** warranty records, maintenance schedules, service requests, reviews and repeat-work opportunities.

## Cross-cutting requirements
- True company-level tenant isolation on every record, query, report, file and background job. Staff-level filtering alone is insufficient.
- Explicit permissions for owner/admin, project manager, estimator, field staff and optionally customer portal users.
- Durable audit trail for price changes, approvals, job status, payments and outbound messages.
- Workflow engine: event -> conditions -> action, retry-safe jobs, human approval gates, scheduled reminders, notification log and templates.
- Consistent currency, decimal arithmetic, tax configuration, time zones, file storage, backups, data export and secure credential handling.
- Mobile-friendly field operations and unreliable-network resilience where practical.
- Clear separation between proposed automations and actions actually delivered to customers.

## Engineering sequence (quality gates, not calendar promises)
**Phase 0: Baseline and safety** — dependency review, test runner, CI, secrets review, role escalation, access control, data model inventory.
**Phase 1: Domain foundation** — organizations/memberships, roles, tenant-scoped managers, customers, leads, activity events, file ownership.
**Phase 2: Sales-to-project** — site survey, estimating, quote versioning and approval, idempotent conversion, customer-visible documents.
**Phase 3: Delivery operations** — scheduling, tasks, materials, variations, progress reports and client approval workflows.
**Phase 4: Handover and aftercare** — inspection, sign-off, warranty, service tickets, review and maintenance follow-up.
**Phase 5: Automation and integrations** — rule engine, notification templates, approved outbound channels, scheduling, logs, retries, integration adapters.
**Phase 6: Pilot readiness** — end-to-end tests, security review, isolated demo with synthetic data, onboarding, pricing validation, first pilot.

## Release gates
- No privilege escalation or cross-tenant access in API, dashboard, exports or attachments.
- Tests for quotation arithmetic, revision immutability, approval authorization, duplicate project conversion, job transitions, change orders and aftercare scheduling.
- Permission tests for unauthenticated, staff, admin and other-tenant accounts.
- Deterministic integration test of inquiry -> assessment -> approved quote -> project -> handover -> aftercare.
- Repeatable deployment, migrations, rollback plan, health checks, logging and backup restoration test.
- No live outreach, automated messages, production changes or paid services without separately required authorization.

## Product design principles
- Automate an existing renovation workflow; don't invent new work for the customer.
- Each piece of information is entered once and reused throughout the lifecycle.
- A person approves commitments, quotes, scope changes and outbound communications when appropriate.
- Deliver the full vision in validated vertical slices, not a fake all-features-at-once release.

## Existing implementation status (audited October 2026)
Django REST backend and React frontend currently include customers, staff, jobs and basic financial fields. A comprehensive renovation automation lifecycle is a roadmap, not an implemented capability. Security work is isolated on the development branch and remains untested.

## Product boundary: assistant, not operator
Studio.OS is a lightweight administrative assistant for small interior-design companies. It does not enter contracts, hire or pay contractors, guarantee estimates, process or hold funds, or send external messages without explicit owner approval. No paid third-party integrations are required for the initial product.

## First target customer
An owner-led interior-design studio with 2–10 people coordinating clients and active projects through WhatsApp, spreadsheets and notes. Validate this profile through customer interviews rather than assuming it represents the market.

## Experience principle
The home screen answers: (1) What needs my attention today? (2) Which client is waiting for me? (3) What should my team do next? The system should minimize data entry, re-use existing records, and prepare actions for human review.

## First vertical slice
- Create a lead with customer, brief and next action.
- Schedule a consultation and record survey notes.
- Draft an itemized quote and review it before sharing.
- Convert an accepted quote into a project without retyping.
- View a daily action list and prepare a customer status update.
- Close out the project and schedule a voluntary follow-up.

## Success measures for pilot
Time to record an inquiry; time to produce a first quote; number of duplicate entries avoided; overdue follow-ups; owner time spent on daily administration; and whether the owner elects to keep using the product after a trial. Measure baseline and trial rather than inventing savings.

## Competitive alternatives to test
Houzz Pro, Mydoma Studio, DesignFiles, Indema, Buildertrend, plus actual local substitutes (WhatsApp, Excel, notebooks). Focus comparison on onboarding effort, core workflow, price, mobile usability, and administrative time saved.
