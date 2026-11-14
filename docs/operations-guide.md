# ShiftFix operations workspace

ShiftFix now includes the maintenance sections in the supplied CMMS reference, sized for a working single-factory prototype. All records save to the existing DynamoDB table; uploaded fault and repair images remain private in S3. Empty states reflect real data rather than seeded chart totals.

## Set up a factory

1. Sign up, verify your email and complete onboarding. The configured owner is Admin; other new users start as Reporters. Admins can make Managers or Workers in Users. Managers manage Workers and Reporters. Teams organize ownership, and do not grant access permissions.
2. Create Locations, then Zones with a parent Location, then Sub-zones with a parent Zone. The API rejects inconsistent asset location hierarchies.
3. Add Asset types, Categories and Teams; then add Assets with a unique immutable code and optional serial, classification, location hierarchy and responsible team. Built-in starter machines remain available to historical work orders and reporting; the Assets section identifies them separately from editable equipment records.
4. Add Vendors, Part types and Part locations; create Parts with opening stock and a reorder level. Use Adjust stock for later issues/replenishment and supply a reason. Stock cannot become negative. History records each movement.
5. Create Purchase management records referencing a Part and Vendor. Receive once to increase stock atomically. These are internal records: no supplier order or payment is transmitted. Received records are immutable.

## Use the modules

| Section | Implemented behavior |
| --- | --- |
| Overview | Counts, completion donut, workload by user/asset/location, recent orders and CSV exports. Filters cover status, date, asset, type, category, team, assignee and location hierarchy. Uses authorized records only. |
| Work orders / Review inbox / Requests | Existing fault-to-repair workflow, duplicate review, return/reassign, already-fixed review, repair evidence, manager verification, optimistic concurrency and audit activity. |
| Recurrence / Upcoming | Every-N-days preventive plans, enabled/paused state and next-run date. EventBridge Scheduler checks hourly. Due requests await manager review; they are not automatically approved. |
| Workflows | Versioned acknowledgment, repair and verification deadline policies. Changes apply to future transitions; previously scheduled deadlines retain their policy. |
| Asset monitoring | Open fault counts and manually recorded meter values. No live sensor connection is configured. |
| Meters / Automations | Manual readings, history, min/max thresholds, and enabled automation rules that create a review request when a reading breaches a threshold. Retrying the same reading idempotency key does not create another reading/request. |
| Inspection templates / responses | Manager-defined ordered checklists, asset selection, Pass/Fail/Not applicable answers and observations. Responses are immutable records. |
| Life tracking | Installed part, asset, installation date, expected life in days, calculated service date and remaining days. Calendar planning, not predictive maintenance. |
| Teams / Users | Team membership and equipment ownership; separately enforced account roles. The backend rechecks current identity and role on each request. |
| Download centre | Role-scoped spreadsheet-friendly CSV exports and bounded asset CSV import: 1 MB / 100 rows, preview and explicit confirmation, partial-result reporting. |
| Bulk archive / Archive | Preview and archive completed/rejected/merged/skipped work, then restore it. Unresolved work cannot be archived. Catalog records also support reversible archive with reference protection. No permanent spreadsheet delete. |
| Billing & usage | Application record counts and Admin link to AWS Billing console. No customer invoicing, subscription collection or measured AWS cost feed. |
| Help & accessibility | Keyboard navigation, focus visibility, screen-reader feedback, reduced motion, high contrast and larger text preferences. |

## Reliability boundaries

- Stock receipt updates purchase status, part quantity and movement history together. A duplicate receive or concurrent stale update fails without double-incrementing stock.
- Recurrence creates a deterministic occurrence and advances the plan in the same transaction. A duplicate invocation or stale plan cannot create duplicate requests. Overdue catch-up is coalesced into one request per due plan, then advances to the next future interval; at most 20 due plans are attempted per hourly invocation.
- Scheduled work may be skipped only before work starts, with a reason. Skipping does not alter the recurring plan.
- Catalog changes use a shared optimistic revision to serialize reference checks with writes in this low-traffic prototype. A concurrent catalog change may return409 and require refresh/retry. New work orders also add strongly read asset references in the same transaction, preventing archive races despite GSI lag.
- Catalog edits require record versions. Referring to archived records is rejected. Asset code reservations remain reserved after archive.
- Fault image rules remain five JPEG/PNG/WebP files, each up to 5 MiB and 25 MiB total. Client validation rejects a 500 MiB selection before requesting upload authorization. The server validates upload declarations, signed size constraints and actual stored content signatures.
- CSV exports quote fields and neutralize formula-like cell prefixes. CSV import is for assets only; native XLSX import is not implemented.
- The recurring scheduler and Lambda asynchronous execution have retries and a dead-letter queue. A failed delivery needs operator investigation; this prototype does not promise industrial control or real-time monitoring.
- This is one factory workspace, not isolated multi-tenant SaaS. Production rollout needs factory-scoped identity, capacity testing and operational ownership.
