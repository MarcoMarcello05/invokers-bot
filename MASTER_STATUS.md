# MASTER STATUS

Date: 2026-11-14

## Product target

**Universal fully autonomous Invokers autopilot.**

The canonical project target list is now:
`MASTER_CHECKLIST.md`

All future planning, implementation and status updates must reference that checklist by stable feature ID. New systems discovered through research must be appended there instead of living only in chat or scattered documentation.

## State

- ABGESCHLOSSEN: Recovery branch `archive/pre-analyser-2.0-restart-2026-11-14`.
- ABGESCHLOSSEN: Clean active-tree reset.
- ABGESCHLOSSEN: Windows live-input engine.
- ABGESCHLOSSEN: Client-area + DPI handling.
- ABGESCHLOSSEN: DXcam + MSS fallback.
- ABGESCHLOSSEN: OpenCV state and target matching.
- ABGESCHLOSSEN: Stable-state gate, UNKNOWN=no-input, F12 abort.
- IN ENTWICKLUNG: Universal Goal -> Task -> State -> Action architecture.
- IN ENTWICKLUNG: Central scheduler and reusable skill registry.
- ABGESCHLOSSEN: Permanent full-project checklist established in `MASTER_CHECKLIST.md`.
- OFFEN: Fresh global UI/state inventory.
- OFFEN: Full account/game automation implementation across checklist domains.
- TEST AUSSTEHEND: Real Windows dry/live validation.

## Working rule

Never mark a major capability as complete only because code exists. A checklist item reaches `ABGESCHLOSSEN` only when its acceptance behavior has been verified.

## Immediate next objective

Work directly from `MASTER_CHECKLIST.md`, starting with the universal core/data/navigation foundations required by many later systems.


## Current data-analysis package

- IN ANALYSE: DATA-002 fresh local data inventory.
- IN ANALYSE: DATA-003 structured snapshot-reader research.
- Fresh snapshot findings are documented in `DATA_SNAPSHOT_2026-11-14.md`.
- Project role split and research-first rule are documented in `PROJECT_WORKFLOW.md`.
- No new production coding task is issued until the model/schema analysis is ready for a precise DEVELOPER prompt.


## IL2CPP schema milestone

- ABGESCHLOSSEN: current Windows IL2CPP metadata identified as version 39.
- ABGESCHLOSSEN: primary player/account aggregate model field inventory extracted.
- ABGESCHLOSSEN: ResourceTypeId structured resource model confirmed.
- IN ANALYSE: snapshot serialization/formatter contract needed before parser handoff.
- Schema findings: `IL2CPP_SCHEMA_0.62.1621.md`.


## Snapshot serialization milestone

- ABGESCHLOSSEN: IAggregateSnapshotDTO MemoryPack union tags mapped for all 12 aggregate files.
- ABGESCHLOSSEN: generic 3-member VersionTolerant envelope verified byte-for-byte across all supplied snapshots.
- BEREIT ZUR ENTWICKLUNG: read-only aggregate-envelope parser (DATA-003 phase 1).
- IN ANALYSE: exact inner-model MemoryPackOrder/reserved-slot maps for AccountState decoding.
- Details: `SNAPSHOT_SERIALIZATION_0.62.1621.md`.

## DATA-003 Phase 1 implementation

- TEST AUSSTEHEND: strict read-only outer envelope parser and synthetic regression tests implemented; inner models remain opaque.
- Windows CI uses existing pytest discovery. No live input or snapshot writes.
- Full DATA-003 remains open pending inner-model research and implementation.
