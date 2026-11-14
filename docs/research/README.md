# ShiftFix research index

The final-day research pack was prepared on2026-11-14. It does not deploy new features or modify factory data. Current live release remains immutable backend-v9.zip.

1. [Recommended24-hour build plan](2026-11-14-final-day-plan.md): implementation order, minimal feature contracts, scope cuts, demo and release gates.
2. [CMMS workflow comparison](2026-11-14-cmms-feature-research.md):21 workflows researched against primary MaintainX, UpKeep, Limble, Fiix and IBM documentation;49 proposed factory acceptance examples.
3. [Current-code/runtime audit](2026-11-14-code-and-runtime-audit.md): reproduced local gaps, inspected risks, live release evidence and source grounding.
4. [100-case acceptance matrix](2026-11-14-edgecase-matrix.csv): priorities and evidence status across access, work orders, evidence, inventory, purchasing, inspections, meters, PM, browser recovery and operations.
5. [Backend probe output](2026-11-14-edgecase-probe-results.json) and [UI race output](2026-11-14-ui-race-probe.json): isolated evidence, not claims of production incidents.

The baseline regression suite remains92 passing tests. Reproduced probe scenarios expose additional coverage gaps; the probe scripts intentionally record current behavior and are separate from acceptance tests. Features/fixes in the plan remain proposed until implemented and verified.

## Deeper factory research, completed 2026-11-15

- [Round2 findings and design implications](2026-11-15-round2-findings.md): six new isolated probe observations, readiness/passport concepts, stronger audit contract and updated scope cut.
- [24 factory workflow concepts](2026-11-14-factory-workflows-round2.md):equipment/fitment, criticality, warranties, serial/lot/kit stock, receipts, shutdowns, contractors, calibration, SOPs, routes and retirement. Each has source evidence, a concrete failure case and a small/deferred boundary.
- [60 additional acceptance cases](2026-11-15-additional-edgecases.csv), numbered EC-101 through EC-160. Together with the original CSV these give 160 acceptance contracts, not 160 current bugs.
- [Second-pass raw observations](2026-11-14-round2-probe-results.json), reproduced only in moto through scripts/research-round2-probes.py.

The research does not implement or deploy these features/fixes. Last verified application release remains v9.
