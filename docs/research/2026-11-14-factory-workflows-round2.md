# ShiftFix: deeper factory workflows, research round 2

Researched 2026-11-14. This note adds 24 feature concepts after reading the [first CMMS comparison](2026-11-14-cmms-feature-research.md) and [final-day plan](2026-11-14-final-day-plan.md). It does not repeat their core issue/return, inspection follow-up, shift handover, QR, PM cadence, meter suppression, offline or site-isolation proposals. Some topics were named in their backlog; this round supplies the missing domain model and concrete factory decisions.

**Recommendation:** retain the existing final-day priority order. If there is room for one more small product improvement, choose asset criticality with a reason, an asset-specific parts/where-used view, or a structured repeat-failure investigation. These give existing records more meaning. Serialized spares, lot stock, purchasing reconciliation and shutdown dependency enforcement require new transaction rules and should remain future work.

Evidence below is public first-party product documentation, not executed vendor testing. “Vendor evidence” states only what the cited page establishes. Every “Proposed contract,” example and implementation cut is a ShiftFix recommendation, not a claim of vendor behavior or a finding that ShiftFix currently lacks it. No application code, deployed runtime or account state was inspected in this round. Factory authorization means an explicit product decision by designated factory users; it makes no legal or regulatory compliance claim. Estimates are omitted because extension points have not been audited.

## Equipment structure and investment decisions

### 1. Component hierarchy with explicit operational impact

