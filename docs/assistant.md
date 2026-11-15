# Ask ShiftFix

Ask ShiftFix adds a role-aware maintenance assistant and a direct workspace search panel. Open **Ask ShiftFix** in navigation. Chat has its own Lambda and does not hold up catalog or work-order loading. Conversation text stays in the current browser tab's memory; sign-out or a role change removes it.

## Current AWS restriction

The first real Converse request for APAC Nova Micro on 15 November 2026 returned AccessDeniedException: “Your account is currently being verified.” The response says verification normally takes less than two hours and directs persistent cases to aws-verification@amazon.com. The deployed Lambda also returns ValidationException with the exact message “Operation not allowed” (final deployment request f50463a6-fe6c-4f21-acac-6c582c8511ee). AWS Knowledge Center identifies that message as an account security restriction requiring AWS Support: https://repost.aws/knowledge-center/bedrock-invokemodel-api-error. This is not a malformed-tool-schema diagnosis. The app exposes safe service diagnostics only to Admins and keeps logs free of prompts and records. No alternate Region/model was used to bypass it. The interface reports account access pending and keeps direct, permission-scoped search available. Real natural-language inference is not verified until AWS allows invocation; mock model output in browser/unit tests is not a live model test.

Once AWS permits invocation, retry a message in the same UI. The deployed model configuration and permissions are already in place; a new deployment is not required for that change.

## What it can do

- Search current accessible work orders by keyword, status, priority, asset, assignee, reporter, overdue flag, archived state and created-at UTC date range. Counts are computed before the bounded result list. Use `me` for the current assignee/reporter.
- Read a work order's description and recent activity; record buttons open the normal detail view. Names/numbers must come from tool data.
- Search permitted assets, types, locations, parts, meters, plans and rules. Parts low-stock search means quantity at or below the reorder level.
- Search management-only people metadata. Contact phone, biography and email are excluded from model directory results.
- Draft a report with a resolved machine, title, description, priority and category. The draft alone creates no work order. **Confirm create** uses the normal report transaction, idempotency, duplicate/advisory checks and manager review. Repeating confirmation creates one work order and one report activity event. The activity identifies a human-confirmed assistant draft.
- Draft a new recurring plan or meter automation for a Manager/Admin. Rules are forced paused. **Review in editor** checks draft ownership/expiry/current role, then populates the existing form. A person must save the normal form. Chat cannot enable rules, grant roles, assign work, close repairs, adjust stock or issue arbitrary API/database commands.

Direct workspace search uses the same checked read tools with no inference request. It remains useful while Bedrock is unavailable. Source text is displayed as text, not executed as HTML or code. Permission-scoped filtering happens before data is sent to a model. Non-management assignment candidates are rechecked with consistent DynamoDB reads to prevent stale GSI assignments exposing a reassigned work order. Authority and referenced-record access are rechecked during the model loop and before returning a response.

## Limits and data lifecycle

The model is pinned to **apac.amazon.nova-micro-v1:0**, discovered in Mumbai's system inference profiles. The APAC profile may route inference to the supported APAC Regions; it is not an India-only residency guarantee. No SageMaker endpoint, model training, vector database or always-running compute was added.

Each message is 1–1200 characters, with at most six alternating prior plain-text messages, each at most 1500 characters. Clients cannot supply system messages or tool results. Each request has at most three model calls, six tool executions and 512 output tokens per model call. Search results return at most 20 records. Two expiring DynamoDB leases limit simultaneous model work. This account's Lambda ConcurrentExecutions limit is 10, so reserved concurrency cannot be allocated while preserving AWS's required unreserved floor. The assistant Lambda uses 512 MB and a 28-second timeout; SDK connect/read timeouts and explicit error handling bound stalled requests. Normal screens use separate compute and their existing cached reads.

Atomic counters cap inference requests at 6/minute and 60/day per user, and 300/day for the factory. These are request/token bounds, not a dollar billing cap. Invalid chat payloads are rejected before counters/inference. Failed service attempts can consume a request allowance. Application logs contain operational error codes and token totals, not prompts or record contents. Bedrock GetModelInvocationLoggingConfiguration returned an empty configuration during setup.

Drafts are private to their creator, bound to their role and expire after 15 minutes. Their server-side expiry is checked even before physical cleanup. Draft/quota/lease records have expiresAt TTL; DynamoDB cleanup is eventual, not immediate. No existing evidence/image/work-order retention policy changed. Successful draft confirmation remains idempotent within the draft's valid lifetime; an expired draft requires a new draft.

## Architecture and permissions

Cognito JWT → explicit `/assistant/*` API Gateway routes → Assistant Lambda → checked tools/DynamoDB and Bedrock Converse. Status/search/chat/review/confirm routes require the existing JWT authorizer. The dedicated handler rejects non-assistant paths. IAM permits only the selected Nova inference profile/foundation model, scoped table/index operations, Cognito user/group reads and its log streams. It has no S3 permissions, Cognito group mutation or broad Bedrock administration. The original API role is unchanged.

IAM Policy Autopilot 0.4.0 analyzed runtime sources. Its baseline included optional/transitively reachable operations and wildcard model resources, so it was not applied wholesale: the deployed policy is restricted to the actual allowlisted assistant operations and concrete stack/model resources. cfn-lint and five custom Guard security rules pass, including a negative control that rejects an anonymous assistant route.

## Validation boundary

Unit tests cover role filtering, strong-read reassignment checks, private field projection, unknown tools/fields, forged histories, draft ownership/expiry, idempotent confirmation, paused rules, atomic quotas, leases, authority rechecks and explicit model denial. Browser tests use marked local fixtures to check the UI and simulated model responses. Production search/auth/confirmation checks and the exact deployment state are recorded in verification.md. Do not present mocked replies as successful live inference.

Run `node scripts/verify-assistant.mjs` against local Vite on port 5174 after generating `.deploy/demo-fixture.json` with `python3 scripts/build-demo-data.py`. This checks blocked-inference handling, direct search, no writes before confirmation, idempotent UI controls, paused rule-editor handoff, expired drafts, conversation continuity and clearing after a role change.
