# ShiftFix current-code and runtime audit

Research date: 2026-11-14. Scope: current repository and the completed `shiftfix-live` deployment in ap-south-1. This is a targeted audit, not an exhaustive security assessment. No application code, production data, account permissions or infrastructure were changed during this research. Adversarial writes ran only in isolated moto databases/object stores, and the UI race used a local fixture API.

## Evidence boundaries

- Completed stack: UPDATE_COMPLETE, immutable `backend-v9.zip`. Live API State=Active and LastUpdateStatus=Successful. CodeSha256=`wVjhq92YLYLUzErzgNy720LOKwEPcfvNDcmyPGOhYp8=`, matching the previously verified release artifact.
- Live API stage: ThrottlingRateLimit=5, ThrottlingBurstLimit=10, DetailedMetricsEnabled=false. These are deliberate account-prototype settings; no load benchmark was run here.
- Evidence S3 bucket: versioning Status=Enabled. The application does not currently persist object VersionId with committed attachments.
- Live preventive schedule: State=ENABLED and ScheduleExpression=`rate(1 hour)`. Configuration is not proof of successful business processing on every run.
- The completed stack template contains no AWS::CloudWatch::Alarm resources. Alarms outside this stack were not inventoried; this is not a whole-account absence claim.
- Existing baseline:92 backend tests and fixture accessibility checks from the preceding release. The adverse probes below intentionally exercise gaps those tests do not assert away. They do not mean the production dataset was attacked or modified.

## Reproduced behavior and proposed repairs

| ID | Observation | Evidence / implication | Priority and repair |
| --- | --- | --- | --- |
| R01 | An undecodable file with a PNG prefix passes current validation | Probe: metadataAccepted=true, imageDecoderAccepted=false. `api.file_metadata` checks size/type and the first16 bytes. This demonstrates invalid-image acceptance, not executable-code execution. | P1: bounded server-side decode/verify, pixel/memory/time limits; optional safe re-encode and metadata stripping. Preserve existing byte/count/MIME rules. |
| R02 | Evidence is not bound to the reviewed object version | Probe committedMetadata contains key/name/type/size/stage, no VersionId. Replacing the object changes the hash returned by a latest-version read, despite bucket versioning being enabled. | P1: snapshot VersionId and checksum, use the same version for verification and signed retrieval, and grant scoped GetObjectVersion as needed through IaC. Never trust latest bytes for committed evidence. |
| R03 | Three distinct high readings create three active requests | Probe:readingCount=3, distinctWorkOrders=3, duplicateFlags=[false,true,true]. A retried identical reading is protected, but distinct readings are separate commands. Advisory flags do not suppress an incident storm. | P1: one active incident per configured rule/asset/condition, transactional condition latch, explicit rearm/cooldown policy, and suppression history. |
| R04 | Duplicate advice misses a simulated lagged GSI | First job exists in a strong read; secondPossibleDuplicate=false when the GSI discovery result is deliberately empty. Both jobs remain present. | P1: reuse strong asset-work references for duplicate candidates; keep human merge/separate decisions. This is an advisory miss, not an automatic-merge data loss. |
| R05 | Repeated catalog create makes separate records | Same vendor body produces different IDs and vendorCount=2. Generic create generates a UUID and ignores logical command identity. | P1: persist a stable operation ID plus normalized payload hash for creates, inspections, and stock commands; after a lost response return the prior result. |
| R06 | Stock unit can be changed after movements; identical SKU can be created twice | Probe changes pieces to litres with balance2 after an issue; sameSkuRecords=2. No conversion or historical unit snapshot is recorded. | P1: lock unit after opening movements, or require explicit conversion. Normalize/uniquely reserve SKU at the chosen catalog/store scope. Snapshot units and cost/currency in movement entries. |
| R07 | Historical inspection restore fails after template questions change | Probe restoreResult.status=400, message=`Checklist answers must match the template in order`. Restore revalidates old answers against the current template. | P1/P2: retain executed template revision/question snapshots and restore historical records using their historical schema. Validate active references separately. |
| R08 | Twenty permanently invalid oldest plans can starve a valid due plan | Fault injection only: corrupted references were inserted directly into moto, bypassing normal catalog validation. First and second runs return processed=[] and20 skipped failures; validPlanWorkCreated=false. | P1 recovery hardening: failure count/backoff/quarantine and a fair due cursor; distinguish business failure from successful invocation. No evidence this corruption exists in the live account. |
| R09 | A report with photos cannot transparently replay after its first success response is lost | Same report key, same image bytes, but a fresh upload key causes409:`Idempotency key already used for a different report`. First job is committed; only one job exists. The current Report.submit path uploads again on retry. | P1: stable persisted draft/command ID and attachment IDs; reuse completed uploads; add lookup/reconciliation for ambiguous commit outcomes. Preserve rejection of genuinely changed payloads under one command. |
| UI01 | Slower detailA overwrites later detailB | Local Playwright probe requested B last, but displayed A after responses arrived out of order; staleDetailWon=true. `detail()` blindly sets selected state when a request resolves. | P1 quick fix: selection generation ID or AbortController; only the latest requested detail may update the panel. Test rapid navigation, logout and page changes. |

