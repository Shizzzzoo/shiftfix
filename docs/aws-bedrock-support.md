# Prepared AWS Support request — not submitted

Subject: Review account-level Amazon Bedrock restriction: Operation not allowed

Hello AWS Support,

Please review the account-level restriction preventing Amazon Bedrock inference in account 720443608839.

- Region: ap-south-1
- API: Amazon Bedrock Runtime Converse
- Model/inference profile: apac.amazon.nova-micro-v1:0
- Lambda execution role: arn:aws:iam::720443608839:role/shiftfix-live-AssistantRole
- Error: ValidationException: Operation not allowed
- Request ID: f50463a6-fe6c-4f21-acac-6c582c8511ee (final deployed version, 15 November 2026)
- The direct AWS MCP invocation also returned AccessDeniedException saying the account is currently being verified.

The application is ShiftFix, a serverless factory-maintenance hackathon prototype. Its assistant uses narrowly scoped model invocation permissions, a small allowlist of role-authorized tools and human confirmation before work-order creation. Model discovery, the application API and DynamoDB operations work. The account plan reports PAID and ACTIVE. No region/model changes were attempted to bypass the restriction.

AWS Knowledge Center describes Operation not allowed as an account security restriction requiring Support: https://repost.aws/knowledge-center/bedrock-invokemodel-api-error

Please review the restriction, enable Bedrock Runtime access if appropriate, and tell us which account-verification steps are required. The hackathon submission deadline is 16 November 2026.

Thank you.

Submission status: not submitted. The AWS Support API returned SubscriptionRequiredException: Amazon Web Services Premium Support Subscription is required to use this service. Account/billing support must be pursued through AWS Support Center with explicit authorization to send the case; no paid support upgrade is required or authorized by this document.
