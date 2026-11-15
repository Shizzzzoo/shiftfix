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


## Component and onboarding revamp (2026-11-15)

TypeScript/Vite production build passed. Existing populated-state and operations Playwright checks passed after updating the old inline-filter test to open/apply the drawer. A separate temporary Playwright script outside the repository exercised draft/apply/cancel/reset/Escape, date errors, dependent location filters, search results and contained focus, guide replay from header/help with focus restoration and no profile writes, all six onboarding steps, four-machine limit and preference persistence. Chromium viewports: 1440x1000, 390x844 and 320x800. Page identity, meaningful rendering, absence of framework overlays and console/page errors passed. Axe WCAG A/AA scans returned no violations for desktop/mobile filter drawers, replayed guide, first-run profile/role/workspace, and accessibility with both preferences enabled. This is automated testing of those states, not complete WCAG certification.

Screenshots outside source: /tmp/shiftfix-revamp/dashboard.png, filters.png, mobile-filters.png, guide.png and mobile-guide.png. Desktop drawer, desktop guide and mobile guide were visually inspected. Browser plugin not available; installed Playwright Chromium used. The fixture API is explicitly local and contains no production login credentials.

Before packaging, IAM-authorized live API checks verified all 18 catalog kinds were populated: active parts8, part types4, part stores3, assets10, asset types4, locations3, zones6, subzones6, teams3, vendors4, purchases12, meters6, inspection templates4, inspection responses28, plans6, automations3, life-tracking6 and categories4. /workorders returned180 total records, including existing real/test records; the completed demo manifest still declares177 fictional work orders. Data was preserved, not re-imported. Live /me confirmed Admin and completed onboarding. Human multi-user browser authentication was not exercised this iteration.

The initial publish attempt was blocked by AWS MCP Unknown tool and CLI NoCredentials. After reconnecting through aws login --profile shiftfix, AWS MCP recovered. The combined component/profile/performance release is now deployed as backend-v10.zip; see the checks below. The old local-only package hash is superseded.


## Profile and loading release (2026-11-15)

- Production build passed. Backend suite: **112 passed**, including own-profile isolation, legacy profile migration, optimistic concurrency, unknown-field/role/email injection rejection, field limits, SDK reuse without caching authorization, and table identity separation. Existing demo/operations/onboarding browser regressions passed.
- `scripts/verify-resource-cache.mjs` passes deduplication, TTL, failed-read retry, selective/session invalidation and protection against an older response repopulating cleared cache. GET snapshots exist only in session memory; writes and sign-out invalidate them. Current Cognito authority is still fetched on every backend request.
- Temporary `/tmp/shiftfix-profile-qa.mjs` verifies saving/reloading/discarding profile edits, 409 recovery, roster visibility of department/title/shift, private phone/bio omission, read-only self authority and management link, and clearing management data after a same-session demotion. With an artificial 1000ms catalog delay, seven warm navigation switches took44–146ms and reused a single catalog GET. These are local fixture measurements, not deployed browser network timings.
- Profile desktop1440x1000, mobile390x844 and320x800 high contrast/larger text axe scans found zero WCAG A/AA violations in tested states; no overflow, page errors or unexpected console errors. Screenshots `/tmp/shiftfix-profile/desktop.png` and mobile.png were visually inspected. Browser plugin not available; installed Playwright used.
- CloudFormation `shiftfix-live` in ap-south-1 reached UPDATE_COMPLETE with immutable backend-v10.zip and unchanged template. API/Static Lambda State=Active, LastUpdateStatus=Successful, CodeSha256=`82UqVNl+tirzZaISbsOZPFdiyJC2x50TshQ9OkmA0nc=` matches the652610-byte local ZIP. Public HTML and both new assets respond200. Anonymous /catalog returns401. Deployed login browser smoke passes identity/render/assets without entering credentials.
- IAM-authorized Lambda test events using the confirmed owner identity saved the exact existing name/department/machine values, upgrading profile version0 to1 while preserving all existing details and Admin authority. An injected role field returned400 with “Access roles and email cannot be changed here”; replay of the old version returned409 with “Your profile changed in another session.” A fresh /me confirms version1; roster responses omit phone and bio.
- Live reads preserve all18 populated catalog kinds,180 work orders total and the177-work-order fictional demo manifest. Data was not re-imported. No email, password, role or demo identity was changed.

Direct Lambda invocation timings from the AWS MCP host (two samples each, including SDK/network overhead):

| Endpoint | Before v9 (ms) | After v10 (ms) | New handler duration (ms) |
| --- | --- | --- | --- |
| /catalog | 4666 / 4796 | 3885 / 1922 | 2187 cold / 587 warm |
| /workorders | 2859 / 2733 | 2177 / 2134 | 586 / 550 |
| /machines | 1633 / 1598 | 1165 / 915 | 171 / 167 |
| /me | 1929 / 1832 | 1023 / 1177 | 181 / 178 |

The new Server-Timing app header isolates handler time. The initial catalog call also initializes SDK pools; on-demand cold starts still exist. These small samples demonstrate improvement, not a p95 or universal end-to-end browser latency guarantee. Authenticated UI checks used local fixtures; production checks used IAM Lambda invocations. Full human multi-user sign-in/repair validation remains separate.


## Ask ShiftFix / Bedrock release (2026-11-15)

