# ShiftFix deeper research: factory behavior and accountability

Completed 2026-11-15, continuing the research started on 2026-11-14. This adds 24 factory workflow concepts and 60 acceptance cases to the earlier research. It also records six new local probe observations. Research did not change application code, deploy a release, create users or alter live data. The last verified live release remains backend-v9.zip; live account state was not re-inventoried in this continuation.

Read with the [24-concept factory research](2026-11-14-factory-workflows-round2.md), [60 additional acceptance cases](2026-11-15-additional-edgecases.csv), and [raw probe output](2026-11-14-round2-probe-results.json). The earlier 100-case matrix remains separate; together the two CSVs contain 160 acceptance cases. They are proposed behavior and existing-test/reproduced observations, not 160 confirmed defects.

## Six new observations from current code

| ID | What the isolated probe observed | Why it matters | Recommended repair |
| --- | --- | --- | --- |
| S01 | Two different persisted IDs produce the same human label `WO-981FAB7A`. The number is derived from the first 8 hexadecimal characters of the ID. | Internal keys remain distinct and protected, but users referring to only the work-order number can be ambiguous. No record overwrite or unauthorized access was demonstrated. | Enforce a unique human reference transactionally, or use the full unique identifier as canonical reference. Search/export/copy must preserve that identity; never mutate a record by the first matching display label. |
| S02 | A reassignment event contains actor, action, time and an empty reason, but not from/to assignee IDs or from/to versions. Earlier worker A is absent from all returned activity after worker B becomes current. | An audit event exists, but that event stream cannot reconstruct assignment history. A new handover feature should not claim accountable ownership history from data that was never stored. | Record meaningful before/after changes, versions, operation ID and actor/source metadata in the same transaction as the state change. Old events should remain explicitly incomplete, not backfilled with invented facts. |
| S03 | The worker profile says `Current display name`, but approving a job stores `Original signup name` as assigneeName. | User roster and job labels can disagree after onboarding/profile changes. This is display consistency, not an authorization bypass. | Resolve assigned-person labels through the same profile logic as the roster; retain historical actor-name snapshots on past events. |
| S04 | A full receipt raises stock from 1000000000 to 1000000001. A later name-only edit fails 400 because validate(parts) enforces the original quantity cap. | This is a deliberately extreme numeric boundary. Mutation paths enforce inconsistent balance invariants and can create a record that an ordinary edit rejects. | Apply one post-operation balance range to create, receive and adjust; make the rejection atomic and explicit. Do not reduce stock silently to fit a cap. |
| S05 | A base64-decoded invalid UTF-8 body returns 500 and logs `UnicodeDecodeError`. | Invalid client input is classified as a server fault, obscuring operational error rates and recovery guidance. | Put transport decode inside input validation, reject malformed UTF-8/base64 with a safe 4xx, and avoid logging the private body. |
| S06 | A 17094-character body containing 68094 UTF-8 bytes succeeds despite the 65536 comparison. An unrecognized field is ignored by work-order creation. | Current body budget measures Python characters, not encoded bytes. The probe called the Lambda handler directly and did not test API Gateway transport rejection. It is not an unlimited-request exploit; upstream service limits and field validation still exist. | Define and enforce an encoded-byte budget and a consistent command-field allowlist before processing. Preserve clear 4xx/413 errors. |

Evidence source: `scripts/research-round2-probes.py`, using only moto and fictional actors. The work-order prefix collision is found by a deterministic local hash search and then confirmed with two isolated creates. It was not searched for or created in the live application. S04 is a boundary exercise, not a claim that normal factory quantities approach one billion.

Reproduce:

```sh
uv run --with boto3 --with 'moto[dynamodb,s3]' --with pillow python scripts/research-round2-probes.py
```

These probes describe current behavior. Future acceptance tests should require corrected behavior rather than preserve the findings as expected defects.

## Product additions that give the existing screens more meaning

### 1. Asset passport and correct-spare view

One asset detail page can combine manufacturer/model/serial, current location, responsible team, reviewed criticality, approved spare references, manuals, previous repairs and upcoming maintenance. A part's reverse view answers where it fits. A recorded historical issue is evidence of usage, not approval that the part fits that machine.

