# Studio.OS workspace

The interface is served by the isolated Studio.OS backend at `/`. It uses the verified
inquiry, visit, assessment and quote APIs. The tutorial frontend/database remain separate.

## Open locally
From the repository root:

```sh
python -m pip install -r studio_os/requirements.txt
python -m studio_os.manage migrate
python -m studio_os.manage create_studio_workspace --username yourname --studio "Your Studio"
STUDIO_OS_DEBUG=true python -m studio_os.manage runserver 127.0.0.1:8000
```

Open http://127.0.0.1:8000/ and sign in with the credentials you created.
The setup command prompts for a password twice (at least 12 characters); it creates no
hardcoded credentials, does not change existing users and grants no Django superuser
privileges. It only supports the isolated Studio.OS SQLite settings.

PowerShell users can set `$env:STUDIO_OS_DEBUG="true"` before running the last Python
command without the shell variable prefix. DEBUG enables local static asset serving.
No Node build is required. Local data is ignored by Git. Nothing is deployed.

## Work through an inquiry
1. Add a customer in Customers. Record their inquiry in Inquiries.
2. Record the response through Today; update the inquiry to Contacted, then Qualified,
   with supporting notes.
3. In Site visits, propose a time and assignee. Open the visit to confirm it.
   Conflicting confirmed bookings are rejected.
4. At/after visit start, record completion or no-show. Reschedule/cancel through the
   visit form rather than its linked action.
5. Record the assessment from the completed visit: scope, notes and labelled dimensions.
   Unknown values stay blank.
6. Review readiness. Missing required dimensions block it unless an owner records an
   explicit preliminary-estimate reason.
7. Draft the quotation with descriptions, quantities, unit prices and optional discount
   and tax factor. The server calculates the totals.
8. Open the quotation and submit for owner review. An owner can approve sharing internally
   or return it to draft. Internal approval sends nothing; recording an already-received customer response is a separate owner action below.

Quotation details show preserved revisions. Reopening source observations revokes approval
and requires a refreshed revision. History retains stage changes and recorded notes.

## Daily work and permissions
Today lists open due/overdue/undated work, linking workflow tasks to their source record.
Ordinary follow-ups accept outcome notes and an optional follow-up action/time.
Owners/coordinators can change ordinary task assignment/time from its outcome form.
Field staff see only assigned actions/visits; private directories and quote amounts are
not requested or shown. Assessment preparation after field visits goes to active office
staff, or remains unassigned for office review if no office membership exists.

Company switching clears displayed records. All requests use the selected company.
After a stale-edit conflict, close the form, use Refresh, review the record and reopen it.
Entered notes remain in the form until it is closed.

Scheduling forms explicitly use Nairobi time, independent of the device timezone.
Currency values remain decimal strings; the browser does not recompute financial totals.

## Verification
```sh
python -m studio_os.manage test studio_os.operations -v 2
python -m unittest discover -s studio_os/tests -v
npm ci --prefix studio_os/ui-tests --ignore-scripts
npm test --prefix studio_os/ui-tests
```

Node/jsdom are test-only dependencies. DOM tests use mocked API responses. Django tests
exercise actual sessions, CSRF and workflow endpoints. No real-browser visual, keyboard
or mobile-device QA was run in this environment.

## Boundaries
Local development interface only. No production changes or deployment are included.
There is no public signup or team-invitation delivery. Agreement signing, purchasing
and payment processing are outside this workflow. Production auth/hosting remains a separate gate.

## Team access and passwords
Owners now have a Team screen. Add a teammate with a unique username, display name,
studio role and initial password. Passwords must be at least 12 characters and pass
similarity/common-password checks. Credentials are not emailed or logged. Give them to
the teammate privately; they can use Change password after signing in.

Existing usernames are never attached to a company or reset through this screen. Role
and access changes apply only to the selected company's membership, with a reason and
version check. Disabling membership preserves assignments/history. Review open actions
and reassign work as appropriate. At least one active owner must remain.

Change password applies to the signed-in account across its studios, verifies the
current password and keeps the current session signed in. Other sessions lose their
old password authentication state. Owners cannot reset another existing user's password
through the Team screen. Django staff/superuser privileges are never granted here.

## Quotation register and print copies
The Quotations screen lists studio estimates and can filter pending owner reviews,
drafts or approved estimates. Search by customer or quotation number.

Open a quotation to use Print estimate / save as PDF. The new tab contains recorded
line prices, totals, scope and revision number. Internal observation notes, staff
outcomes and the private explanation of provisional authorization are omitted. A
preliminary-estimate notice remains when measurements require confirmation.

Current internally approved estimates are labelled for discussion. Drafts, changed
sources and archived revisions carry explicit internal-copy labels. Viewing or printing
does not send anything, record customer acceptance or change inquiry/quotation state.

Verification update (2026-10-29): live desktop sign-in layout checked in the browser.
Authenticated-screen, mobile and print-dialog browser QA remain outstanding. The
additional API/DOM tests cover the new team, review register and print functionality.


## From quotation to internal project planning
After internal approval, the owner can Record manual sharing against that revision.
Enter when it actually happened, a reference/channel, notes and an explicit future
follow-up time. This records staff-reported history; the system has not delivered or
verified a customer message. Owners/coordinators can later reschedule the reminder.

When a response arrives, the owner records Approval already received, Changes requested
or Declined, with time/reference/notes. Responses cannot predate the recorded sharing.
Recording approval moves the inquiry to Won; a dormant inquiry can be won through this
evidence-bearing path, while the manual stage picker still cannot select Won.

A shared revision cannot be edited until a customer change request is recorded. New
revisions preserve prior prices and require internal review again. After approval is
recorded, its source is frozen. An approval entered by mistake can be corrected with a
reason before project creation; the original record remains and customer follow-up is
restored. Once a project exists, this correction path is blocked to preserve its baseline.

Use Plan project on the recorded approved quotation. Choose a project name, an active
owner/coordinator, optional planning dates and a note. Repeating conversion returns the
existing project instead of creating a duplicate. Scope and total remain linked to the
accepted revision; no payment, hiring or agreement is created.

## Project work
Projects lists the studio's work. Owners/coordinators add work items, assign active
staff and choose a due time or explicitly leave it undated/unassigned. Start the project
before progressing its work. Assigned staff can start work, record a blocker, resume it
and mark it done, always with an update note. Blockers are visible in the project and
in the daily action list. Field staff see only their assigned work, not quote amounts,
other people's tasks, accepted scope snapshots or internal project history.

Pausing blocks work start/completion until a manager resumes the project. Cancelling
cancels open tasks and keeps completed history. Managers can reopen a work item with a
reason; cancelled projects cannot be resumed or receive new work in this slice.

Finishing every task does not mark the project complete. Handover inspection, scope-change
approval and aftercare are the next workflow gates. Work descriptions are internal plans;
they do not alter the accepted quotation or create approved extra scope.
