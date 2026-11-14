# ShiftFix design
Build an original hackathon prototype for one factory: report a fault with machine, description, priority and photos; supervisor approves/assigns, merges duplicates, requests clarification or rejects with reason; technician accepts/returns assignment, marks blocked, submits repair evidence; supervisor verifies or returns for rework. Maintain an immutable activity timeline. Explicitly preserve reports when merging. Same machine can have different faults. Closed faults can have linked recurrence reports.

## Approach
Use React/Vite/TypeScript frontend, Python Lambda API, API Gateway HTTP JWT authorizer, Cognito email/password auth, DynamoDB on-demand and versioned optimistic concurrency, private S3 signed photo uploads, Step Functions Standard waits for deadlines. Infrastructure via CloudFormation, static HTTPS frontend via CloudFront/private S3. Prefer explicit deadline executions with version checks over callback credentials; stale timers no-op. One factory, fixed machine registry, no AI/parts inventory/messaging external integrations. Cognito defaults to operator; confirmed email mohammedsahlbaig@gmail.com is supervisor, email verification required. Supervisor can promote signed-up users to technicians.

## Constraints and decisions
Backend permissions enforce roles independently of UI. Technician writes only own current assignments. Rejection/return/merge/verification-rejection requires reason. Work status and assignment status and flags separate. Idempotency key for create; conditional version checks for mutations. Attachments maximum 5 x 5MB per upload batch, JPEG/PNG/WebP only; private signed downloads, no public bucket, unique keys. No automatic deletion of evidence attached to open jobs. No infrastructure continuously running. Account PAID with $100 credits observed; no cost guarantee. Workloads small and throttled. Existing root session submits initial CloudFormation stack, dedicated service roles perform runtime operations. Deployment roles scoped to ShiftFix where practical; no root access keys created.

## Deliverables
Working deployed app with authentic backend; source repo, setup/cleanup docs, architecture diagram, honest limitations and submission article draft/video script. Verify role boundaries, duplicate handling, assignment return, repair rejection, idempotency and stale timers. Do not publish article or video without explicit instruction.

## UI
Industrial operations console: charcoal sidebar, orange accent, light gray canvas, white work-order list and detail pane; review inbox/overview/work orders/machines, report dialog, Cognito sign in/signup. Desktop split panes collapse on mobile. Empty database shows honest empty state; optional clearly labeled demo records only. All visible controls work.

## Deployment ruling
CloudFront creation is blocked by account verification, so deploy UI via API Gateway public static GET routes and a dedicated static Lambda. All data routes still require Cognito JWTs. The first stack rolled back. A missing HTTP API Name caused a second rollback; corrected and cfn-lint passes. Active stack shiftfix-live created successfully. Record all retained resources rather than deleting them without instruction.
