# QUESTS MEMORYPACK MAP — 0.62.1621

Date: 2026-11-14

Sources:
- current IL2CPP v39 dump
- fresh PlayerQuestsModel.dat
- MemoryPack union/runtime behavior

Raw user/account files are not committed.

## PlayerQuestsModel

Current payload is VersionTolerant with exactly 6 members.

| Slot | Field | Current bytes |
|---:|---|---:|
| 0 | LastQuestId | 4 |
| 1 | ActiveQuestsById | 44459 |
| 2 | CompletedPrototypeIds | 480 |
| 3 | PeriodicGroups | 128 |
| 4 | AchievementGroups | 7369 |
| 5 | TotalCompletedQuests | 4 |

Observed snapshot facts:
- LastQuestId = 683
- ActiveQuestsById count = 523
- CompletedPrototypeIds count = 119
- PeriodicGroups count = 4
- AchievementGroups count = 491
- TotalCompletedQuests = 116

## IQuestState union

IL2CPP confirms:

- tag 1 = QuestStatePeriodic
- tag 2 = QuestStateAchievement
- tag 3 = QuestStateBook

Every one of the 523 observed active quest states uses:
- a one-byte MemoryPack union tag
- VersionTolerant member count = 51
- identical nonzero slot pattern

Union distribution in current snapshot:
- Periodic: 31
- Achievement: 488
- Book: 4

MemoryPack union reference:
https://github.com/Cysharp/MemoryPack

## Quest-state slot map

All 523 observed active quest values have nonzero slots:

- 0
- 1
- 2
- 3
- 5
- 50

All other slots are zero-length/reserved in the current snapshot.

Verified mapping:

| Slot | Field | Type |
|---:|---|---|
| 0 | QuestId | int32 |
| 1 | PrototypeId | int32 |
| 2 | StateId | QuestStateId / int32 |
| 3 | TimeStarted | DateTime / 8 bytes |
| 4 | RESERVED / removed | zero length |
| 5 | Progress | int32 |
| 6..49 | RESERVED / removed | zero length |
| 50 | derived field | int32 enum/page |

Derived slot 50:
- QuestStatePeriodic -> QuestPeriodicGroup
- QuestStateAchievement -> QuestAchievementGroup
- QuestStateBook -> Page

Strong cross-check:
- QuestId in slot 0 equals the ActiveQuestsById dictionary key for every one of the 523 observed entries.

## QuestStateId

Current enum:
- 0 Unknown
- 1 New
- 2 InProgress
- 3 Completed

Current active-state distribution:
- New: 518
- Completed: 5

The model name 'ActiveQuestsById' therefore does not mean every contained quest is unfinished; completed-but-not-yet-processed/claimed state can still exist in the active dictionary.

## CompletedPrototypeIds

Slot 2 is a normal List<int>:
- count = 119
- payload length = 4 + 119*4 = 480 bytes

This provides a cheap structured signal for already completed quest prototypes.

## PeriodicGroups

QuestPeriodicGroup enum:
- 1 Daily
- 2 Weekly
- 3 Monthly
- 4 Advance
- 5 Clan

Current snapshot contains four group entries:
- Daily
- Weekly
- Monthly
- Clan

Each PlayerPeriodicGroup is VersionTolerant with two fields:
- slot 0 StartTime: DateTime, 8 bytes
- slot 1 FinishTime: Nullable<DateTime>, 16 bytes

This can provide direct structured timing for quest resets/windows.

## AchievementGroups

Current snapshot contains 491 PlayerAchievementGroup entries.

Each group object has two fields:
- slot 0 CurrentLevel: int32
- slot 1 Progress: int32

The QuestAchievementGroup enum is extensive and includes account, summon, collection, gear, battle, towers/spires, Arena and Clan Boss objectives.

Examples present in the current schema include:
- WinArenaBattle
- CompleteTowerFire/Earth/Wind/Water/Light/Dark
- CompleteClanBoss1Boss
- DealDamageToClanBoss2Normal/Hard/Brutal/Nightmare
- Arena Hall upgrade achievements

This is highly valuable for task planning because achievement progress can be read without OCR.

## Bot architecture consequence

The quest subsystem can eventually be driven primarily from structured local state:

1. identify all quest states
2. distinguish periodic / achievement / progress-book quests
3. detect completed states
4. read current progress
5. know periodic reset windows
6. map prototype/group IDs to static quest definitions
7. use vision only to navigate to claim/GO buttons and verify UI transitions

## Parser design

Recommended later DATA-003 quest phase:

- parse PlayerQuestsModel 6-slot envelope
- parse CompletedPrototypeIds
- parse PeriodicGroups
- parse AchievementGroups
- parse ActiveQuestsById using IQuestState union tags
- preserve unknown future union tags as explicit unsupported data rather than guessing
- enforce QuestId == dictionary key
- decode only verified quest-state slots
- skip reserved slots by MemoryPack delta

Static quest prototype/config lookup is a separate layer and should not be mixed into the low-level binary parser.

## Development sequencing

Do not interrupt the current PlayerModel/Resources Phase 2 implementation.

Quest parser work can be issued after the Hero parser or in a later structured-data package once dependencies and static-data lookup are planned.
