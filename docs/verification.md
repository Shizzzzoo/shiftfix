# ShiftFix verification record

## Local automated checks

Backend command:

```sh
uv run --with boto3 --with 'moto[dynamodb,s3]' --with pytest python -m pytest -q tests
```

Latest recorded result: **30 passed** on 2026-11-14. A warning comes from the installed AnyIO pytest plugin referring to a deprecated pytest type; no test failures occurred.

Coverage includes:

- Supervisor-only approval and duplicate disposition.
- Current-assignee checks, including rejecting the previous owner after reassignment.
- Invalid/stale version rejection and terminal-state immutability.
- Returned assignments preserving the fault and deadline history.
- Preventing an assignment return after a repair has been submitted for verification.
- Repair submission, rejected verification/rework and eventual closure.
- Required decision reasons.
- Explicit reporter-only clarification resubmission.
- Supervisor confirmation of an already-resolved returned assignment.
- Idempotent create retries and rejecting changed payloads under the same key.
- Separate potentially duplicate reports without automatic merging.
- Atomic version-conflict handling without an extra activity event.
- Stale deadline no-ops and a due deadline escalating at most once.
- Rejecting foreign upload prefixes and unverified email claims.

Moto exercises local simulated DynamoDB/S3 behavior; it is not proof of live IAM, browser CORS, or cloud event delivery.

## Deployment and browser verification

The controller is recording deployment and browser checks separately. At the time this document was written, a full real user sign-up → email confirmation → assignment → repair → verification flow had **not** been established by these local tests. The first supervisor still needs to confirm their email in the deployed app. Do not present a local mock, a compiled frontend, or an infrastructure success status as complete end-to-end evidence.

CloudFront creation was blocked by account verification. The current implementation therefore serves static assets through API Gateway and a static Lambda while preserving JWT authorization on the work-order API. Verify both public static GET routes and an unauthenticated rejection from an application endpoint.

Before recording the submission video, check:

- Supervisor email confirmation creates supervisor access; ordinary verified sign-ups remain operators.
- A verified operator can be promoted to technician, then receives new group claims after fresh sign-in.
- Photo upload succeeds from the deployed origin and evidence cannot be fetched anonymously from its S3 object URL.
- A report can be approved, accepted, repaired and verified across actual role sessions.
- Merge/keep-separate, return/reassign, and clarification/resubmission actions behave as labeled.
- Deadline outbox delivery starts an execution and overdue escalation appears after the configured wait.
- A superseded deadline does not mark the new assignment overdue.
- Desktop/mobile layouts and core controls are usable.

## Known practical limits

No independent production security review or factory trial has occurred. Prototype list queries read all work orders before role filtering. Deadlines are normal elapsed hours, not business/shift calendars. Escalation is an inbox flag, not SMS/email. No exact-time S3 deletion or abandoned-upload cleanup is claimed. Cloud storage and retained resources can continue to cost money after a stack is deleted.


## Final deployed checks (2026-11-14)
Active stack shiftfix-live reached UPDATE_COMPLETE using immutable backend-v4.zip. App at https://11z3m6ydfe.execute-api.ap-south-1.amazonaws.com. Production build and cfn-lint passed. Backend 31 tests passed. Playwright fixture tests passed desktop assignment and reporting, mobile width check; live HTTPS login/signup screen render passed without submitting a user account.
Public /workorders without JWT returned HTTP 401. IAM-authorized direct Lambda smoke requests used explicitly synthetic claims (not a Cognito browser authentication test). Signed regional S3 POST uploaded a synthetic 68-byte PNG with HTTP 204; API validated HeadObject and transactionally created [QA] work order WO-1EBFEBB1. An explicitly injected short QA timer outbox triggered the deployed stream Lambda, Standard state machine and deadline Lambda. Execution timer-bc70d06a-4397-46bd-abec-8f78c8795755 SUCCEEDED with output {"escalated":true}; consistent DynamoDB read showed overdue=true. Test work order subsequently rejected with audit explanation, not deleted.
Human Cognito email confirmation/sign-in and multi-user browser repair workflow remain to be exercised by the owner. No password/code collected. No article, repository or video publicly published.

## Four-role/onboarding iteration
64 backend tests passed. Canonical roles Admin/Manager/Worker/Reporter, live membership refresh, strict persisted onboarding and closed-repair advisory reviewed independently. TypeScript/Vite build, cfn-lint and CloudFormation template validation passed. Added only four Cognito group resources; existing groups retained. Active deployed CodeKey backend-v6.zip, UPDATE_COMPLETE. Local Playwright fixture flow: onboarding profile -> role explanation -> workspace, team access, 500 MiB invalid replacement clears previous photo and cached metadata, no upload-signing request, form invalid until corrected/explicitly omitted, Escape/focus restoration, contrast/larger text preferences, 390px viewport no overflow. Axe returned zero violations in tested onboarding and overview states. These automated checks do not certify whole-app WCAG compliance. Real owner signup and multi-user repair test still require human interaction.

