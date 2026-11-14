# PLAYERMODEL / RESOURCES MEMORYPACK MAP — 0.62.1621

Date: 2026-11-14

Sources:
- current IL2CPP v39 dump for Windows build 0.62.1621-0cc5
- fresh PlayerModel.dat snapshot
- Cysharp MemoryPack generator/runtime source

Raw user/account data is not committed.

## MemoryPack generator rule

For VersionTolerant objects MemoryPack pads missing explicit orders with blank members. The generator:
- takes the maximum member order,
- creates an array through that order,
- inserts empty members for missing orders,
- writes one serialized-length delta per slot.

Reference:
https://github.com/Cysharp/MemoryPack/blob/main/src/MemoryPack.Generator/MemoryPackGenerator.Emitter.cs

This explains why PlayerModel has 53 serialized slots while only 49 current backing fields are visible in the IL2CPP type.

## PlayerModel slot map

The current PlayerModel payload starts with object member count 53.

The current snapshot produces these exact serialized member lengths:

| Slot | Field | Bytes |
|---:|---|---:|
| 0 | PlayerId | 16 |
| 1 | Name | 13 |
| 2 | RegistrationDate | 8 |
| 3 | AppliedMigrations | 8 |
| 4 | Level | 4 |
| 5 | Experience | 4 |
| 6 | TotalExperience | 4 |
| 7 | RESERVED / removed member | 0 |
| 8 | EnergySyncTime | 8 |
| 9 | Resources | 400 |
| 10 | ResourcesGained | 400 |
| 11 | ResourcesSpent | 136 |
| 12 | RESERVED / removed member | 0 |
| 13 | RESERVED / removed member | 0 |
| 14 | RESERVED / removed member | 0 |
| 15 | LastActivityDate | 8 |
| 16 | Boosters | 62 |
| 17 | ConfigVersion | 17 |
| 18 | AbTest | 4 |
| 19 | Tutorial | 49 |
| 20 | Settings | 32 |
| 21 | IsCheater | 1 |
| 22 | LinkStatus | 4 |
| 23 | ClaimedPlayTimeRewards | 4 |
| 24 | ClaimedPlayerLevelRewards | 60 |
| 25 | DailyLoginPrograms | 249 |
| 26 | SummonResults | 394 |
| 27 | SummonBonusSystem | 26 |
| 28 | ClientNotificationsCheckpoint | 18 |
| 29 | BanInfo | 1 |
| 30 | LastActualizationTime | 8 |
| 31 | LastDeviceId | 40 |
| 32 | MultiBattleTokensRefreshTime | 8 |
| 33 | TodayTotalPlayedMinutes | 4 |
| 34 | ArenaTokenSyncTime | 8 |
| 35 | LiveOps | 2154 |
| 36 | SelectedAvatar | 15 |
| 37 | SelectedFrame | 6 |
| 38 | UnlockedCustomAvatarIds | 4 |
| 39 | UnlockedFrameIds | 20 |
| 40 | NameChangeCount | 4 |
| 41 | Capabilities | 5 |
| 42 | RelicSwapPassFinish | 8 |
| 43 | DaysPlayed | 4 |
| 44 | LastVirtualTimeResetTime | 8 |
| 45 | VipStatus | 91 |
| 46 | LastDeviceModel | 27 |
| 47 | LobbySelectedHero | 8 |
| 48 | LobbySelectedAnimaId | 8 |
| 49 | CreatorsProfile | 1 |
| 50 | Acquisition | 3 |
| 51 | SupportRevision | 8 |
| 52 | SupportLastReadRevision | 8 |

Evidence level: HIGH.

Why:
- the 53-slot header is read directly from the current snapshot;
- the four zero-length slots match MemoryPack's documented blank-member padding behavior;
- all remaining serialized lengths align with the current IL2CPP field types in declaration progression;
- the Resources slots are independently decoded and cross-validated below.

## Resources schema

IL2CPP:

`Resources`
- MemoryPackable(VersionTolerant)
- one serialized member: `SortedDictionary<ResourceTypeId,int> RawValues`

The current Resources payload is:

`[object count=1] [varint member length] [dictionary payload]`

The dictionary payload uses MemoryPack SortedDictionary formatting:
- Int32 collection count
- repeated key/value pairs

For this model both key and value are 32-bit:
- key = ResourceTypeId enum/int32
- value = int32

Reference:
https://github.com/Cysharp/MemoryPack/blob/main/src/MemoryPack.Core/Formatters/CollectionFormatters.cs

## Current snapshot structural proof

PlayerModel slot 9 (Resources):
- member payload bytes: 400
- Resources internal member delta: 396
- dictionary count: 49
- dictionary bytes = 4 + (49 * 8) = 396
- exact match

Slot 10 (ResourcesGained):
- same structure
- 49 entries
- exact 396-byte dictionary payload

Slot 11 (ResourcesSpent):
- outer member bytes: 136
- Resources internal member delta: 132
- dictionary count: 16
- dictionary bytes = 4 + (16 * 8) = 132
- exact match

## Arithmetic cross-validation

The decoded lifetime-gained and lifetime-spent dictionaries provide an independent consistency check.

Examples from the supplied current snapshot:

- Gold:
  gained 4,484,724
  spent 3,587,830
  current 896,894
  gained - spent = current

- Energy:
  gained 1,911
  spent 485
  current 1,426
  gained - spent = current

- Memorium:
  gained 15,977
  spent 8,679
  current 7,298
  gained - spent = current

- Arena_Token:
  gained 25
  spent 13
  current 12
  gained - spent = current

This confirms that slots 9, 10 and 11 are not merely plausible but semantically correct.

## Current structured resources observed

Examples:
- Gem
- Gold
- Energy
- Memorium
- Token_MultiBattle
- ClanBoss2Key
- Arena_Token
- Arena_Coin
- Arena medals
- XP potions
- summon Stars / Star fragments
- summon Orbs / Orb fragments
- Codexes
- Prisms
- ascension/awakening materials
- class/faction materials
- event currencies

The complete ResourceTypeId enum is recoverable from the current IL2CPP dump and should become a stable parser enum/map rather than OCR labels.

## Parser implication

DATA-003 Phase 2 can safely implement:

1. PlayerModel VersionTolerant slot table.
2. Scalar fields required for AccountState:
   - Level
   - Experience
   - TotalExperience
   - EnergySyncTime
   - TodayTotalPlayedMinutes
   - ArenaTokenSyncTime
   - DaysPlayed
   - SupportRevision
   - SupportLastReadRevision
3. Resources
4. ResourcesGained
5. ResourcesSpent
6. ResourceTypeId mapping
7. Unknown/reserved slot preservation/skipping by declared delta.

The parser should NOT need to fully understand nested members like Tutorial, LiveOps or VipStatus yet. VersionTolerant deltas allow those slots to be skipped safely.

## Design rule

Never parse nested PlayerModel fields by guessed fixed offsets across the whole file.

Instead:
- read the PlayerModel member-count and all deltas,
- compute each slot span,
- decode only known/needed slots,
- skip unknown/reserved/nested slots using their declared delta.

This keeps the parser tolerant of historical reserved slots and future additive fields.