- Full backend suite: **135 passed**. New assistant coverage checks role-filtered queries and exact counts, private projections, strongly re-read assignments, read/tool allowlists, forged histories, draft ownership/expiry/role changes, retry-safe human-confirmed creation, paused rules, atomic quotas, two expiring leases, current authority rechecks, model rejection and Admin-only safe service diagnostics. Tests simulate Bedrock; they do not prove live inference.
- TypeScript/Vite build and resource-cache verification pass. Existing populated/operations/profile/onboarding browser checks passed after the integration. `scripts/verify-assistant.mjs` exercises simulated model output, independent search while inference is blocked, record links, no writes before Confirm, one confirmed work order, paused rule editor with no automatic Save, expiry, navigation continuity and clearing management history on role change. Desktop1440, mobile390 and320px high contrast/larger text tested without overflow or unexpected page errors. Axe reported zero violations in tested assistant states. These are local fixtures, not a complete human multi-user production sign-in test. Screenshots: /tmp/shiftfix-assistant.
- cfn-lint passes. All five custom rules in infra/assistant.guard pass using guardpycfn; an anonymous-route negative control fails as intended. IAM Policy Autopilot 0.4.0 analyzed the runtime sources; its broad baseline was reviewed, not automatically applied. The actual role permits only the selected inference profile/foundation model, table/index operations, Cognito reads and own logs. Read-back found ScopedRuntime as the only inline policy and AttachedPolicies=[]; TTL TimeToLiveStatus=ENABLED, AttributeName=expiresAt.
- CloudFormation shiftfix-live reached UPDATE_COMPLETE with backend-v13.zip. API, Static and Assistant runtime CodeSha256 all equal P8hkk08TqV886L0rYQQygoRCco0Q427vTE6R6N4MvIE= (668698-byte final package), State=Active and LastUpdateStatus=Successful. Production public HTML and index-DjuDc845.js / index-CKNCHDvW.css respond200. Installed Chromium rendered the deployed login without page errors. All five anonymous assistant routes return401. No password/login code was collected.
- IAM-authorized invocation using the existing confirmed owner identity returned configured=true/scope=admin for assistant status. Direct search for DEMO returned totalMatches=165 with three requested results and sources; management people projection omitted email/phone/bio. Forged system history returned400, and a display-only demo identity returned403. These tests exercise live IAM/data/authorization, not browser JWT issuance.
- The confirmation path was verified live using one explicitly synthetic private draft inserted for testing, not a model-generated draft. Two confirmation calls returned the same WO-CA8CAE3E (ca8cae3e-20ee-3eb3-4984-262d96bac52f), createdVia=assistant, with the human-confirmation audit event. It was rejected through the normal API with a test explanation and archived; final status=rejected, archived=true, version=3. No repair assignment, rule activation or factory action was triggered. Existing demo data was preserved without re-import.
- Actual Bedrock inference **fails**: the first direct Converse request returned AccessDeniedException saying the account is currently being verified. The deployed function returned ValidationException: Operation not allowed. The final v13 retry returned503, code=AI_ACCOUNT_RESTRICTED; Admin diagnostic requestId=f50463a6-fe6c-4f21-acac-6c582c8511ee. The complete error responses were read. AWS Knowledge Center documents this exact error as an account security restriction requiring AWS Support: https://repost.aws/knowledge-center/bedrock-invokemodel-api-error. The underlying reason for the account restriction has not been determined. Do not infer a security incident or claim successful live AI replies. Permission-aware direct search and confirmation work without inference.
- The Support API returned SubscriptionRequiredException: Amazon Web Services Premium Support Subscription is required to use this service. A support request is prepared in aws-bedrock-support.md but **not submitted**; explicit permission to send an external support message is pending. No paid support plan was purchased. No Region/model changes were used to bypass the restriction.


## Temporary Gemini adapter preparation (2026-11-15)

The owner requested provider-neutral UI and disclosure in the project description, and explicitly chose free-tier/demo-only data. The adapter, scope filters, credential helper, template parameters and description are implemented locally. Full suite:158 tests pass; TypeScript/Vite build, cache verification and cfn-lint pass. All five Guard rules pass (result.container.FileCheck.status=PASS). Assistant browser checks pass with a visible demo-only data notice, desktop/mobile/320px accessibility scans, confirmation and paused-editor flows. These tests use mocked Gemini responses.

The helper's original command missed the CRT extra required by the existing AWS login profile. It failed at session.client('secretsmanager') before any secret write. Inline uv dependencies now include boto3>=1.41.0 and botocore[crt]>=1.41.0, and STS sign-in is checked before hidden prompts. `uv run scripts/configure-gemini-secret.py --check` actually completed successfully on the owner's machine without a key prompt or secret read/write. Regression tests cover dependency failure before prompting and read-only preflight.

Compared with the completed v13 template: no resources added/removed, only Assistant environment changes; four provider/model/data-mode/secret-ARN parameters plus a secret-presence rule/condition are added. No runtime IAM policy is broadened. The packaged pending artifact backend-v14.zip is671961 bytes, hash cG5eUukNdJu0yMDEeIkFB+NgU8nIRr51bniEmjrTqtg=, frontend index-Cw_JnT2j.js / index-CKNCHDvW.css. The exact new artifact key was checked unused before upload. This is preparation, not proof of deployment or live Gemini inference. The active application remains v13 until a completed release entry says otherwise.

At this preparation checkpoint, DescribeSecret for shiftfix/gemini in ap-south-1 returned ResourceNotFoundException. This describes only that exact expected secret/Region; no global absence is claimed. The replacement key must be stored through the corrected terminal helper before enabling the dynamic reference. No pasted key was used, no stored secret value was read into assistant context, and no live Gemini model response has yet been verified.