Proposed day-sized slice:asset–part links with fitment notes plus current references. Keep BOM engineering, model-revision compatibility and automated substitution decisions out of that slice. [Fiix parts and BOM](https://helpdesk.fiixsoftware.com/hc/en-us/articles/210056226-Getting-started-with-parts-and-supplies).

### 2. Criticality and urgency as separate decisions

A critical machine can have a low-urgency cosmetic defect. An ordinary asset can have an urgent fault. Store asset criticality with a short reason and review owner while keeping work-order priority separate. Preserve the historical reason when evaluating old work.

MaintainX explicitly documents asset criticality as a property usable for filtering/reporting. The distinction from our job-priority contract is a ShiftFix design recommendation. [Asset criticality](https://help.getmaintainx.com/about-assets).

### 3. Repeat-failure review

Three seal failures after three verified repairs are three real incidents linked to one investigation. They should not disappear through duplicate merging. A small record can capture symptom, linked incidents, suspected/confirmed cause, supporting evidence, improvement-action owner and later effectiveness check. Unknown cause remains an allowed honest state.

This is a stronger learning workflow than treating replacement of the same part as proof that the underlying problem was solved. [MaintainX root-cause workflow](https://help.getmaintainx.com/create-a-root-cause-analysis-report).

### 4. Readiness and next-action queue

A proposed derived supervisor view should answer why each repair cannot proceed:review pending, wrong owner, awaiting spare, missing procedure, no production access window, awaiting specialist, repair submitted, or verification pending. Each reason needs its source link and a next owner/action. Avoid a new manually edited status that can drift from source work, stock or assignment records.

Keep the first version deterministic. A shortage should name the part and available quantity; an assignment problem should name the current owner and return reason. This is our proposed product design, not a claimed vendor capability.

### 5. Job-pinned SOP reference

Show which published instruction revision was chosen for this repair. If a new revision appears, the current job keeps its original reference until a designated owner records an applicability decision. Store publish/effective dates and a job snapshot; do not silently replace steps already executed. A full change-control/approval engine is a separate feature. [MaintainX procedures](https://help.getmaintainx.com/about-procedures), [procedure edits/history](https://help.getmaintainx.com/edit-a-procedure).

### 6. Shutdown package overview

Group the electrical, mechanical and guarding jobs required before a line can be handed back. Show independent owners, blockers and verification. Our proposed rule is to refuse required-child completion by implication; package closure requires all required work to be verified or explicitly waived under the factory's policy.

MaintainX documents parent/child work and also a parent-Done action that can complete unfinished children. That is evidence to choose our own closure semantics deliberately, not behavior we should copy automatically. [Parent/sub-work-order behavior](https://help.getmaintainx.com/parent-and-sub-work-orders).

## Deeper models to design before claiming support

- **Serialized repairable spare:** track removed motor M17, installed motor M22 and each unit's custody/history. A stock quantity alone cannot represent a unit installed on exactly one machine.
- **Quarantine/usable balance:** physical stock includes units awaiting test; readiness must use serviceable stock under an explicit release decision.
- **Lot lineage:** record which lot quantities a job actually used, so a later suspect lot has a bounded impact list.
- **Directional substitute:** A can replaceB under a specific fitment approval; the reverse is not implied.
- **Recipe versus stock kit:** a recipe expands required component lines. A physically assembled kit requires assembly/disassembly stock transactions and cannot also leave its components counted on the shelf.
- **Partial receipt and short-close:** preserve ordered, arrived, accepted, rejected, canceled and outstanding quantities instead of overwriting the original order.
- **Calibration:** preserve as-found and as-left readings, tolerance basis and the exact physical reference standard used. A final pass does not erase an initial failure.
- **Production access:** a technician's free time is not the machine's released maintenance window. Both must fit the estimated duration.
- **External contractor:** vendor contact, internal sponsor, performedBy and recordedBy are distinct. Actual portal access introduces a separate scoped identity boundary.
- **Transfer and retirement:** keep old installation context, open jobs, plans, child components and replacement references. Catalog archive alone is not a complete retirement process.

The source-annotated contracts and concrete examples for these models are in the 24-concept note. The proposal does not claim a legal safety authorization, a complete vendor portal, an accounting ledger or full traceability from an optional metadata field.

## Strengthening the audit envelope

For new events, a useful minimal envelope is:

```json
{
  "eventId": "unique immutable event id",
  "operationId": "durable logical command id",
  "workOrderId": "full unique id",
  "at": "server timestamp",
  "actorId": "authenticated actor or explicit service actor",
  "actorRoleAtAction": "authority at the action",
  "source": "ui | workflow | import",
  "action": "reassign",
  "fromVersion": 4,
  "toVersion": 5,
  "changes": {
    "assigneeId": {"before": "worker-A", "after": "worker-B"}
  },
  "reason": "Worker A unavailable; accepted by Worker B"
}
```

This is a proposed schema, not current output. It must commit with the business mutation. Do not put passwords, authentication values, signed evidence URLs or entire request bodies into it. Keep raw-image provenance in a separate authorized evidence record. Current role is still checked for the next action; storing an old role in an event never grants future authority.

An append-only event alone does not guarantee complete field history, tamper-proof retention or legal nonrepudiation. The current runtime uses ordinary versioned business writes and stored audit rows, so claims should stay at that level until stronger mechanisms are built and tested.

## What this changes in the one-day plan

The earlier integrity/retry → job-linked parts → inspection follow-up → handover sequence still stands. Add unique canonical work references and before/after assignment events to its foundation, because every new relationship and handover will rely on them. Profile-label and input-validation fixes are bounded follow-ups. Numeric-cap alignment is low-urgency boundary hardening.

If one additional visible factory feature fits, choose **criticality + correct-spare links** or **repeat-failure investigation**. Keep recipes, shutdown packages and controlled SOPs at their stated small slices. Full kit inventory, lot/serial ledgers, contractor accounts, calibration mathematics and automatic dependency scheduling should replace existing scope if selected, not be added as surprise one-day obligations.

Research completion status:documentation and six isolated observations are complete. Implementation is still proposed. Production data and the application release were not changed by this research.