**Vendor evidence:** MaintainX models components as independently maintainable sub-assets. Its hierarchy settings can ask which related statuses to update, update ancestors, or propagate more broadly. Hierarchy deletion and movement can affect whole subtrees. [Hierarchy management](https://help.getmaintainx.com/create-and-manage-asset-hierarchies).

**Proposed contract and failure case:** a packaging line contains two parallel pumps. Pump A going offline need not mark Pump B offline; the line may run at reduced capacity. Record the failed component and a separate operator-confirmed production impact. Reject A → B → A parent cycles. Preview the affected subtree before movement or retirement; never infer that every descendant physically failed.

**One-day cut:** show parent/component breadcrumbs and an explicit impact note. **Defer:** status propagation, capacity calculations and bulk subtree mutations.

### 2. Asset BOM, fitment and reverse where-used

**Vendor evidence:** Fiix associates parts and quantities with assets through its BOM view, which also shows associated assets. [Parts and BOM setup](https://helpdesk.fiixsoftware.com/hc/en-us/articles/210056226-Getting-started-with-parts-and-supplies).

**Proposed contract and failure case:** press P1 and P2 have similar names but different seal diameters. P1's asset page should list its approved seal and fitment note; the seal page should list all known compatible machines. Distinguish “fits this model/revision” from “was consumed once on a job.” A mistaken historic issue must not automatically become approved fitment. A BOM quantity is a design requirement, not live stock or a reservation.

**One-day cut:** bidirectional asset–part references with manufacturer/model notes. **Defer:** configurable assemblies, engineering BOM revisions and automatic compatibility decisions.

### 3. Criticality separate from fault urgency

**Vendor evidence:** MaintainX has an asset criticality field with Critical, Important and Normal values used for filtering/reporting. [About Assets](https://help.getmaintainx.com/about-assets).

**Proposed contract and failure case:** the single compressed-air dryer is critical because many lines depend on it; a cosmetic casing dent on that dryer may still be a low-urgency job. Show both asset criticality and job priority, with a short reason and review owner. A manager changing the criticality next month must not rewrite the reason a historic repair was prioritized. “Unknown” should remain distinct from Normal.

**One-day cut:** reasoned criticality field and filter. **Defer:** weighted risk scoring and automatic priority escalation until the factory supplies its factors.

### 4. Warranty-aware repair decision and claim record

**Vendor evidence:** Fiix stores part warranties and explicitly notes that consumable warranties can be difficult to track at one stock-item level; it suggests batch/lot-specific records. [Parts warranty setup](https://helpdesk.fiixsoftware.com/hc/en-us/articles/210056226-Getting-started-with-parts-and-supplies).

**Proposed contract and failure case:** two identical motors were bought six months apart; only one remains covered. A generic SKU warranty must not mark both covered. Attach coverage to the relevant asset/serial/receipt or lot, with document, expiry basis and contact. Separate “possible coverage,” “claim submitted,” “accepted” and “rejected.” A covered-looking date is a prompt for review, not proof the supplier will pay. Preserve the failed serial and evidence when a replacement arrives.

**One-day cut:** warranty document/date on the asset plus a manager review note. **Defer:** claim automation, supplier messaging and coverage adjudication.

### 5. Repair-versus-replace worksheet with uncertain inputs

**Vendor evidence:** MaintainX calculates straight-line depreciation from supplied asset information and presents book value; its help page frames this as information for repair/replacement decisions. [Asset Depreciation](https://help.getmaintainx.com/asset-depreciation).

**Proposed contract and failure case:** a fully depreciated but healthy conveyor still has operational value. A zero book value must not automatically recommend scrapping it. Compare the repair quote, replacement quote, lead time, repeat history and expected outage using dated sources. Label missing or estimated numbers and let a designated decision owner record the choice. Keep book value, replacement cost and avoided outage estimate as distinct inputs.

**One-day cut:** linked quotes and a decision note using existing attachments. **Defer:** accounting depreciation, lifecycle forecasting and automated replacement recommendations.

## Storeroom behavior beyond a quantity field

### 6. Serialized repairable spares and installation custody

**Vendor evidence:** IBM describes rotating items as interchangeable assets that change locations and are repaired rather than replaced. [Inventory items](https://www.ibm.com/docs/en/masv-and-l/maximo-manage/cd?topic=inventory-items).

**Proposed contract and failure case:** motor serial M17 is removed from Line 1 while M22 is installed. “Issue one motor” is insufficient: M17 moves to repair, M22 moves from storeroom to an installation, and each keeps its own service history. Prevent M22 from being simultaneously installed on two machines. A supplier's repaired return must retain M17's identity rather than silently create a new motor. Consuming a spare and installing an asset are linked but different events.

**One-day cut:** record removed/installed serials as structured job evidence. **Defer:** serialized stock balances, custody transfers and automatic installation history.

### 7. Condition-separated stock and quarantine release

**Vendor evidence:** Maximo condition-enabled items have physical condition codes and associated rates; condition is recorded through inventory actions. Its documentation says lotted items cannot be condition-enabled. [Condition-enabled items](https://www.ibm.com/docs/en/masv-and-l/maximo-manage/cd?topic=items-condition-enabled).

**Proposed contract and failure case:** four rebuilt valves and one failed valve share a part number. A balance of five must not tell the planner five are usable. Keep serviceable, awaiting test, repair and scrap quantities separate; a completed repair job must not automatically certify the returned valve serviceable. A named reviewer releases the particular unit or batch with test evidence. Show physical count and usable count separately.

**One-day cut:** conspicuous condition note and manual release evidence; do not include uncertain stock in a readiness promise. **Defer:** condition-specific valuation and transactions.

### 8. Lot lineage, expiry and maintenance impact lookup

**Vendor evidence:** IBM documents lotted inventory with shelf life/expiry and inventory movements split across bins/lots. [Inventory items](https://www.ibm.com/docs/en/masv-and-l/maximo-manage/cd?topic=inventory-items), [Pick and stage](https://www.ibm.com/docs/en/masv-and-l/maximo-manage/cd?topic=inventory-pick-stage).

**Proposed contract and failure case:** an adhesive lot is later found defective. The factory must find which repairs used lot L2409, not every job that used the adhesive SKU. An issue drawing three tubes from one lot and two from another keeps two trace lines totaling five. A bin transfer retains expiry and supplier lot; it cannot reset the shelf-life clock. A manually extended expiry requires a separate recorded decision. Link affected maintenance work for review without claiming automatic product-batch genealogy.

**One-day cut:** optional lot field on receipt/issue evidence, clearly incomplete traceability. **Defer:** lot balances, expiry allocation and recall-impact completeness claims.

### 9. Directional, reviewed part substitutions

**Vendor evidence:** IBM alternate-item relationships are explicitly configured. To make substitution reciprocal, its instructions say to add each item as the other's alternate. [Adding alternate items](https://www.ibm.com/docs/en/masv-and-l/maximo-manage/cd?topic=records-adding-alternate-items).

**Proposed contract and failure case:** a high-temperature seal may substitute for a standard seal, while the reverse is unsuitable on the hot press. Record A → B, the permitted asset context, quantity/unit equivalence and approving factory user. Picking a similar name must not silently merge stock. The job records the requested part and the actual substitute. If the substitute expires or is archived between planning and issue, recheck before issue.

**One-day cut:** reviewed substitution note and actual-part selection. **Defer:** automatic availability substitution and chained equivalence inference.

### 10. Parts recipes versus assembled stock kits

**Vendor evidence:** Maximo assembly increases kit stock and decreases component balances; assembled components are not separately counted. It excludes rotating, condition-enabled and lotted components from kits. [Item kits, Maximo Asset Management 7.6.1](https://www.ibm.com/docs/en/mam/7.6.1?topic=overview-item-kits).

**Proposed contract and failure case:** an oil-service recipe contains one filter and six litres of oil. Adding that recipe to a job should expand component requirements. It must not also create one physical stocked kit, which would double-count the same filter. A physical kit needs a separate assembly/disassembly ledger. Partial unused returns require component accounting, not merely “return 0.3 kits.” Snapshot the recipe so later edits do not alter old consumption.

**One-day cut:** saved recipe expanded into ordinary part lines. **Defer:** physical kit assembly, nested kits and kit valuation. A kitted job bag is also distinct from a stocked kit SKU.

### 11. Shipment receipts, backorders and deliberate short-close

**Vendor evidence:** MaintainX supports multiple shipments, receipt records and partial fulfillment. Administrators can complete a partially fulfilled PO and undo completion if outstanding goods arrive later. [Fulfillment](https://help.getmaintainx.com/fulfill-a-purchase-order), [Completion](https://help.getmaintainx.com/complete-a-purchase-order).

**Proposed contract and failure case:** order ten bearings, receive four, then the vendor cancels six. Display ordered 10, received 4, canceled remainder 6 and outstanding 0; do not rewrite ordered quantity to four. A late second shipment cannot be mistaken for a retry of the first packing slip. If five unexpected units arrive, require an explicit overreceipt decision rather than silently losing the discrepancy behind a zero outstanding value.

**One-day cut:** show packing slip/reference and a manual outstanding note using current receiving. **Defer:** multi-receipt balances, short-close/reopen and receipt corrections as one coherent ledger change.

### 12. Receipt inspection, rejected delivery and correction distinction

**Vendor evidence:** IBM documents material receipts waiting for inspection, followed by accepted quantity transferred to storeroom and rejected quantity returned. This cited example is Maximo Asset Management 7.6.1. [Material receipt inspection](https://www.ibm.com/docs/en/mam/7.6.1?topic=application-material-receipts-inspection-required).

**Proposed contract and failure case:** eight sensors arrive, two are cracked. “Received eight” must not advertise eight installable sensors while inspection is pending. Record 8 arrived, 6 accepted and 2 rejected. Returning a defective delivered unit, voiding an accidental duplicate receipt and returning an unused job part are distinct business events. If the six accepted sensors have already been issued, a receipt correction cannot simply subtract eight from available stock.

**One-day cut:** receiving condition/evidence and an explicit hold note; no automated quality-release claim. **Defer:** holding-bin transactions, inspection acceptance and linked supplier returns.

### 13. PO–receipt–invoice reconciliation without payment automation

**Vendor evidence:** IBM's Oracle connector documentation distinguishes three-way matching of PO, invoice and receipt from four-way matching that adds acceptance for rotating/inspection items. This is connector-specific evidence, not a statement of every configuration. [Centralized invoices](https://www.ibm.com/docs/en/maximo-ora-con/8.1.0?topic=integration-centralized-invoices).

**Proposed contract and failure case:** the PO orders 10 valves at 100 each, only 6 are accepted, and the invoice bills 10 at 110. Flag both quantity and price differences. Freight, currency and taxes need explicit treatment; comparing header totals alone can hide an offsetting error. Re-entering the same vendor invoice number should raise a duplicate candidate, and later credit notes retain links to the original discrepancy.

**One-day cut:** attach invoice and record manually reviewed discrepancies. **Defer:** invoice approval engine, financial posting, OCR matching and any supplier payment action.

## Coordinating a factory shutdown

### 14. Shutdown package with independently verified child jobs

**Vendor evidence:** current MaintainX docs support parent/sub-work orders, with parts and procedures on child jobs and aggregate parent progress/cost. Setting the parent Done can mark unfinished children Done. [Parent and Sub-Work Orders](https://help.getmaintainx.com/parent-and-sub-work-orders). Its April 2026 update says this replaces the older multi-asset feature. [Release documentation](https://help.getmaintainx.com/help-center-updates/april-2026).

**Proposed contract and failure case:** a weekend line shutdown has electrical, lubrication and guarding jobs. One completed motor service must not close the package while guarding work remains unverified. Adopt a stricter ShiftFix contract: parent closure refuses required unfinished children, with explicit reviewed waiver/cancellation rather than implicit completion. Display child owners and blockers. Aggregate child spending once; do not add parent costs again.

**One-day cut:** read-only package/group ID with child progress. **Defer:** cascading creation, status inheritance and package-level closure enforcement.

### 15. Dependencies with skip, rework and cycle semantics

**Vendor evidence:** IBM documents predecessor/finish-to-start dependencies; an older Maximo support example shows a conditional omitted task can leave a later task without its intended predecessor. [Task dependencies, Real Estate and Facilities](https://www.ibm.com/docs/en/masv-and-l/maximo-ref/cd?topic=dependencies-task-record), [Job plan condition gap, Maximo 7.5](https://www.ibm.com/support/pages/node/216871).

**Proposed contract and failure case:** inspection may start after both alignment and lubrication are verified. A → B → A is rejected. Skipping lubrication needs a decision about whether the inspection remains eligible; deleting the edge is not that decision. If alignment is reopened after inspection started, mark the downstream job for review rather than silently leaving a green dependency indicator. A sequence number alone establishes neither dependency nor authorization.

**One-day cut:** display explicit predecessor links as advisory blockers. **Defer:** enforced dependency graph, critical-path scheduling and automatic downstream transitions.

### 16. Production access window separate from technician schedule

**Vendor evidence:** Maximo distinguishes maintenance availability from operational schedules. Its example intersects specialized crew availability with times the asset is not operating. [Asset and location availability](https://www.ibm.com/docs/en/masv-and-l/maximo-manage/cd?topic=schedules-asset-location-availability).

**Proposed contract and failure case:** the electrician is free 13:00–16:00, but the furnace is released only 14:00–15:00; a two-hour job does not fit. Store estimated duration and the confirmed plant access window separately from due date. If production withdraws the window, keep the job and explain that the schedule needs review. Do not manufacture outage timestamps from planned windows or treat a reservation of time as factory permission to begin work.

**One-day cut:** explicit window field and conflict warning. **Defer:** automatic rescheduling, optimization and live production-calendar integration.

### 17. Technician capacity, skill and absence-aware assignment

**Vendor evidence:** Limble supports working schedules and one-time availability exceptions, and distinguishes scheduled dates from task due dates. UpKeep documents skill/responsibility categories for people and teams. [Limble resource planning](https://help.limblecmms.com/en/articles/12082843-how-to-use-resource-planning), [UpKeep people categories](https://help.onupkeep.com/en/articles/1746935-how-to-add-edit-or-remove-users).

**Proposed contract and failure case:** three four-hour jobs assigned to an eight-hour technician show overload. Sick leave reduces capacity without rewriting the original shift. A job needing an electrical specialist should not become eligible merely because any Worker is idle. Skill tags are descriptive until the factory defines qualification review, expiry and authorization rules. Two locations must not each spend the same eight hours independently.

**One-day cut:** current availability note, estimated effort and manager-confirmed skill match. **Defer:** workforce calendar, cross-location capacity, qualification enforcement and optimized dispatch.

### 18. Contractor reference versus authenticated external worker

**Vendor evidence:** UpKeep's generic role guide says assigned vendor records cannot act on work orders. Its separate Provider Portal gives invited providers portal credentials and job collaboration capabilities. These are different workflows. [Role guide](https://help.onupkeep.com/en/articles/108077-upkeep-s-user-types-roles-and-responsibilities-overview), [Provider Portal](https://help.onupkeep.com/en/articles/12325916-using-the-provider-portal-in-upkeep).

**Proposed contract and failure case:** “ABC Drives” on a job is a business reference, not a login identity. Keep a real internal sponsor responsible for evidence/review. If external access is later built, scope it to specifically shared jobs; revocation must apply to attachments and exports too. Recording a contractor report must distinguish who performed the work from who entered it. A vendor's submitted completion must still await factory review.

**One-day cut:** vendor reference, service report attachment and internal sponsor. **Defer:** portal credentials, invitations, external uploads and messaging.

## Calibration, learning and controlled instructions

### 19. Calibration as-found and as-left readings

**Vendor evidence:** IBM calibration work orders copy approved data sheets and record readings before adjustment (as-found) and after adjustment (as-left). The guide requires these values before closure. [Work order tracking in calibration](https://www.ibm.com/docs/en/masv-and-l/maximo-manage/cd?topic=orders-work-order-tracking-in-calibration).

**Proposed contract and failure case:** a pressure gauge reads 108 at a reference 100 before adjustment and 100 afterward. Preserve the failed initial result; a final Pass does not mean the gauge was accurate during previous production. Store units, reference value, tolerance basis, actual reading and sheet revision. A tolerance of 1% of full scale differs from 1% of reading. Failed as-found results prompt a separate factory impact review.

**One-day cut:** attach the calibration certificate and distinct before/after values. **Defer:** tolerance calculations and a dedicated calibration workflow until measurement rules are specified.

### 20. Reference-standard usage and reverse traceability

**Vendor evidence:** IBM documents identifying which test standard calibrated an instrument and reverse lookup of instruments calibrated with a particular standard. [Calibration assets and standards](https://www.ibm.com/docs/en/masv-and-l/maximo-manage/cd?topic=administering-calibration-assets-standards).

**Proposed contract and failure case:** reference standard S9 later fails its own test. Find the gauge jobs that actually used S9 during the questioned period. A link to the model of calibrator cannot answer this; record the physical standard identity, use time and certificate/due state at use. Later updating S9's certificate must not rewrite that historical snapshot. An impact list is for factory assessment, not automatic invalidation or automatic approval of every linked instrument.

**One-day cut:** standard serial and certificate reference on the job. **Defer:** completeness claims, reverse-impact engine and automatic overdue-tool enforcement.

### 21. Repeat-failure investigation distinct from closing a repair

**Vendor evidence:** MaintainX supports structured root-cause categories/collections and reports linked to work orders; incident period and repair time are separate report inputs. [Root cause analysis](https://help.getmaintainx.com/about-root-cause-analysis), [Creating a report](https://help.getmaintainx.com/create-a-root-cause-analysis-report).

**Proposed contract and failure case:** the same pump seal fails on three different dates after verified repairs. These are three incidents connected to one investigation, not duplicates to suppress or merge. Record observed symptom, proposed cause, supporting evidence, confidence/review state and corrective action owner. Replacing the seal closes repair work; changing suction conditions is a separate improvement action with later effectiveness review. “Cause unknown” is more accurate than forcing the technician to guess a cause to finish.

**One-day cut:** related prior jobs, structured symptom and a manager-reviewed cause/action note. **Defer:** automated diagnosis, statistical recurrence alerts and causal claims derived from text similarity.

### 22. SOP draft, published revision and change applicability

**Vendor evidence:** MaintainX draft procedures cannot be attached to work orders; procedure history records additions/edits/removals. IBM job plans become editable job-specific work plans without altering the source plan. [Procedure drafts](https://help.getmaintainx.com/about-procedures), [Version history](https://help.getmaintainx.com/edit-a-procedure), [Job plans](https://www.ibm.com/docs/en/masv-and-l/maximo-manage/cd?topic=module-job-plans).

**Proposed contract and failure case:** the lubrication SOP changes grease type while a job is in progress. Show that revision 3 is being executed and revision 4 is available; a designated owner decides whether this job continues, restarts or receives an addendum. Updating the library must not silently replace signed-off steps. Record who published the revision, its effective date and affected asset models. This extends the earlier historical-inspection snapshot proposal into instruction rollout/change control.

**One-day cut:** explicit document revision/reference with current-job snapshot. **Defer:** approval builder, multi-document dependency rollout and automatic migration of active work.

### 23. Inspection/5S route with per-stop accountability

**Vendor evidence:** IBM routes contain asset/location stops and can generate child work orders, task work orders or one multi-stop work order; individual stops can have their own job plan. [Routes](https://www.ibm.com/docs/en/masv-and-l/maximo-manage/cd?topic=module-routes), [Applying routes](https://www.ibm.com/docs/en/masv-and-l/maximo-manage/cd?topic=reporting-applying-routes-work-orders).

**Proposed contract and failure case:** an operator checks ten lubrication points and three housekeeping areas but cannot access stop 7. “Route complete” must not fabricate a Pass for stop 7. Each stop has its own asset/location, result, time and skipped reason. A spill at a shared aisle belongs to that location rather than the last machine inspected. Changing tomorrow's walk order does not reorder today's evidence. The 5S use here is proposed, not a documented IBM scoring feature.

**One-day cut:** ordered checklist whose items explicitly name their stop and permit a reasoned skip. **Defer:** route designer, per-stop automatic jobs and scoring comparisons before consistent questions exist.

### 24. Component transfer and deliberate retirement

**Vendor evidence:** MaintainX documents asset movement history and a choice of whether completed work stays with a previous parent or moves with the component. IBM Maximo support describes moving retired assets to salvage locations. [Hierarchy/work history](https://help.getmaintainx.com/create-and-manage-asset-hierarchies), [Salvage retirement example](https://www.ibm.com/support/pages/maximo-support-desk-use-salvage-storeroom-retire-rotating-assets).

**Proposed contract and failure case:** compressor C8 moves from Line A to Line B. Retain its own repair history and the installation context of each old job, rather than attributing all earlier outages to Line B. Retirement is a business event with reason, date, replacement link and disposition reference, not merely hiding a catalog row. Before retirement, show open jobs, active plans and installed child components for explicit resolution. A retired spare must not remain available for issue; restoration needs a recorded review.

**One-day cut:** movement/retirement note and preserved historical links using existing archive behavior. **Defer:** transfers across stores/sites, financial disposal and automatic cascading retirement.

## What to actually add during the remaining day

These are alternatives after the already-prioritized reliability and connected repair workflow, not 24 extra tasks:

| Candidate | Small honest slice | Demonstrable factory question | Stop before |
| --- | --- | --- | --- |
| Criticality | Level + reason + review owner | Why does this machine matter to production? | Risk-score formulas and automatic urgency |
| Asset parts / where-used | Reviewed asset–part association, fitment note, reverse list | Which seal fits this press; which presses use this seal? | BOM revision engine or inferred compatibility |
| Repeat failure | Link three resolved incidents to one investigation with action owner | Why does this seal keep failing after repair? | AI root-cause or predictive claims |
| SOP reference | Published document revision pinned on the job | Which instruction did this technician actually use? | Full approval/change-management system |
| Shutdown grouping | Read-only package with child owners/status | What is still preventing the line handback? | Cascading parent completion or dependency enforcement |

The cleanest extra demo is a **repeat-failure review**: open the press → view its component and correct spare → show two earlier resolved failures → create a reviewed investigation → assign one improvement action. This adds learning after repair without redoing the first round's inspection-to-repair story. Use fictional examples visibly labeled as such. An investigation record is a record of a factory decision and supporting evidence, not a proven causal diagnosis.

## Research boundaries

The cited pages document specific products and editions. The dependency record page is Maximo Real Estate and Facilities; the condition-gap support example is Maximo 7.5; receiving inspection is 7.6.1; invoice matching is an Oracle connector page. Their domain distinctions inform proposed ShiftFix requirements without asserting current Maximo Manage behavior everywhere. IBM community posts were not used as evidence because being hosted on a vendor domain alone does not establish first-party authorship. Public availability does not demonstrate behavior under a particular vendor account configuration.

Each source is paraphrased briefly, below 200 words per page across this note. No pricing comparisons, vendor absence claims, legal compliance claims, account writes, AWS changes or deployments were made. The only file authored in this research round is this note.

Continued review on 2026-11-15: the current Manage item-kit page returned 403 to the reviewer; the linked first-party 7.6.1 documentation/search excerpt supports the kit accounting distinction and exclusions for that edition. UpKeep provider pages also differ in access mechanics across dated guides; the September 2026 portal guide requires authenticated setup, while an older sharing guide describes name/email entry without login. Do not copy either as a universal authentication guarantee. ShiftFix should define and verify its own scoped contractor access contract before implementing a portal.
