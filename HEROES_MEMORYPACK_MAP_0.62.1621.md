# HEROES MEMORYPACK MAP — 0.62.1621

Date: 2026-11-14

Sources:
- current IL2CPP v39 dump
- fresh PlayerHeroesModel.dat
- current PlayerRelicsModel.dat for cross-reference
- MemoryPack runtime/generator behavior

Raw user/account files are not committed.

## PlayerHeroesModel

Current payload:
- VersionTolerant member count: 10
- no reserved gaps observed in the current model

Verified slot lengths in the supplied snapshot:

| Slot | Field | Bytes |
|---:|---|---:|
| 0 | LastId | 4 |
| 1 | HeroesById | 4976 |
| 2 | LobbyHeroIds | 4 |
| 3 | SeenHeroConfigIds | 20 |
| 4 | ReceivedHeroesCount | 900 |
| 5 | StarterHeroId | 8 |
| 6 | FusedHeroesCountByOutputGdId | 4 |
| 7 | RemovableFuseMaterialGdIds | 4 |
| 8 | HeroRating | 20 |
| 9 | ReceivedChromaHeroConfigIds | 4 |

Snapshot facts:
- LastId = 227
- HeroesById contains 30 PlayerHero entries
- LobbyHeroIds is empty in this capture
- StarterHeroId matches one of the current Hero ConfigIds

## PlayerHero

Current PlayerHero uses a VersionTolerant object with 22 serialized slots.

Verified map:

| Slot | Field | Evidence |
|---:|---|---|
| 0 | InventoryId | fixed int32; equals HeroesById dictionary key |
| 1 | ConfigId | fixed int64 |
| 2 | Rank | AscensionRank int32 |
| 3 | Level | int32 |
| 4 | Experience | int32 |
| 5 | TotalExperience | int32 |
| 6 | Locked | bool |
| 7 | InStorage | bool |
| 8 | Marker | CharacterMarker int32 |
| 9 | RecentBattleTime | nullable DateTime payload |
| 10 | RESERVED / removed | zero length in all 30 observed heroes |
| 11 | RelicIdBySlot | SortedDictionary<RelicSlot,int> |
| 12 | AccessoryIdBySlot | SortedDictionary<AccessorySlot,int> |
| 13 | RESERVED / removed | zero length in all 30 observed heroes |
| 14 | RESERVED / removed | zero length in all 30 observed heroes |
| 15 | AwakeNodeIds | List<int> |
| 16 | AwakeLevel | int32 |
| 17 | ChromaEnabled | bool |
| 18 | Skin | CharacterSkin int32 |
| 19 | RESERVED / removed | zero length in all 30 observed heroes |
| 20 | RESERVED / removed | zero length in all 30 observed heroes |
| 21 | SkillLevels | List<UpgradeableSkill> |

Evidence level: HIGH.

### Why slot 11 is RelicIdBySlot

Observed Hero InventoryId 1 contains eight pairs:
- RelicSlot 1 -> inventory relic 70
- 2 -> 40
- 3 -> 1
- 4 -> 74
- 5 -> 106
- 6 -> 48
- 7 -> 3
- 8 -> 50

RelicSlot enum from IL2CPP:
1 Weapon
2 Shield
3 Helmet
4 Pauldrons
5 Gauntlets
6 Chestplate
7 Belt
8 Boots

All eight referenced relic inventory IDs exist in the supplied PlayerRelicsModel snapshot.

This cross-model referential integrity strongly confirms slot 11.

### Why slot 21 is SkillLevels

UpgradeableSkill is a fixed MemoryPack struct with:
- SkillKind Kind
- int Level

The observed slot 21 payload is:
- Int32 list count
- repeated 8-byte UpgradeableSkill entries

Examples decode to valid SkillKind values such as:
- ActiveSkill1
- ActiveSkill2
- ActiveSkill3
- Ultimate
- Combo
- Tolerance1 / Tolerance2

Observed list sizes are 6 or 7 entries, matching the 52/60-byte member sizes:
- 4 + 6*8 = 52
- 4 + 7*8 = 60

### Other structural evidence

Across all 30 observed heroes:
- slots 10, 13, 14, 19, 20 are always zero-length
- slot 11 is either 4 bytes for an empty dictionary or 68 bytes for eight relic mappings
- slot 12 is 4 bytes in this snapshot, consistent with an empty Accessory dictionary
- slot 15 is 4 bytes in this snapshot, consistent with an empty AwakeNodeIds list
- slot 21 is 52 or 60 bytes and decodes cleanly as UpgradeableSkill list

## Useful AccountState fields now available

A read-only Hero parser can reliably expose:

- InventoryId
- ConfigId
- Rank
- Level
- Experience
- TotalExperience
- Locked
- InStorage
- Marker
- RecentBattleTime
- RelicIdBySlot
- AccessoryIdBySlot
- AwakeNodeIds
- AwakeLevel
- ChromaEnabled
- Skin
- SkillLevels

These fields are sufficient for future:
- roster inventory
- progression decisions
- duplicate/material protection
- lock-state safety policy
- gear relationship mapping
- awakening state
- skill-development planning

## Parser design

Use the same VersionTolerant strategy as PlayerModel:
1. read member count and all member-length deltas
2. compute per-slot spans
3. decode only verified slots
4. skip reserved/unknown slots by declared length
5. validate dictionary/list counts against each member span
6. never use global guessed file offsets

For HeroesById:
- dictionary count is Int32
- key is inventory id Int32
- value is one PlayerHero object
- verify PlayerHero.InventoryId equals dictionary key; mismatch should be surfaced as malformed/inconsistent data

## Development status

Do not interrupt the current DATA-003 Phase 2 PlayerModel/Resources implementation.

This map is ready to become a later DATA-003 Phase 3 developer package after Phase 2 is merged and CI-verified.
