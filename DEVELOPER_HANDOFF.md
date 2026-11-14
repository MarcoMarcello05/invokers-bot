# DEVELOPER HANDOFF

## Current package: DATA-003 Phase 4 — PlayerRelicsModel + PlayerRelic

Status: BEREIT ZUR ENTWICKLUNG

Read first:
- PROJECT_WORKFLOW.md
- MASTER_CHECKLIST.md
- MASTER_STATUS.md
- TEST_RESULTS.md
- SNAPSHOT_SERIALIZATION_0.62.1621.md
- RELICS_MEMORYPACK_MAP_0.62.1621.md
- HEROES_MEMORYPACK_MAP_0.62.1621.md
- current shared parser code under src/invokers_bot

## Context

DATA-003 phases 1-3 are complete and CI-verified.

Phase 3:
- commit: `09a3c33638abbede74ad1063e26baf3b02a87b54`
- Actions run: `43641550108`
- result: `129 passed, 1 warning`

Reuse the existing:
- envelope parser
- VersionTolerant member-span reader
- nested-object reader

Do not duplicate these layers.

## Goal

Implement strictly read-only parsing for:

- PlayerRelicsModel
- RelicsById
- PlayerRelic

Do NOT implement PlayerRelicBonus internals yet unless the exact schema is independently verified from current data/docs during this task.

## Verified PlayerRelicsModel

Current model is VersionTolerant with 3 slots:

0 LastId
1 RelicsById
2 Randoms

Current analyzed snapshot:
- LastId = 361
- RelicsById contains 180 PlayerRelic entries

## Verified PlayerRelic

Current PlayerRelic has 9 slots with no observed reserved gaps:

0 InventoryId
1 Slot
2 Rank
3 Rarity
4 Set
5 EquippedHeroId
6 Level
7 IsSeen
8 Bonuses

Types:

- InventoryId: int32
- Slot: RelicSlot / int32
- Rank: RelicRank / int32
- Rarity: RelicRarity / int32
- Set: RelicSet / int32
- EquippedHeroId: nullable int32
- Level: int32
- IsSeen: bool
- Bonuses: list of PlayerRelicBonus

## Required implementation

Expose immutable state objects with at minimum:

PlayerRelicsState:
- version
- updated_at_utc
- last_id
- relics_by_id
- opaque/randoms raw data if not decoded

RelicState:
- inventory_id
- slot
- rank
- rarity
- set
- equipped_hero_id
- level
- is_seen
- bonuses_raw or safely preserved bonus entries if exact bonus schema is not yet verified

## Cross-model integrity

Where practical, add optional validation helpers/tests that can later join:

PlayerHero.RelicIdBySlot -> PlayerRelic.InventoryId

Do not create hard parser dependency on heroes_model.py if that would couple parsers unnecessarily.

Parser layer should remain model-focused; cross-model joins belong in AccountState/adapters later.

## Validation

Strictly validate:
- correct aggregate union/model
- root member count
- RelicsById dictionary count
- duplicate relic dictionary keys
- Relic.InventoryId equals dictionary key
- exact scalar widths
- bool values only 0/1
- nullable int32 layout for EquippedHeroId
- member spans stay in bounds
- malformed/truncated nested objects rejected
- trailing bytes rejected inside known structures
- additional future root/relic slots may be skipped only if the chosen parser policy explicitly allows additive VersionTolerant members safely
- unknown enum numeric values preserved, not rejected

For Bonuses:
- if exact PlayerRelicBonus binary schema is not confirmed, preserve slot 8 safely as opaque bytes or a bounded raw list representation
- do not guess bonus member order

## Tests

Add synthetic tests for at minimum:

1. empty relic dictionary
2. one relic
3. multiple relics
4. inventory-id/dictionary-key agreement
5. mismatch rejection
6. duplicate dictionary key rejection
7. Slot/Rank/Rarity/Set/Level
8. EquippedHeroId null
9. EquippedHeroId value
10. IsSeen false/true
11. invalid bool
12. empty bonuses
13. opaque/non-empty bonuses preserved safely if exact schema deferred
14. malformed root member count
15. malformed PlayerRelic member count
16. truncated delta table
17. out-of-bounds member
18. wrong scalar width
19. malformed nullable int32
20. trailing bytes
21. wrong aggregate union tag
22. read-only file behavior
23. additive future slots if supported

If a current real snapshot is locally available, validate it without committing private data.

## Out of scope

Do not implement yet:
- PlayerAccessory
- PlayerAnima
- Quests
- Arena
- Battle
- Clan
- Events
- Shop
- gear optimization logic
- sell/crush/equip actions
- any mutation/write API

## Completion

1. run full pytest suite
2. push to main
3. verify remote HEAD
4. verify Windows GitHub Actions
5. update TEST_RESULTS.md and MASTER_STATUS.md
6. report:
   - commit SHA
   - branch
   - push result
   - pytest result/count
   - GitHub Actions run ID/result
   - changed files
   - unresolved assumptions
