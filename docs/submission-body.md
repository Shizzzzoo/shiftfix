## A repair should survive a shift change

A machine fault starts with something small: a photo, a description and a request for help. The difficult part is keeping that fault owned until somebody verifies that the repair worked.

Two people may report the same machine. A task may reach the wrong technician. A repair may already have been completed. A deadline may expire after the work has been reassigned. These situations need clear decisions and preserved context.

I built **ShiftFix**, a serverless factory-maintenance workspace, to connect fault reporting, responsibility, evidence and final verification. **Maintiny**, its maintenance assistant, helps users find permitted records and prepare drafts for review.

[Open the deployed application](https://11z3m6ydfe.execute-api.ap-south-1.amazonaws.com/?release=maintiny-v20).

## The workflow

1. A **Reporter** selects a machine, describes a fault, chooses a priority and optionally adds photographs.
2. A **Manager** reviews the request, asks for missing details, rejects it with a reason, reviews possible duplicates or approves and assigns it.
3. A **Worker** accepts the assignment, records a blocker or returns an incorrect assignment with an explanation.
4. The worker submits repair notes and optional evidence.
5. The manager verifies completion or returns the repair for rework.

An **Admin** manages account access, including Manager access. Managers can manage Worker and Reporter access. Roles and current ownership are checked on the backend. Profile edits and team membership do not grant permissions.

An activity timeline keeps the decisions and reasons attached to the work. Overdue work remains visible for attention; a missed deadline never silently closes an unresolved fault.

## The edge cases are part of the product

**Two reports about the same machine.** Machine/category matches flag possible duplicates. A manager can compare, merge or keep the reports separate. Merging preserves the original reports, authors and evidence. This is a deterministic review aid, not image recognition or automatic proof that two faults are identical.

**The assigned person is not responsible.** Workers can return an assignment with a reason. The manager can reassign it while retaining the history. A returned assignment does not resolve the underlying fault.

**The repair was already handled.** Matching completed repairs produce an advisory. A manager reviews the evidence and either confirms an already-resolved outcome with a recorded reason or treats the report as a new occurrence. The app does not automatically discard it.

**Two reviewers act at once.** Version conditions reject stale decisions. Repeated report submissions use idempotency keys, protecting against duplicate work orders after a retry.

**An old deadline fires.** The deadline handler checks the current state, deadline and deadline version. A superseded timer cannot flag a newer assignment or completed job as overdue.

**An oversized image is selected.** Browser checks reject a 500 MB selection before requesting upload authorization. Evidence is limited to five JPEG, PNG or WebP images, up to 5 MiB each. Signed S3 policies constrain size, and the backend checks ownership, stored size, content type and image signatures before attachment.

**A receipt or scheduled run is retried.** Purchase receiving updates stock and receipt history atomically. Preventive occurrences use deterministic identities and conditional transactions so a retry does not create a second occurrence.

## How the AWS services connect

The frontend uses **React and TypeScript**; the backend uses **Python Lambda functions**.

| Service | Responsibility in ShiftFix |
| --- | --- |
| Amazon Cognito | Email verification, sign-in and identity groups supporting the access hierarchy. |
| Amazon API Gateway HTTP API | HTTPS endpoints and JWT authorization for application and assistant routes. |
| AWS Lambda | API rules, identity onboarding, frontend serving, stream dispatch, deadline checks, preventive planning and Maintiny. |
| Amazon DynamoDB, on-demand | Work orders, activity, equipment/catalog records, profiles, private conversations, idempotency records and timer outbox. |
| Amazon DynamoDB Streams | Dispatch committed timer-outbox records to the workflow starter. |
| Amazon S3 | Private fault and repair photographs with temporary signed access. |
| AWS Step Functions Standard | Durable waits until acknowledgment, repair or verification deadlines. |
| Amazon EventBridge Scheduler | Hourly invocation of the due-plan checker for preventive maintenance. |
| Amazon SQS | Failure destinations for selected asynchronous processing paths. |
| Amazon CloudWatch | Application and API operational logs. |
| AWS IAM | Service roles scoped to their responsibilities. |
| AWS CloudFormation | Infrastructure definitions and manual stack updates without a deployment pipeline. |

The central event path is:

**Report/action → API Gateway → API Lambda → DynamoDB transaction → DynamoDB Streams → dispatcher Lambda → Step Functions Wait → deadline Lambda → current-state check.**

The work-order update, activity entry and any required timer-outbox record are committed together. The dispatcher starts a deterministic workflow execution. Step Functions stores the wait; a Lambda invocation does not remain running until the deadline.

The application has no always-running application server or CI/CD pipeline to maintain. Infrastructure is defined in CloudFormation and deployed with immutable application artifacts. Storage, backups, logs and scheduled activity can still incur charges when nobody is browsing.

## A useful workspace around the repair

ShiftFix also connects the records needed to understand and plan maintenance:

- **Equipment and locations:** assets, asset types, categories, teams, locations, zones and sub-zones with hierarchy validation.
- **Inventory:** parts, part types, storage locations, vendors, reasoned stock adjustments, reorder levels and movement history. Stock cannot become negative.
- **Purchasing:** internal purchase records and one-time stock receiving. The prototype does not send supplier orders or payments.
- **Preventive maintenance:** recurring plans, next-run dates, paused/enabled states and upcoming occurrences that enter manager review.
- **Meters and automations:** manually entered readings, min/max thresholds and rules that create review requests after threshold breaches.
- **Inspections:** ordered checklist templates, Pass/Fail/Not applicable answers and recorded observations.
- **Part life:** installation records and calendar-based service dates.
- **Reporting:** filtered dashboards, workload breakdowns, CSV exports, bounded asset CSV import with preview, and reversible archive controls.
- **Profiles and onboarding:** editable profile details, explanations of current access and a guided introduction to the main modules.

Dashboard filters live in an Apply/Cancel drawer. Shared, short-lived browser-memory caching reduces repeated data fetching when switching modules. Keyboard navigation, visible focus, screen-reader feedback, high contrast, larger text and responsive layouts support different ways of using the workspace.

## Meet Maintiny

The bottom-right **Ask Maintiny** button is available across the workspace, with a dismissible introduction. A dedicated Maintiny tab provides saved conversations, new chats and deletion. Both entry points share the current conversation.

Maintiny can search permitted work orders, check low-stock demo parts, find accessible equipment and prepare work-order or maintenance-rule drafts. Management-only directory access remains restricted by role. The model uses allowlisted tools rather than unrestricted database access.

A proposed work order requires **Confirm create**. Planning and automation drafts open paused in the regular editor for review and saving. Chat does not grant roles, assign technicians, close repairs, adjust stock or silently activate rules.

Conversations are private to the authenticated account and bound to its access context. Referenced work-order access is rechecked before displaying or reusing history. Follow-up replies inherit relevant access references. Deleting a chat removes its live messages and linked private draft payloads; conditional writes prevent late replies from recreating it. Previously created work orders and saved rules remain.

**Temporary model-provider disclosure:** Amazon Bedrock integration is implemented, but model invocation in this AWS account is restricted. The deployed assistant therefore uses the **Gemini API as a temporary replacement**. Its current free-tier mode restricts tool exports to fictional demonstration records, and users are instructed to keep personal and confidential information out of chat. Working Gemini inference has been verified; working Bedrock inference is not claimed. Authentication, authorization, records, evidence and durable workflows remain on AWS.

## Building around constraints

The initial account restriction also prevented CloudFront distribution creation. For this prototype, the compiled frontend is served through public API Gateway static GET routes and a dedicated Lambda. Application data remains behind JWT-protected routes. This gave the project a working HTTPS deployment without introducing a server to manage.

The reusable pattern is a conditional business transaction with an auditable activity record and durable, version-aware follow-up. It applies to maintenance handovers and can be adapted to facilities requests, equipment inspections and other human-reviewed work queues.

## Validation and demonstration data

The backend suite has **177 passing tests**, covering permissions, ownership, conflicting updates, retries, duplicate review, evidence checks, inventory operations, stale timers and saved-chat behavior. The frontend build, infrastructure linting and custom infrastructure security checks pass.

Browser fixture tests exercise populated modules, onboarding, filters, profiles, assistant confirmation, conversation persistence/deletion and responsive layouts down to 320 pixels. Automated accessibility checks found zero violations in the tested states; this is not a complete accessibility certification.

Live AWS checks have separately verified deployed storage, evidence and deadline paths, actual Gemini tool calls, reviewed draft confirmation, saved conversations, retry replay and deletion. These checks include IAM-authorized Lambda test events; they are distinct from a complete human browser walkthrough across separate factory accounts.

The demo contains clearly labeled fictional factory history spanning **14 September to 14 November 2026** across work orders and connected modules. Demo people are display-only records, and seeded preventive plans and automation rules start paused. The data demonstrates functionality, not measured customer outcomes.

## Current boundaries and next steps

This is a single-factory hackathon prototype. Meter readings are manual; no live IoT sensor feed is connected. Part-life estimates use dates, not predictive maintenance. Deadline escalation appears in the workspace rather than email/SMS/push notifications. Image checks are not a complete malware-scanning system.

Next steps include validated factory isolation, notification delivery, production upload scanning and retention policies, real sensor integration, broader human usability testing and activating the existing Bedrock provider once account access permits it.

ShiftFix keeps a fault connected to its owner, evidence, deadline and final decision, using managed AWS services to carry the workflow across shifts.
