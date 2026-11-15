# Roles, onboarding, evidence and accessibility

## Access hierarchy
Admin is the verified configured owner; only the backend grants this bootstrap role. Admins manage Managers, Workers and Reporters, and can perform management actions. Managers review/assign/merge/reject/verify maintenance requests and manage Worker/Reporter access; they cannot grant or change Admin/Manager access. Workers act only on their current assignments. Reporters create faults, add notes to their own requests and respond to clarification. Reports never become resolved merely because a Worker returns them as already repaired.

Every API call rechecks current Cognito membership and enabled/verified status, so a demoted user's older token does not preserve former authority. Existing supervisor/technician/operator groups map to manager/worker/reporter. The verified configured owner maps to Admin even with a legacy token. Old groups remain to avoid deleting existing memberships. No client onboarding field can grant roles.

## First-time setup
After email verification and sign-in, a user without a stored profile sees six steps: profile, assigned role, workspace, operations, accessibility and ready. Profile collects a display name, department and up to four optional machines, with a searchable machine list and a disabled fifth choice. Workspace covers dashboard filters, work orders/requests, assets/types/categories and the location hierarchy. Operations covers inventory/purchasing, planning/deadlines, inspections/meters, people, exports and archive. Accessibility includes working high-contrast/larger-text controls and keyboard, status, screen-reader and reduced-motion guidance.

Only “Open my workspace” persists the profile in DynamoDB; Back preserves the draft. Reading preferences save on this device as they change. This applies to newly verified email accounts, including Gmail, and is not Google social sign-in. Existing users can open “Workspace guide” from the header or Help & accessibility. Replay starts at Workspace, closes without writing the profile, and returns keyboard focus to its opening button. The tour explains role restrictions and identifies fictional records, display-only demo people and paused rules/plans.

## Upload boundaries
Maximum five images, 5 MiB each, 25 MiB total. Browser preflight checks the entire selection before generating/uploading anything. API prevalidates the whole batch before signing S3 POST policies. S3 enforces the per-object content-length policy. Attachment commits check object ownership, actual size, content type and PNG/JPEG/WebP signatures. SVG and masquerading text are rejected. Signature checks are not a complete malware scanner or full image decoder. Selecting an invalid replacement clears previous files and cached upload metadata and blocks form submission until corrected or explicitly continued without that image.

## Already-completed repairs
A new report matching a closed machine/category repair gets a possibleResolved advisory. Managers/Admins can inspect related completed work; other users do not receive private historical IDs. A Manager can confirm already resolved with a mandatory reason, or approve a new recurrence. It is never automatically discarded or silently merged. Concurrent decisions still use version conditions and append an activity record.

## Accessibility
Search fields keep keyboard focus inside their own border, without the old protruding orange input outline. Other controls retain visible keyboard focus. Dashboard Filters opens a named modal drawer with a focus cycle, Escape, return focus, Apply/Cancel, draft reset, removable applied chips and date-range validation. Location changes clear dependent zone/sub-zone choices and restrict both lists.

Skip link, semantic navigation/main/table landmarks, named keyboard-operable work-order buttons, visible focus, modal focus trap/restoration and Escape, screen-reader error/status announcements, meaningful photo alt text, color-independent status labels, contrast-safe primary actions, high contrast and larger text preferences, reduced-motion support, mobile responsive views. Automated axe WCAG A/AA checks found zero violations in tested onboarding and overview states after contrast fixes; that is not a complete WCAG conformance certification. Browser plugin/IAB unavailable earlier in this environment; Playwright Chromium used. Checked desktop 1440x1000 and mobile 390x844.

## Verification
64 backend tests passed. TypeScript/Vite build and cfn-lint passed. Browser fixture checks: first-time setup completion, role explanation, profile saves, Admin team view, 500 MiB preflight zero upload requests, invalid replacement clearing, Escape and focus return, high contrast/larger text, no mobile overflow. Real email-code confirmation and the complete human multi-user repair flow still need the owner. Source images and license links: image-credits.md.
