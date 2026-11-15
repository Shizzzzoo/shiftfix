# Maintiny

Maintiny adds a role-aware maintenance assistant and direct workspace search. Open **Maintiny** in navigation for saved chats, or use the bottom-right launcher from any other signed-in page. Both entry points share the current conversation. The launcher says “Ask Maintiny” and shows a dismissible “Need a hand?” introduction until it is used or dismissed on that browser/account. Chat has its own Lambda and does not hold up catalog or work-order loading. Completed replies are saved privately in DynamoDB and reload after sign-in; sign-out or a role change clears browser state.

## Saved conversations

Start a new conversation from either the floating panel or the dedicated tab. Conversations are titled from the first question and listed by recent activity. The floating panel can expand into the tab without resetting the chat. Enter sends, Shift+Enter adds a line, and Escape closes dialogs with focus restored. Mobile layouts support the existing high-contrast and larger-text preferences.

Each account can keep 50 active conversations, with 30 exchanges per conversation and a 256KiB document limit. Full chats remain readable; start a new chat to continue. No old messages are silently discarded. The model receives only the last three permitted exchanges as context. Client-supplied history is rejected for saved chats. One generation lease and conditional version checks protect each conversation; request replay returns the saved result without another inference call.

Delete a chat using its trash button and confirm, or cancel to keep it. Deletion removes live messages, title and linked draft payloads, and frees a saved-chat slot. Conditional writes prevent replies or draft writes from restoring a deleted conversation. A content-free tombstone expires after two days. Existing DynamoDB backups/PITR follow their own retention; this is not an immediate backup purge. Previously created work orders and saved rules remain. Chats from an earlier role/data scope are locked with generic titles and can still be deleted. Referenced work-order access is rechecked before display and reuse; unavailable exchanges are hidden. Follow-up replies inherit the references used in their recent context, so reassignment also protects derived answers.

## Current AWS restriction

The first real Converse request for APAC Nova Micro on 15 November 2026 returned AccessDeniedException: “Your account is currently being verified.” The response says verification normally takes less than two hours and directs persistent cases to aws-verification@amazon.com. The deployed Lambda also returns ValidationException with the exact message “Operation not allowed” (final deployment request f50463a6-fe6c-4f21-acac-6c582c8511ee). AWS Knowledge Center identifies that message as an account security restriction requiring AWS Support: https://repost.aws/knowledge-center/bedrock-invokemodel-api-error. This is not a malformed-tool-schema diagnosis. The app exposes safe service diagnostics only to Admins and keeps logs free of prompts and records. No alternate Region/model was used to bypass it. The interface reports account access pending and keeps direct, permission-scoped search available. Bedrock inference is not verified until AWS allows invocation; mock model output in browser/unit tests is not a live model test.

After AWS permits Bedrock invocation, select AssistantProvider=bedrock in CloudFormation and verify an actual message. The selected provider is now Gemini; it does not silently switch providers.

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

Cognito JWT → explicit `/assistant/*` API Gateway routes → Assistant Lambda → checked tools/DynamoDB and Bedrock Converse. Status/search/chat/review/confirm and conversation list/create/read/delete routes require the existing JWT authorizer. The dedicated handler rejects non-assistant paths. IAM permits only the selected Nova inference profile/foundation model, scoped table/index operations and BatchGetItem on the table for saved-history access checks, Cognito user/group reads and its log streams. It has no S3 permissions, Cognito group mutation or broad Bedrock administration. The original API role is unchanged.

IAM Policy Autopilot 0.4.0 analyzed runtime sources. Its baseline included optional/transitively reachable operations and wildcard model resources, so it was not applied wholesale: the deployed policy is restricted to the actual allowlisted assistant operations and concrete stack/model resources. cfn-lint and five custom Guard security rules pass, including a negative control that rejects an anonymous assistant route.

## Validation boundary

Unit tests cover role filtering, strong-read reassignment checks, private field projection, unknown tools/fields, forged histories, draft ownership/expiry, idempotent confirmation, paused rules, atomic quotas, leases, authority rechecks and explicit model denial. Browser tests use marked local fixtures to check the UI and simulated model responses. Production search/auth/confirmation checks and the exact deployment state are recorded in verification.md. Do not present mocked replies as successful live inference.

Run `node scripts/verify-assistant.mjs` against local Vite on port 5174 after generating `.deploy/demo-fixture.json` with `python3 scripts/build-demo-data.py`. This checks blocked-inference handling, direct search, no writes before confirmation, idempotent UI controls, paused rule-editor handoff, expired drafts, conversation continuity and clearing after a role change.


## Temporary Gemini provider (15 November 2026)

The interface is provider-neutral at the owner's request. The project description discloses Gemini as a temporary external model while AWS Bedrock access is restricted. The existing Cognito, API Gateway, Lambda, DynamoDB, S3 and Step Functions workflows continue to run on AWS. The provider adapter is selected through AssistantProvider; switching is explicit configuration, never an automatic export to a second provider after an error.

