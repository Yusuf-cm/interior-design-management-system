# Studio.OS architecture decision record 001: Tutorial code is non-authoritative

Status: Accepted for planning (2026-10-17). This is an architecture decision, not implemented software.

## Context
The existing Django/React repository began as a tutorial. Its current model relationships, endpoint structure, UI navigation and implementation order must not constrain Studio.OS. Product requirements come from the scenario catalogue and docs/DOMAIN_AND_ACCEPTANCE_SPEC.md.

## Decision
Design the product domain and user journeys independently of tutorial code. Treat existing code as a source of potentially reusable techniques and components only, never as a schema to preserve by default. Preserve existing main/production behavior; implement the replacement on an isolated development branch or separate app directory. No production changes without separate approval.

## Architecture order
1. Establish domain language, bounded contexts, invariants, workflows and acceptance tests.
2. Define organization isolation, user roles, authentication and audit history.
3. Define customer/lead/consultation/assessment and next-action models.
4. Define quote revisions, deterministic pricing and approval gates.
5. Define project conversion, execution, handover and aftercare.
6. Add workflow engine, retries, communication drafts and adapters.
7. Implement a simple mobile-friendly UI aligned to the owner's daily action queue.
8. Pilot with fictional data, then validate with a real small studio before claims about savings.

## Reuse rubric
- **Reuse:** independently understandable, tested, secure, and matches the new domain contract.
- **Rewrite:** useful behavior but wrong domain boundaries, coupling, permissions, or workflow assumptions.
- **Discard:** tutorial-only shortcuts, misleading screens, duplicate concepts, or insecure patterns.
- **Defer:** capabilities without a demonstrated scenario or operational need.

## Explicit non-goals
No binding contracts, payment processing or custody, contractor hiring, autonomous customer commitments, compulsory paid integrations, or hidden outbound messages. Studio.OS prepares and organizes work; the studio owner remains the operator.

## Implementation guardrails
- No blind migration of old tutorial models into the new domain.
- Do not silently change existing production data or URLs.
- No claims of passing tests until executed against actual implementation.
- Write characterization tests before reusing tutorial behavior.
- Each feature must cite a scenario and acceptance criterion.

## Immediate next deliverables
1. Tutorial inventory with keep/rewrite/discard decisions.
2. Independent entity relationship and event/state diagrams.
3. Executable acceptance-test skeleton in isolated implementation.
4. First end-to-end workflow slice with measured test results.
