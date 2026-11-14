# Deployment record
Region ap-south-1. Active CloudFormation stack shiftfix-live. Application: https://11z3m6ydfe.execute-api.ap-south-1.amazonaws.com
Artifacts bucket: shiftfix-artifacts-720443608839-ap-south-1.

CloudFront creation returned AccessDenied requiring account verification; app serves static frontend through API Gateway + Lambda instead. An intermediate stack failed because API Name was absent; fixed and cfn-lint validation passes. Failed stack names shiftfix and shiftfix-app remain for audit; retained state must be inspected before cleanup, not automatically deleted.

Rebuild: npm ci; npm run build; python3 scripts/package.py. Runtime identifiers from CloudFormation outputs go in public/config.json BEFORE the build. These are not secrets. Upload resulting ZIP under a new immutable S3 key, then update stack CodeKey using CloudFormation with CAPABILITY_NAMED_IAM and existing parameters; wait for UPDATE_COMPLETE. Use AWS MCP for agent-driven AWS operations. Do not overwrite a deployed package key.

Logs retained seven days. DynamoDB, evidence S3 bucket and Cognito pool retained on stack deletion. API throttles five requests/second, burst ten; no provisioned concurrency or servers. Account PAID with $100 remaining credits observed at start; not a hard spend cap. Initial stack was submitted with existing root session; runtime uses scoped service roles. No IAM access keys created. Dedicated human development identity still recommended.

Final deployed immutable CodeKey: backend-v4.zip. Additional intermediate retained table: shiftfix-app-Table-RXLR5WMM812U.
