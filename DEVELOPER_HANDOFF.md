# DEVELOPER HANDOFF

## Current package: DATA-003 Phase 2 — PlayerModel + Resources read-only parser

Status: BEREIT ZUR ENTWICKLUNG

Read first:
- PROJECT_WORKFLOW.md
- MASTER_CHECKLIST.md
- MASTER_STATUS.md
- IL2CPP_SCHEMA_0.62.1621.md
- SNAPSHOT_SERIALIZATION_0.62.1621.md
- PLAYERMODEL_RESOURCES_MAP_0.62.1621.md
- TEST_RESULTS.md

## Context

DATA-003 Phase 1 is complete and CI-verified.

Verified implementation commit:
`ed11fb1f06373c72f394b6d06e35be7f039a70c1`

Verified GitHub Actions run:
`43602310052`

The existing outer envelope parser must be reused rather than duplicated.

## Goal

Implement a strictly read-only Phase 2 parser for selected `PlayerModel` fields and structured resources.

Do not attempt full nested decoding of Tutorial, LiveOps, DailyLoginPrograms, SummonResults, VipStatus or other complex members yet.

## Verified PlayerModel layout

The current PlayerModel is a MemoryPack VersionTolerant object with 53 serialized slots.

Reserved/removed zero-length slots:
- 7
- 12
- 13
- 14

The complete verified slot map is in:
`PLAYERMODEL_RESOURCES_MAP_0.62.1621.md`

## Required decoded fields

Decode at minimum:

- slot 4: Level
- slot 5: Experience
- slot 6: TotalExperience
- slot 8: EnergySyncTime
- slot 9: Resources
- slot 10: ResourcesGained
- slot 11: ResourcesSpent
- slot 33: TodayTotalPlayedMinutes
- slot 34: ArenaTokenSyncTime
- slot 43: DaysPlayed
- slot 51: SupportRevision
- slot 52: SupportLastReadRevision

All other slots should be preserved as spans or safely skipped according to their declared VersionTolerant member lengths.

## Resources format

`Resources` is a VersionTolerant MemoryPack object with one serialized member:

`SortedDictionary<ResourceTypeId, int> RawValues`

Verified binary structure:

- object member count = 1
- one MemoryPack VarInt member-length delta
- Int32 collection count
- repeated:
  - ResourceTypeId as Int32
  - value as Int32

Implement a stable ResourceTypeId mapping from the current IL2CPP schema where identifiers have been verified.

Unknown future resource IDs must not crash parsing. Preserve numeric ID even when no friendly enum/name is known.

## Parser behavior

Prefer an explicit immutable result model, for example:

- PlayerModelState
- ResourceEntry or mapping keyed by numeric ResourceTypeId

Expose:
- current resources
- lifetime gained resources
- lifetime spent resources
- decoded scalar account fields above

The parser must consume the `data` payload from the existing Phase 1 AggregateSnapshot parser.

## Validation

Strictly validate:
- PlayerModel member count is sufficient for every accessed slot
- member-delta table is not truncated
- negative lengths are rejected
- each computed member span remains within the PlayerModel payload
- reserved zero-length slots are accepted
- Resources object member structure is valid
- dictionary length cannot exceed remaining bytes
- duplicate ResourceTypeId keys are rejected or handled explicitly according to SortedDictionary semantics
- trailing bytes inside a known Resources member are rejected
- unknown PlayerModel slots are skipped only by their declared length, never guessed offsets

## Tests

Add synthetic tests for at minimum:

1. valid minimal 53-slot PlayerModel
2. known scalar decoding
3. all four reserved zero-length slots
4. Resources with zero entries
5. Resources with multiple entries
6. ResourcesGained and ResourcesSpent
7. unknown ResourceTypeId preserved numerically
8. malformed PlayerModel member count
9. truncated member-delta table
10. negative member length
11. member span out of bounds
12. malformed Resources member count
13. truncated dictionary count
14. dictionary count greater than available pairs
15. duplicate ResourceTypeId
16. trailing bytes inside Resources member

If local access to the real user snapshot exists, verify the parser against it without committing the raw file.

Expected real-snapshot consistency checks documented by ANALYSER include examples such as:

- Gold: gained - spent = current
- Energy: gained - spent = current
- Memorium: gained - spent = current
- Arena_Token: gained - spent = current

Do not hardcode these user values into production code.

## Safety

- read-only only
- no write APIs
- no game process access
- no LocalLow mutations
- no packet/network manipulation
- no private snapshot data committed

## Out of scope

Do NOT implement:
- PlayerHeroesModel
- PlayerHero
- PlayerRelicsModel
- PlayerArenaModel
- PlayerQuestsModel
- nested LiveOps/Tutorial/VIP parsing
- any game-state modification

## Completion requirements

1. Run full test suite.
2. Ensure Windows GitHub Actions passes.
3. Update TEST_RESULTS.md.
4. Update MASTER_STATUS.md.
5. Commit to main.
6. Push to the existing GitHub repository.
7. Verify remote HEAD / pushed commit.
8. Report:
   - exact commit SHA
   - branch
   - push result
   - pytest command/result
   - GitHub Actions run/result
   - changed files
   - any schema assumptions still unresolved
