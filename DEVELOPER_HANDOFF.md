# DEVELOPER HANDOFF

## Current package: DATA-003 Phase 3 — PlayerHeroesModel + PlayerHero

Status: BEREIT ZUR ENTWICKLUNG

Read first:
- PROJECT_WORKFLOW.md
- MASTER_CHECKLIST.md
- MASTER_STATUS.md
- TEST_RESULTS.md
- SNAPSHOT_SERIALIZATION_0.62.1621.md
- HEROES_MEMORYPACK_MAP_0.62.1621.md
- RELICS_MEMORYPACK_MAP_0.62.1621.md
- PLAYERMODEL_RESOURCES_MAP_0.62.1621.md

## Context

Phase 1 and Phase 2 are complete and Windows-CI verified.

Phase 2 implementation:
`2a9f1d5b508a321dc7553ea2a899eeff43cc3612`

CI:
`43640238110` — SUCCESS — 89 passed, 1 warning.

Reuse:
- existing snapshot envelope parser
- existing generic VersionTolerant member-span reader

Do not duplicate those layers.

## Goal

Implement read-only parsing for:
- PlayerHeroesModel
- HeroesById
- PlayerHero
- core hero progression/safety/equipment references

No mutation APIs.

## Verified PlayerHeroesModel

10 slots:

0 LastId
1 HeroesById
2 LobbyHeroIds
3 SeenHeroConfigIds
4 ReceivedHeroesCount
5 StarterHeroId
6 FusedHeroesCountByOutputGdId
7 RemovableFuseMaterialGdIds
8 HeroRating
9 ReceivedChromaHeroConfigIds

Current analyzed snapshot contained 30 PlayerHero entries.

## Verified PlayerHero

22 VersionTolerant slots:

0 InventoryId
1 ConfigId
2 Rank
3 Level
4 Experience
5 TotalExperience
6 Locked
7 InStorage
8 Marker
9 RecentBattleTime
10 RESERVED
11 RelicIdBySlot
12 AccessoryIdBySlot
13 RESERVED
14 RESERVED
15 AwakeNodeIds
16 AwakeLevel
17 ChromaEnabled
18 Skin
19 RESERVED
20 RESERVED
21 SkillLevels

Reserved slots 10, 13, 14, 19, 20 must be skipped by declared length.

## Required output

Expose an immutable Hero state with at minimum:
- inventory_id
- config_id
- rank
- level
- experience
- total_experience
- locked
- in_storage
- marker
- recent_battle_time
- relic_id_by_slot
- accessory_id_by_slot
- awake_node_ids
- awake_level
- chroma_enabled
- skin
- skill_levels

PlayerHeroesModel result should expose:
- last_id
- heroes_by_id
- lobby_hero_ids
- seen_hero_config_ids
- starter_hero_id
- received hero counters where schema is verified

## Validation requirements

Strictly validate:
- root union/model is PlayerHeroesModel
- member counts and deltas
- dictionary/list lengths stay within slot span
- PlayerHero.InventoryId equals its HeroesById dictionary key
- duplicate dictionary keys rejected
- invalid bool bytes rejected
- known fixed-width scalar widths validated
- RelicIdBySlot dictionary keys/values decoded as int32
- AccessoryIdBySlot likewise
- UpgradeableSkill list entries are exact pairs of int32 values
- unknown future enum values remain numeric rather than crashing
- additional future PlayerHero slots may be skipped safely by declared length
- no trailing bytes inside known members

## Tests

Synthetic tests at minimum:
1. empty hero dictionary
2. one minimal valid hero
3. multiple heroes
4. inventory-id/dictionary-key agreement
5. mismatch rejection
6. rank/level/xp scalars
7. locked/in-storage booleans
8. recent-battle nullable DateTime
9. empty relic/accessory maps
10. 8 relic slot mappings
11. accessory mappings
12. awake nodes
13. awake level
14. chroma / skin
15. 6-skill list
16. 7-skill list
17. reserved slots ignored safely
18. malformed root count
19. malformed PlayerHero count
20. truncated delta tables
21. out-of-bounds members
22. duplicate dictionary keys
23. invalid bool
24. malformed skill list
25. trailing bytes
26. wrong aggregate union tag
27. read-only file behavior

If a current real snapshot is locally available, verify it without committing any private data.

## Optional cleanup

The current CI has one non-blocking pytest warning:
`tests/test_snapshot_envelope.py::test_tags` passes an `enumerate` directly to parametrize.

You may convert it to a tuple/list if convenient, but do not let this distract from Phase 3.

## Out of scope

Do not implement yet:
- full PlayerRelic parser
- PlayerAccessory parser
- PlayerAnima parser
- Quests
- Arena
- Battle
- Clan
- Events
- writing/manipulation

## Completion

1. run full pytest suite
2. push to main
3. verify Remote HEAD
4. verify Windows GitHub Actions
5. update TEST_RESULTS.md and MASTER_STATUS.md
6. report exact:
   - commit SHA
   - branch
   - push result
   - pytest result/count
   - GitHub Actions run ID/result
   - changed files
   - unresolved assumptions
