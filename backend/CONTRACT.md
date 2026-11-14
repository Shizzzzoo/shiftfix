# Backend contract
Lambda handler `backend.api.handler`, stream handler `backend.deadlines.stream_handler`, deadline handler `backend.deadlines.expire_handler`, post-confirmation `backend.auth.post_confirmation`.
Environment: TABLE_NAME, ASSETS_BUCKET, USER_POOL_ID, SUPERVISOR_EMAIL, STATE_MACHINE_ARN (stream only). Python 3.13; boto3 provided by Lambda.

JWT must be Cognito ID token (email_verified true). /me returns {id,email,name,role}. roles admin/manager/worker/reporter with legacy aliases mapped (see Four-role iteration).
GET /machines -> {items:[{id,name,location}]}.
GET /workorders -> {items:[WorkOrder]} (all pages read; prototype).
GET /workorders/{id} -> WorkOrder plus activity:[{id,at,actorId,actorName,action,reason}], attachments photos have url signed.
POST /workorders header Idempotency-Key required; JSON {machineId,title,description,category?,priority:'low'|'medium'|'high'|'critical',attachments?:[{key,name,type,size}],relatedId?} -> WorkOrder. Matching machine/category pending/open jobs set possibleDuplicate true (suggestion only).
POST /workorders/{id}/actions {action,version,reason?,assigneeId?,assigneeName?,targetId?,attachments?}. action approve/reassign require assigneeId; return/clarify/reject/merge/block/rework/add_note require reason; merge targetId required. submit attaches repair photo(s). Empty attachments allowed but repair notes required. Returns WorkOrder.
GET /users admin/manager only -> {items:[{id,name,email,role}]}; POST /users/{id}/role {role:'manager'|'worker'|'reporter'} with hierarchy enforcement described below.
POST /uploads {files:[{name,type,size}]} -> {items:[{key,name,type,size,url,fields}]} S3 presigned POST. Multipart FormData: append every fields entry then file. Attach returned metadata only (omit url/fields) to create/submit. max 5 images, 5 MiB each, JPEG/PNG/WebP. Signing upload doesn't attach until work order commit.

WorkOrder: id,number ('WO-'+first8 uppercase UUID),machineId,machineName,title,description,category,priority,status,assignmentStatus,assigneeId,assigneeName,reporterId,reporterName,createdAt,updatedAt,version (integer),deadlineVersion (integer),deadline (UTC ISO),deadlineKind,overdue(bool),blocked(bool),possibleDuplicate(bool),attachments:[{key,name,type,size,stage:'before'|'after',url?}],relatedId?,mergedInto?.
status: pending_review/open/in_progress/awaiting_verification/closed/rejected/merged/needs_details. assignmentStatus unassigned/awaiting_acceptance/accepted/returned. Approval starts acknowledgement deadline; acceptance starts repair deadline; submit starts verification deadline. Rules configurable ACK_SECONDS (default3600), REPAIR_SECONDS(default14400), VERIFY_SECONDS(default7200). Closed/rejected/merged no deadline.
All mutations require version; stale version -> HTTP409. Reasons required ->400. Role/ownership mismatch->403. Private work orders visible to supervisor, reporters, current assignee; list filtered accordingly.
DynamoDB PK WORK#{id}, SK META; GSI1PK WORK, GSI1SK createdAt. Activity PK WORK#{id}, SK EVENT#{at}#{uuid}. Timer outbox PK TIMER#{uuid}, SK META, fields workOrderId,deadlineVersion,deadline,kind; stream invokes on INSERT, start execution name timer uuid. StepFunctions input same timer object; Wait timestamp $.deadline then call expire_handler. Timeout escalation preserves work/assignment status and sets overdue flag; stale revision or terminal/cleared deadline no-op.

keep_separate: supervisor only, required reason, clears possibleDuplicate without state/deadline change. resubmit: reporter only from needs_details, required reason, optional updated description, returns pending_review. add_note no longer implicitly resubmits; explicit resubmit is needed. Role assignment and work assignment reject unconfirmed/unverified/disabled Cognito users.

resolve_existing: supervisor only for open + returned assignment; requires reason and closes as supervisor-confirmed existing repair. Assignment history preserved. Technician's already-repaired claim alone never closes a work order.

## Four-role iteration
Canonical role values are admin, manager, worker, reporter. Legacy groups supervisor/technician/operator map to manager/worker/reporter. Verified SUPERVISOR_EMAIL is always admin, including existing sessions. Admin may set other users to manager, worker or reporter; managers may set only workers/reporters and cannot modify a manager/admin; no API grants admin or demotes the owner admin.
POST /onboarding body exactly {displayName:string 2..100,department:'production'|'maintenance'|'engineering'|'quality'|'operations'|'other',machineIds:string[] <=4 distinct registry IDs}. Client role/extra fields rejected. Success stores USER#sub / PROFILE and returns /me shape. GET /me -> {id,email,name,role,onboardingComplete:boolean,profile:{displayName,department,machineIds}|null}. Missing profile is incomplete, not a fake completed profile.
New reports include possibleResolved:boolean and internal relatedResolvedIds for same-machine/category closed work. Only admin/manager receive relatedResolvedIds and detail resolvedCandidates summaries; others receive boolean flag without hidden IDs. resolve_existing accepts pending_review/needs_details or open+returned, supervisor decision required with reason. It never auto-rejects a recurrence.
Uploads validate all files before signing any; max5 files x5MiB, total25MiB, JPEG/PNG/WebP only, boolean/noninteger sizes invalid. Attachment commits verify actual image magic via S3 ranged GET as well as metadata size/type.

Every request rechecks current Cognito membership and verified/enabled status before applying role rules, preventing old JWT group claims from retaining demoted permissions. Existing worker/manager names are read from completed profiles where available.