Final v6 HTTPS check: deployed factory JPEG returned HTTP 200, image/jpeg, and 233135 bytes; Playwright waited for naturalWidth>0 and confirmed browser rendering. Deployed login axe scan returned no violations. Sign-in to sign-up interaction, 390px mobile signup and unauthenticated work-order HTTP401 checks passed; no email/password/account submission made. The initial image test checked before the asynchronous image loaded; fixed the test wait, not the app delivery.

## Operations expansion (2026-11-14)

- Frontend TypeScript/Vite build passes. `uvx cfn-lint infra/template.json` passes. Live-template comparison before deployment found seven added scheduler resources, no removals, and no changed existing resources.
- `scripts/verify-operations.mjs` runs a local Vite session on port 5174 with explicit fixtures, never production credentials. It verifies dashboard filtering, vendor and asset creation, stock validation error recovery, inspection submission, versioned deadline policy changes, CSV download and mobile overflow. Dashboard, vendor editor, inspection and mobile dashboard axe WCAG A/AA scans reported no violations in those tested states.
- Separate CSV checks passed formula neutralization, quoted commas/newlines, malformed quoting, duplicate/unsafe column headers and 100-row bounds.
- Independent review found a parent-archive/child-create concurrency gap and stale inspection asset selection when changing templates. Both were corrected and passed targeted independent re-review. Final checks are recorded below.
- Local screenshots: `/tmp/shiftfix-operations/overview-desktop.png` and `/tmp/shiftfix-operations/overview-mobile.png`. Screenshots use test fixtures; these are not claims of populated production data.

- Final backend regression suite: **89 passed**. Race tests cover both orderings of archive/child creation and archive/work creation, including simulated delayed GSI visibility.
- Completed CloudFormation deployment uses `backend-v8.zip`, final `template-v8.json`. API, Planning and Static Lambda code hashes match the packaged ZIP (`VqAn2hZKj6IzeEwZ/r+6Bra6mMEmAzb8ktthkxkuWMI=`), with State Active and LastUpdateStatus Successful.
- Live public HTML serves the new `index-BXueMXrH.js`; unauthenticated `GET /catalog` returns401.
- IAM-authorized Lambda test events using the confirmed owner identity exercised the live API and its scoped runtime role. `/me` confirms Admin and completed onboarding. A marked supplier/part/internal purchase test received2 units into opening stock5, yielded7, rejected repeated receive409 and negative issue409, and preserved movement history. All three catalog test records were archived.
- A marked recurring plan generated one pending_review request through the live Planning Lambda; a repeat invocation returned processed=[] and skipped=[]. The plan advanced by365 days. The generated request was skipped with an explicit test reason and archived, and the plan was archived. This verifies the live function path and its permissions; it is not a claim of observed delivery by the hourly scheduler. GetSchedule confirms State ENABLED, rate(1 hour), the correct target, bounded retries and DLQ.
- The owner account is now CONFIRMED with email_verified=true. Full multi-user browser sign-in/repair validation remains separate from the local fixture UI checks and IAM-authorized live API checks. No password or login code was collected.

## Populated demo release

92 backend tests pass, including deterministic demo graph integrity, stable keys, stock reconciliation, absence of timer outbox rows, completed-manifest disclosure and denial of demo identities for login/role/assignment. `scripts/verify-demo.mjs` passed every catalog and specialized section, stock/meter history, work-order activity, and desktop/mobile checks using the generated dataset. Axe reported zero violations in populated overview, Upcoming, Users and mobile overview after chart scroll regions were made focusable.

Live API verified 177 tagged work orders from 2026-09-14 through 2026-11-14, 12 archived work orders, all 18 catalog kinds populated, and zero enabled demo plans/automations. Completed import replay returned alreadyComplete=true with no writes. Deployed /me exposes the disclosure and /users returns 8 display-only people; attempting a demo role change returned 403. CloudFormation UPDATE_COMPLETE with backend-v9.zip. Live API State Active, LastUpdateStatus Successful, and code hash `wVjhq92YLYLUzErzgNy720LOKwEPcfvNDcmyPGOhYp8=` matches local package. Public HTML serves the new index-CUS7iSjA.js.

Dataset scope and counts: demo-data.md. Screenshots in /tmp/shiftfix-populated use the same seeded fixture; signed-in live API checks used IAM-authorized Lambda test events, not a human browser sign-in.
