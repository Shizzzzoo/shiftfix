# ShiftFix research index

The final-day research pack was prepared on2026-11-14. It does not deploy new features or modify factory data. Current live release remains immutable backend-v9.zip.

1. [Recommended24-hour build plan](2026-11-14-final-day-plan.md): implementation order, minimal feature contracts, scope cuts, demo and release gates.
2. [CMMS workflow comparison](2026-11-14-cmms-feature-research.md):21 workflows researched against primary MaintainX, UpKeep, Limble, Fiix and IBM documentation;49 proposed factory acceptance examples.
3. [Current-code/runtime audit](2026-11-14-code-and-runtime-audit.md): reproduced local gaps, inspected risks, live release evidence and source grounding.
4. [100-case acceptance matrix](2026-11-14-edgecase-matrix.csv): priorities and evidence status across access, work orders, evidence, inventory, purchasing, inspections, meters, PM, browser recovery and operations.
5. [Backend probe output](2026-11-14-edgecase-probe-results.json) and [UI race output](2026-11-14-ui-race-probe.json): isolated evidence, not claims of production incidents.

The baseline regression suite remains92 passing tests. Reproduced probe scenarios expose additional coverage gaps; the probe scripts intentionally record current behavior and are separate from acceptance tests. Features/fixes in the plan remain proposed until implemented and verified.
