# Submission draft — review before publishing

**Title:** ShiftFix: Serverless Factory Maintenance Workflows

**Description:** Turn machine-fault reports and photo evidence into owned maintenance tasks, with supervisor review, duplicate handling, verified repairs, and durable deadline escalation. Includes an optional assistant using a temporary external LLM while Bedrock account access is restricted.

## The problem

A maintenance fault can outlive the shift in which it was reported. A photo and a message are easy to send, but responsibility, duplicate reports, missed deadlines, and proof that the repair worked are harder to keep consistent.

ShiftFix follows a fault from reporting through assignment and repair to a supervisor's final decision. Its purpose is to keep work visible when ownership changes, without requiring a server or deployment pipeline to maintain.

## What the prototype does

An operator selects a machine, describes the fault and attaches optional photos. A supervisor reviews the request and assigns a verified technician. The technician accepts it, records blockers or returns a mistaken assignment, and eventually submits repair notes and evidence. The supervisor verifies the result or sends it back for rework.

Similar reports on the same machine are flagged as possible duplicates. The supervisor can merge them while preserving the original reports, or keep them separate. If a technician says the job was already handled, the work remains open until a supervisor confirms that decision with a reason.

Each decision appears in the activity timeline. An overdue deadline flags the work order for attention; it never silently deletes an unresolved fault.

## How the AWS services connect

- **Amazon Cognito** handles sign-up, email verification and sign-in. Server-enforced Admin, Manager, Worker and Reporter roles govern access.
- **Amazon API Gateway** validates JWTs before sending application requests to **AWS Lambda**.
- The Python API Lambda applies state and ownership rules and writes work orders plus activity atomically to **Amazon DynamoDB**.
- **Amazon S3** stores private evidence. Browsers upload through short-lived signed requests, and authorized viewers receive temporary download links.
- A transactional timer outbox enters **DynamoDB Streams**. A dispatcher starts a deterministic **AWS Step Functions Standard** execution, which waits until the relevant deadline.
- The deadline Lambda checks the current deadline version and state before marking the job overdue. Old timers cannot escalate a reassigned or closed job.

The initial account could not create CloudFront distributions until AWS account verification was completed. For this prototype, the React bundle is served by a static Lambda through public API Gateway GET routes. The work-order endpoints remain authenticated. The application still uses managed serverless services and manual infrastructure deployment through CloudFormation.

## The engineering detail

A report, a work order and an assignment have different meanings. Returning an assignment does not resolve a fault. Missing a deadline does not close the job. Merging two reports does not erase either reporter's evidence.

Conditional writes protect against two reviewers deciding from the same old record version. Idempotent report creation protects against a repeated submission. Deadline versions prevent stale automation from acting on newer assignments.

## Validation and limits

Local domain and mocked-storage tests cover role boundaries, current ownership, optimistic conflicts, report retry idempotency, duplicate handling, assignment return, clarification/resubmission, rejected verification, and stale or repeated deadline callbacks. See `docs/verification.md` for recorded checks. Do not claim complete live end-to-end verification until the confirmed supervisor and technician have completed the deployed workflow.

The prototype supports managed equipment, a location hierarchy, spare-parts inventory, purchases, inspections and paused demonstration maintenance plans. It serves one factory and uses inbox flags rather than external notifications. Production malware scanning is outside this prototype. No measured waste, cost saving, uptime, or maintenance-time improvement is claimed.

## Links to fill before submission

- **Public video, less than three minutes:** add the actual published video URL in the challenge's demo field and here.
- **Deployed application:** copy the final AppUrl from stack outputs.
- **Repository:** add the public repository URL only after intentionally publishing the source.

## Suggested 2:40 demonstration

- 0:00–0:15: Explain how faults lose ownership across shifts.
- 0:15–0:45: Report a machine fault with a real uploaded image.
- 0:45–1:10: Review a possible duplicate and keep it separate or merge it.
- 1:10–1:35: Assign the repair, show technician acceptance or return with reason.
- 1:35–2:05: Submit repair evidence, then supervisor verification or rework.
- 2:05–2:25: Show a deliberately shortened deadline escalate and an old timer safely no-op.
- 2:25–2:40: Show architecture and explain how conditional writes and deadline versions protect the workflow.

Record actual deployed behavior; label demonstration data and shortened timers. Omit any segment that has not been verified, and adjust the script rather than implying it worked.


## Optional assistant and temporary model provider

Ask ShiftFix searches role-permitted records and prepares work-order or paused maintenance-rule drafts for human review. The AWS Bedrock integration is implemented, but account-level model invocation is currently restricted. A temporary external LLM adapter uses the Gemini API while AWS access is being resolved; the application, authorization, records, evidence and durable maintenance workflows remain on AWS serverless services. This is not a claim of working Bedrock inference.

The temporary provider uses Google's free tier and is restricted to fictional demo records. Work-order creation requires explicit confirmation; rules open paused in the regular editor. Provider branding is omitted from the interface, with this implementation choice disclosed here. The temporary integration is deployed and verified with real Gemini replies and checked tool calls for work-order search, low stock, fictional people/assignments, work-order drafts and paused planning/automation drafts. Confirmation replay created one synthetic QA work order, subsequently rejected and archived; no factory action was triggered. Production verification used IAM-authorized Lambda test events, with separate local browser checks. See docs/verification.md for the precise validation boundary.
