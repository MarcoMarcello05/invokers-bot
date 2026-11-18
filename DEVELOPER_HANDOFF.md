# DEVELOPER HANDOFF

## QUEST-LIVE-001 — structured quest state foundation

Status: BEREIT ZUR ENTWICKLUNG

User is currently mobile, so this package must be fully offline/read-only and require no real-client interaction.

Arena remains paused at the accepted live-integration boundary. Do not modify Arena behavior in this package.

## Goal

Implement the first real Quest domain slice from the already-mapped PlayerQuestsModel.

The package should make Quest state available through AccountState and expose safe, semantic read-only facts for later planning.

This package does NOT click, claim, navigate, or infer unknown quest objectives.

## Verified schema source

Use `QUESTS_MEMORYPACK_MAP_0.62.1621.md` as the binary source of truth.

PlayerQuestsModel:
- exactly 6 current members
- slot 0 LastQuestId int32
- slot 1 ActiveQuestsById
- slot 2 CompletedPrototypeIds List<int>
- slot 3 PeriodicGroups
- slot 4 AchievementGroups
- slot 5 TotalCompletedQuests int32

IQuestState union:
- tag 1 QuestStatePeriodic
- tag 2 QuestStateAchievement
- tag 3 QuestStateBook

Current quest-state member count:
- 51
- verified nonzero slots: 0,1,2,3,5,50
- slot0 QuestId int32
- slot1 PrototypeId int32
- slot2 StateId int32
- slot3 TimeStarted DateTime
- slot5 Progress int32
- slot50 subtype-specific enum/page
- all other current slots reserved/zero-length

QuestStateId:
- 0 Unknown
- 1 New
- 2 InProgress
- 3 Completed

Periodic subtype slot50:
- QuestPeriodicGroup

Achievement subtype slot50:
- QuestAchievementGroup

Book subtype slot50:
- Page

Enforce:
- dictionary key == QuestId for every active quest
- unknown union tags are explicit unsupported values/errors, never guessed
- malformed lengths/counts rejected
- reserved fields not semantically interpreted

## A. Parser

Create a strict read-only parser, naming may follow project conventions, e.g.:
- `quests_model.py`

Suggested immutable models:

`QuestKind`
- PERIODIC
- ACHIEVEMENT
- BOOK

`QuestStateId`
- UNKNOWN=0
- NEW=1
- IN_PROGRESS=2
- COMPLETED=3

`QuestState`
- quest_id
- prototype_id
- state_id
- time_started_utc
- progress
- kind
- group_or_page
- source union tag

`PeriodicWindow`
- group
- start_time_utc
- finish_time_utc nullable

`AchievementProgress`
- group_id
- current_level
- progress

`PlayerQuestsState`
- version
- updated_at_utc
- last_quest_id
- active_by_id immutable mapping
- completed_prototype_ids immutable tuple/frozenset
- periodic_groups immutable mapping
- achievement_groups immutable mapping
- total_completed_quests

Preserve numeric IDs as canonical values. Enums may wrap known values but parser must not invent labels for unknown future numeric values unless existing verified schema explicitly supports them.

## B. AccountState integration

Add `PlayerQuestsModel.dat` as source name `quests` to AccountObserver.

Requirements:
- same read-only before/after stat guard as existing sources
- same digest/version/freshness semantics
- `AccountState.quests` convenience property
- source-scoped invalidation support automatically includes quests
- no unrelated Arena/Hero/Relic behavior changes

Update type unions cleanly.

## C. Quest semantic adapter

Add a pure/domain-level quest view, separate from binary parsing.

At minimum expose:

`QuestSummary`
- source digest/version/observed_at
- total active
- total completed-state active entries
- periodic count
- achievement count
- book/progress count
- completed prototype count
- total_completed_quests

`ClaimableQuest`
- quest_id
- prototype_id
- kind
- state_id == COMPLETED
- group_or_page
- time_started
- periodic finish time if directly joinable
- source provenance

Important:
A quest in ActiveQuestsById with StateId COMPLETED is only a **claim candidate**.
Do not assert reward details or UI claimability until live/static-definition evidence exists.

Provide deterministic queries:
- all_completed_candidates()
- periodic_candidates(group)
- active_periodic_windows()
- summary()

## D. Periodic windows

Parse the four observed periodic groups generically:
- Daily
- Weekly
- Monthly
- Clan

Do not hardcode that only four can ever exist.

Nullable FinishTime must be preserved exactly.

The planner may later use finish time for urgency, but this package only exposes the data.

## E. Static definition boundary

Do NOT attempt to infer objective/reward semantics from PrototypeId.

Create an explicit boundary/interface or TODO contract for a later `QuestDefinitionCatalog` sourced from verified static game data.

Reason:
Current official game material confirms quest objectives/rewards can change between updates, including 0.62 quest reward changes and hidden Clan Quest placement. Static definitions must therefore be build/version aware, not baked into snapshot parser code.

No web data belongs in runtime parser constants.

## F. Pure goal facts, no scheduler expansion

Produce only safe facts for later goals:
- `quests.has_completed_candidates`
- completed candidate count
- nearest known periodic finish time
- groups with completed candidates
- source freshness/provenance

Do NOT build full ProgressQuest routing yet.
Do NOT add new utility-scoring architecture.
Do NOT implement claim clicks.

## G. Tests

Use synthetic binary fixtures following the verified MemoryPack profile.

At minimum test:

1. parse 6-slot PlayerQuestsModel
2. periodic union tag 1
3. achievement tag 2
4. book tag 3
5. dictionary key == QuestId success
6. dictionary key mismatch rejected
7. malformed member count rejected
8. malformed scalar width rejected
9. reserved/extra future slots safely handled only according to existing VersionTolerant reader contract
10. unknown union tag explicitly rejected/unsupported
11. Completed StateId=3 becomes claim candidate
12. New/InProgress do not become claim candidates
13. CompletedPrototypeIds parsed exactly
14. periodic nullable FinishTime
15. achievement current_level/progress
16. AccountObserver reads `quests`
17. unchanged quest file retains model/digest semantics
18. changed quest file marks source changed
19. invalid/corrupt quest source does not destroy last-good diagnostic model
20. quest invalidation is source-scoped
21. summary/group queries deterministic
22. no input/action dependencies imported by quest parser/domain adapter
23. entire existing test suite remains green

## H. Documentation

Update:
- MASTER_STATUS.md
- MASTER_CHECKLIST.md
- TEST_RESULTS.md
- ACCOUNTSTATE_SOURCE_MATRIX.md if necessary
- LIVE_ACCOUNTSTATE.md if necessary

Document clearly:
- parser/code CI validation is not live quest UI validation
- no static PrototypeId semantics yet
- no claim/navigation capability yet
- no raw user snapshot committed

## Constraints

- read-only
- no SendInput
- no screenshots/templates
- no OCR
- no claim action
- no purchase behavior
- no static quest guesses
- no raw PlayerQuestsModel.dat committed
- no Arena regressions
- Windows CI required

## Completion report

Report:
- commit SHA
- files changed
- parser model/schema decisions
- AccountState integration
- claim-candidate semantics
- test count
- Windows CI run/result
- remaining blockers for QUEST-LIVE-002