These priorities concern the next product iteration. R01/R02 require evidence-integrity work before presenting images as trusted maintenance proof. R03/R04 are operational workflow risks with existing human review retained. R08 is specifically a recovery/fault-injection result. No remote exploit or production incident is asserted.

Reproduce without live mutations:

```sh
uv run --with boto3 --with 'moto[dynamodb,s3]' --with pillow python scripts/research-edgecase-probes.py
# With local Vite on5174 and the existing generated demo fixture:
node scripts/research-ui-race.mjs
```

Raw observations: [backend probe JSON](2026-11-14-edgecase-probe-results.json) and [UI race JSON](2026-11-14-ui-race-probe.json). The scripts record current behavior; they are not acceptance tests that should permanently require these defects to remain.

## Code-inspected gaps, not reproduced production failures

1. **Session/draft recovery:** the client stores an ID token and clears it on401; it has no persisted report draft or refresh/re-authentication recovery flow. A forced-password state currently suggests a newly registered account. No real password, login code or session secret was collected in this audit. Preserve private user-scoped drafts before adding a recovery path.
2. **Unbounded API responses:** `storage.list_jobs` correctly walks all DynamoDB pages, then `/workorders` returns the whole authorized result. `/catalog` collects all permitted catalogs and their pages; every module load requests that bootstrap. This is boundedness/cost/rendering risk, not a claim that internal pagination is missing. Add cursors, per-kind queries and bounded exports before a high-volume history import.
3. **Shared revision contention:** all catalog mutations and new work create paths update one revision item. It protects reference/archive integrity at prototype scale but makes unrelated concurrent writes conflict. Keep it until there is a measured reason and a correctly designed per-reference replacement; do not remove the guard merely to hide409s.
4. **Action recovery:** most actions depend on a version and do not have a durable logical command result. Version checks prevent stale double mutation; they do not tell a user whether a timed-out command actually succeeded. Create/issue/receive/inspection actions need explicit ambiguity recovery.
5. **Meter semantics:** current reading inputs are finite value/note with server arrival time and free-text unit. No observedAt, cumulative/gauge type, reset epoch, per-rule outcome, hysteresis or old-reading policy exists. Updating units/thresholds changes future interpretation without a stored historical rule version.
6. **Purchasing:** receiving is intentionally full-order once. Partial receipts, returns-to-vendor, line items, approvals and work-order blockers are not implemented. Existing atomic receipt protection is worth preserving.
7. **Inspections:** responses preserve question strings and answers, but no corrective-request link or executed template version. Fail notes and evidence are not conditionally required. An immutable response is not yet a complete corrective-maintenance workflow.
8. **Deadline delivery:** deadline processing writes overdue state and activity. No in-app notification inbox/push/email implementation is present. Do not describe this as delivered notifications. Retries and a shared DLQ exist, but no operator recovery interface or stack-defined alarms.
9. **Scheduler health:** RuleError failures are returned as skipped entries, so invocation success is not business success. Hourly20-plan handling, UTC elapsed intervals and coalesced catch-up are explicit limitations, not month/weekday or completion-based schedules.
10. **Reporting semantics:** current dashboard excludes archived rows and filters by createdAt, including demo data in aggregate counts. It does not expose real/demo scope or explicit created/closed date modes. Source data lacks failure/runtime/outage intervals for MTBF/MTTR; request age is not equipment downtime.
11. **Assignment readiness:** access-role validation exists, but skills, shift availability, workload, responsible-team routing and absence/delegation policies are not represented. Team membership is descriptive and deliberately does not grant authorization.
12. **Upload lifecycle:** per-update image bounds exist, while repeated rework can accumulate attachments. Interrupted uploads can leave uncommitted objects. Separate temporary upload expiry from committed evidence retention; blanket age-based deletion would be unsafe.
13. **Role change transactionality:** removing and adding Cognito groups are separate API calls. Concurrent admin edits or a failure midway need a fail-closed, audited recovery policy. This is a code-inspected failure mode, not a demonstrated privilege escalation.
14. **Security boundaries already worth keeping:** current identity/group rechecks, role-specific operations, foreign image-key rejection, optimistic work-order writes, target-version checks on merge, reserved asset codes, atomic stock receipt, strong catalog revision and asset-work references, and no fake Cognito demo users. Every new feature must use these same boundaries.

