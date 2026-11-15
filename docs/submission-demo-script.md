# Suggested 2:45 demo recording

An initial silent, captioned Playwright walkthrough is available at `docs/submission-assets/shiftfix-demo.mp4` (1:57.92). It is a **scripted UI demonstration with fictional API fixtures**, labeled in the video. Use it to review pacing and coverage. The challenge requires a public video of the build running end to end; the final submission should capture authenticated requests against the deployed API and actual saved work-order transitions. The video also needs a public YouTube, Vimeo, Facebook Video or Youku URL in the demo field.

Use real deployed screens, fictional demo records and prepared verified accounts. Do not show passwords, verification emails or cloud/API credentials. Only show steps that actually work; allow time for loading. The recording must remain below3minutes.

0:00–0:15 — Problem and overview
“ShiftFix helps a factory keep a fault owned across shift changes. A request keeps its equipment, evidence, responsible person, deadline and verification history together.” Show populated dashboard and fictional-data notice.

0:15–0:40 — Report a fault
Select a demo machine, enter a short fault description and upload a small permitted photo. Submit; show its actual saved work-order number. Use an original/permitted image.

0:40–1:05 — Review and ownership
In a pre-authenticated Manager/Admin account, review this report. Show duplicate/already-resolved advisories if present; make a deliberate review decision. Assign only to a genuine verified Worker account, never a display-only demo person.

1:05–1:35 — Worker and verification
Switch to the assigned Worker's prepared session. Accept and submit repair notes/evidence. Return to Manager and verify or request rework. Show the resulting activity timeline. Do not imply prerecorded demo history is a repair you just performed.

1:35–2:05 — Maintiny
Open Ask Maintiny at the bottom-right. Ask which fictional parts need replenishment, or show demo work awaiting verification. Show actual returned data/source links. Expand into the saved-chat workspace; show persistence and a delete confirmation if time permits. Say: “The assistant currently uses a temporary Gemini provider because Bedrock account access is restricted. Its tools are limited to fictional demo data.”

2:05–2:30 — Architecture
Display architecture.png. “API Gateway and Lambda enforce rules; DynamoDB stores work and audit records; private photos live in S3. A timer record enters DynamoDB Streams and starts a Step Functions wait. The final deadline check verifies the current version, so an old timer cannot escalate newer work. CloudFormation deploys this without a CI/CD pipeline.”

2:30–2:45 — Reuse and close
“Conditional updates handle concurrent decisions, idempotency handles retries, and a manager verifies completion. The same pattern can support other equipment and facilities workflows.” End on the live app and actual public repository link if one is available.

If the multi-user sequence has not been rehearsed, complete it before filming rather than presenting a mocked interaction as live behavior. Shorten the catalog tour first; the end-to-end build demonstration is mandatory under the supplied rules.