Gemini uses the generateContent REST endpoint and the same allowlisted tool executor and confirmation flow. Native function-call IDs and opaque thought signatures are retained inside one Lambda request so subsequent function responses remain valid. Reasoning text and native protocol metadata are never included in the public reply. HTTPS redirects are rejected, credentials are in a request header, and raw provider error bodies are neither returned nor logged. Admins alone receive a bounded diagnostic with credential/request-text redaction and allowlisted status/reason codes; regular users receive a general error. Each Gemini call has a six-second network timeout, bounded response size and at most1024 output tokens including thinking; the original three-call/six-tool/per-user/factory quotas remain. Bedrock keeps its512-token limit.

The owner confirmed a **free-tier Gemini project**. GeminiDataMode defaults to demo. Only demo-tagged, role-accessible work orders, catalog records and display-only people can be exported by chat tools. Real identity names are removed if a demo work order was subsequently assigned/reported by a genuine user. Only demo-tagged activity is included. Drafts must reference demo assets/meters; normal editor operations and independent direct search remain available. Newly confirmed work orders are genuine audit records and are not automatically reclassified as imported demo records. Do not enter personal or confidential information in chat; the UI gives that brief data-scope notice. Marking a record demo is not automatic personal-data anonymization: imported demonstration records must continue to contain fictional content.

Google's unpaid-service terms permit product improvement and human review of inputs/outputs and prohibit sending personal/confidential information: https://ai.google.dev/gemini-api/docs/terms. Enabling paid mode is an explicit deployment change requiring an active billed Google project and appropriate data handling; it is not inferred from possession of a key. The configured model defaults to gemini-3.5-flash-lite; actual project model availability must be verified by a real invocation before claiming the feature works.

### Fresh credential setup

The key originally pasted in chat was not used or copied into a file. Revoke it at Google. The replacement is entered only in the owner's terminal:

```sh
uv run scripts/configure-gemini-secret.py
```

The script has inline uv dependencies including botocore[crt] for AWS login profiles. `--check` verifies SDK dependencies and STS sign-in before any key prompt. The original command omitted CRT and failed before a secret could be stored; that dependency and prompt ordering are corrected. Hidden prompts reject mismatches/noninteractive input. A Google ListModels authentication check runs before saving; rejection leaves the stored credential untouched. Successful output says the user is finished; no ARN or key needs to be copied to chat. It writes directly to Secrets Manager without reading a stored value. A new secret uses a dedicated rotating KMS key; Google API-key rotation itself is manual. Secrets Manager and a customer-managed KMS key have ongoing AWS charges; they are not a hard-capped free service. No new support plan is involved.

The deployment locates the secret through metadata. Supply its ARN as GeminiKeySecretArn and its immutable current version as GeminiKeyVersionId, with AssistantProvider=gemini and GeminiDataMode=demo. The template uses a Secrets Manager dynamic reference for the Assistant Lambda environment; the key is not a raw stack parameter, template literal, source file, frontend value or runtime-role permission. Do not print the function's Environment configuration. Secret changes require updating GeminiKeyVersionId to resolve a fresh value. No secret value is fetched directly into assistant context; the official AWS asm-exec runner is used for runtime-only connection diagnostics. The original Bedrock permissions/configuration remain available.

Deployment status and actual inference results must be read from the final release entry in verification.md; compilation/mocked tests alone do not prove a working live Gemini call.


## Current deployment status: working

The owner stored a replacement credential on 15 November 2026. CloudFormation now pins GeminiKeyVersionId=651541d2-b72c-42af-9a5e-0b00a055f034 in the existing secret. The stack reached UPDATE_COMPLETE without changing code or broadening permissions; the credential activation initially retained backend-v17.zip; see the latest release in verification.md for current code. Complete model discovery authenticated successfully and included gemini-3.5-flash-lite with generateContent support.

Six actual deployed chat requests returned200 and executed checked tools: exact verification count, low-stock inventory, a work-order draft, a paused recurring-plan draft, a directory-to-assignment lookup, and a paused meter-automation draft. Independent database reads confirmed the returned counts and inventory values. No work order existed before confirmation. Two explicit confirmation calls for the real model-generated QA draft returned the same work order and one reported event. The synthetic test work order was rejected and archived afterward. Neither the plan nor automation draft saved or enabled a catalog rule.

The interface remains provider-neutral. The project description discloses the temporary Gemini provider while Bedrock access remains restricted. Free-tier/demo-only scope still applies. These production checks used IAM-authorized Lambda test events for the confirmed owner; full human browser authentication across separate factory roles is a separate validation boundary. Existing local browser tests cover the presentation, source links, confirmation and normal-editor handoff. See verification.md for identifiers, values and cleanup.

The prior API_KEY_INVALID error belongs to the earlier credential version and is resolved by this replacement. The helper now checks Google before saving and has no ARN handoff. Never copy a key into chat or source; future rotations only require storing a fresh accepted key and updating GeminiKeyVersionId from metadata.