Code anchors: `backend/api.py` functions file_metadata, signed, set_role, route, create; `backend/catalog.py` functions validate, mutate, readings, archive; `backend/storage.py` list_jobs/write; `backend/planning.py` handler; `src/main.tsx` api/detail/upload/Report.submit; `src/components/OperationsWorkspace.tsx` load/mutate; `src/components/OperationsDashboard.tsx` jobs filters.

## Primary-source grounding

- Header/MIME checks are insufficient as a sole upload defense; OWASP recommends layered controls, content validation, permissions and size limits. Bounded image decoding is the proposed extension to our current checks. [OWASP File Upload](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).
- AWS documents that presigned requests can remain reusable within their validity, and uploading to the same key changes the current object. Our immutable-version recommendation follows from that behavior and the application's missing VersionId. [S3 presigned uploads](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html).
- GSI propagation after transactions is not immediate; dependent discovery cannot assume a current GSI view. Durable operation IDs also outlive the API transaction replay window. [DynamoDB transaction behavior](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transaction-apis.html), [TransactWriteItems request identity](https://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_TransactWriteItems.html).
- DynamoDB stream consumers can receive repeated records. Our outbox dispatcher already handles repeated execution names; new notification/issue consumers need equivalent idempotency. [Lambda DynamoDB integration](https://docs.aws.amazon.com/lambda/latest/dg/with-ddb.html).
- A rate measured in days represents elapsed24-hour periods; calendar scheduling and daylight-saving behavior need separate contracts. [EventBridge schedule types](https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html).
- Synchronous Lambda responses have finite payload limits, so returning every historical row is not an unlimited strategy. [Lambda quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html).
- IndexedDB supports local transactional data but is not a server synchronization engine; Background Sync has limited availability. A draft-first, explicit-send design is a smaller promise than full offline execution. [IndexedDB](https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API/Basic_Terminology), [Background Sync](https://developer.mozilla.org/en-US/docs/Web/API/Background_Synchronization_API).
- Loading, success, errors and reconciliation outcomes should be exposed to assistive technologies without forcing focus changes. [W3C status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html).

All proposed repairs remain unimplemented in this research deliverable; production continues to run the verified v9 release.
