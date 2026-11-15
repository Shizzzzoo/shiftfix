# AWS Builder Center submission fields

Title:
ShiftFix: Serverless Factory Maintenance Workflows

Description (339 characters):
Turn factory fault reports and photo evidence into accountable repairs, with duplicate review, role-based ownership, verified completion and durable deadline tracking. Built on AWS serverless services, with Maintiny for permission-scoped search and reviewed drafts; Gemini temporarily replaces Bedrock because account access is restricted.

Body:
Enable Markdown; paste docs/submission-body.md. Insert docs/submission-assets/architecture.png near How the AWS services connect.
Architecture alt text: React users authenticate with Cognito and call JWT-protected API Gateway routes. Lambda applies maintenance rules and stores records in DynamoDB; private photos use signed S3 access. DynamoDB Streams starts a Step Functions deadline wait, followed by a current-state check. EventBridge Scheduler triggers preventive-plan checks. Maintiny uses scoped DynamoDB tools and a temporary Gemini provider limited to fictional demo data.

Tags (select the closest available dropdown values, maximum five):
Serverless; AWS Lambda; Amazon DynamoDB; AWS Step Functions; Amazon S3.

Repository:
https://github.com/Shizzzzoo/shiftfix

Live application:
https://11z3m6ydfe.execute-api.ap-south-1.amazonaws.com/?release=maintiny-v20

Endpoint or live demo:
The supplied rules require a PUBLIC video shorter than 3 minutes in the submission's demo field. If this UI field is that demo field, put the video URL here and retain the live app link in the body. If a separate challenge video field exists, place the public video there and the live app URL here. No video URL has been supplied in this session.

Jupyter or SageMaker notebook:
Leave blank. This project does not use either notebook product.

Cover:
Optional. Keep a relevant factory/application cover. Recommended 1200x675; JPG/PNG/WebP; maximum2MB; avoid text-heavy cover imagery. Existing factory photography credit: YIHAI LASER / Pexels, documented in docs/image-credits.md. Architecture.png is intended as a body illustration, not a text-free cover.

Before Publish:
- Add the real public video URL under3minutes to the required demo field and ensure playback works signed out.
- Confirm the written project explains the problem, running behavior and connected serverless services.
- Preserve temporary Gemini/Bedrock restriction disclosure and fictional demo labeling.
- Confirm eligibility and original/previously-unpublished project requirements against the supplied rules.
- Do not put passwords, keys, secret identifiers or private factory information in the submission or recording.
