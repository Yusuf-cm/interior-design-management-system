# Studio.OS renovation workflow MVP

## Primary workflow
Inquiry -> site assessment -> itemized quotation -> client approval -> project execution -> handover -> aftercare.

## Today: demo acceptance criteria
1. Record a customer inquiry with contact details, project description and requested service.
2. Record site-visit notes and measurements against that inquiry.
3. Produce a quotation with line items, quantities, unit costs, total and approval state.
4. On approval, create exactly one linked job; prevent duplicate conversion.
5. Assign staff, track status and keep a timestamped progress history.
6. Generate customer-ready status messages, but never send automatically without consent.
7. At completion, create a handover record and a review/maintenance follow-up task.
8. Staff must never see another staff member's restricted records; company isolation must be designed before multi-company hosting.

## Out of scope today
Automated WhatsApp sending, payment processing, accounting integrations, AI-generated estimates, and paid infrastructure.

## Test checklist
Role escalation, dashboard isolation, customer/job access control, quotation arithmetic, duplicate conversion, state transitions, handover and follow-up creation, unauthenticated access.

## Current code baseline
Customers, jobs, staff roles and financial fields exist. Inquiry, assessment, quotations, handover and aftercare are not yet verified as implemented. This document is a scope contract, not a claim that these features work.
