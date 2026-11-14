# Deployment record
Region ap-south-1. Active CloudFormation stack shiftfix-live. Application: https://11z3m6ydfe.execute-api.ap-south-1.amazonaws.com
Artifacts bucket: shiftfix-artifacts-720443608839-ap-south-1.

CloudFront creation returned AccessDenied requiring account verification; app serves static frontend through API Gateway + Lambda instead. An intermediate stack failed because API Name was absent; fixed and cfn-lint validation passes. Failed stack names shiftfix and shiftfix-app remain for audit; retained state must be inspected before cleanup, not automatically deleted.

Rebuild: npm ci; npm run build; python3 scripts/package.py. Runtime identifiers from CloudFormation outputs go in public/config.json BEFORE the build. These are not secrets. Upload resulting ZIP under a new immutable S3 key, then update stack CodeKey using CloudFormation with CAPABILITY_NAMED_IAM and existing parameters; wait for UPDATE_COMPLETE. Use AWS MCP for agent-driven AWS operations. Do not overwrite a deployed package key.

Logs retained seven days. DynamoDB, evidence S3 bucket and Cognito pool retained on stack deletion. API throttles five requests/second, burst ten; no provisioned concurrency or servers. Account PAID with $100 remaining credits observed at start; not a hard spend cap. Initial stack was submitted with existing root session; runtime uses scoped service roles. No IAM access keys created. Dedicated human development identity still recommended.

Final deployed immutable CodeKey: backend-v8.zip. Additional intermediate retained table: shiftfix-app-Table-RXLR5WMM812U.

Four-role/onboarding iteration: CloudFormation UPDATE_COMPLETE with immutable backend-v6.zip. Added admin, manager, worker, reporter groups while preserving legacy groups and existing data. Backend authority refreshes live membership; bootstrap owner is Admin. Includes local Pexels factory assets.64 backend tests passed; local onboarding/overview axe scans reported no WCAG A/AA violations in tested states, along with upload preflight/focus/mobile checks. Full human verified sign-up remains owner-driven.

Operations expansion: final template `template-v8.json`, immutable code `backend-v8.zip`, CloudFormation UPDATE_COMPLETE. Added hourly EventBridge Scheduler, scoped invocation role and Planning Lambda with retries/DLQ. Planning role includes the table actions and Query on GSI1, needed for duplicate advisory checks. Existing data/auth/evidence resources preserved. 89 backend tests pass. Live purchase/stock/recurrence checks and cleanup are recorded in verification.md; module setup is in operations-guide.md.
