# ANIMAS / TITANS MEMORYPACK MAP — 0.62.1621

Date: 2026-11-14

Sources:
- current IL2CPP v39 dump
- fresh PlayerAnimasModel.dat
- verified UpgradeableSkill layout from the Hero analysis

Raw user/account files are not committed.

## PlayerAnimasModel

Current payload is VersionTolerant with 5 members:

| Slot | Field | Current bytes |
|---:|---|---:|
| 0 | LastId | 4 |
| 1 | AnimasById | 436 |
| 2 | SeenAnimaConfigIds | 4 |
| 3 | ReceivedAnimasCount | 68 |
| 4 | ReceivedChromaAnimaConfigIds | 4 |

Observed snapshot:
- LastId = 4
- AnimasById contains 4 PlayerAnima entries

## PlayerAnima

Current PlayerAnima is VersionTolerant with 13 serialized slots.

Observed member lengths are identical across all four current Animas:
4, 8, 4, 4, 4, 4, 16, 0, 36, 4, 1, 1, 4

Verified mapping:

| Slot | Field | Type |
|---:|---|---|
| 0 | InventoryId | int32 |
| 1 | ConfigId | int64 |
| 2 | EmpowermentLevel | int32 |
| 3 | Level | int32 |
| 4 | Experience | int32 |
| 5 | TotalExperience | int32 |
| 6 | RecentBattleTime | Nullable<DateTime> |
| 7 | RESERVED / removed | zero length |
| 8 | SkillLevels | List<UpgradeableSkill> |
| 9 | Rank | AscensionRank / int32 |
| 10 | Locked | bool |
| 11 | ChromaEnabled | bool |
| 12 | Skin | CharacterSkin / int32 |

Evidence level: HIGH.

### Ordering evidence

The current IL2CPP class exposes:
- InventoryId
- ConfigId
- Rank
- EmpowermentLevel
- Level
- Experience
- TotalExperience
- RecentBattleTime
- SkillLevels
- Locked
- ChromaEnabled
- Skin

However serialized VersionTolerant order is historical rather than simple declaration order.

Observed values make the mapping unambiguous:
- slot 2 values are 0, consistent with EmpowermentLevel
- slot 3 values are 6/1, consistent with Level
- slot 4 values are 950/0, consistent with current Experience
- slot 5 values are 3400/0, consistent with TotalExperience
- slot 9 values are 3/4, valid AscensionRank values
- slot 10 is bool lock state
- slot 11 is bool chroma state
- slot 12 is CharacterSkin enum value

## SkillLevels

Slot 8 is 36 bytes for every current Anima:
- 4-byte list count = 4
- four UpgradeableSkill entries
- each UpgradeableSkill is 8 bytes: SkillKind + Level

4 + (4 * 8) = 36 bytes exactly.

This matches the already verified UpgradeableSkill struct used by PlayerHero.

## Bot value

A read-only Anima/Titan parser can provide:
- inventory identity
- ConfigId
- rank
- empowerment
- level / XP
- lock protection
- recent use
- skill levels
- chroma/skin state

This enables future Titan progression, duplicate protection, skill upgrades and team-builder logic without OCR.

## Development sequencing

Do not interrupt DATA-003 Phase 2.

This schema is ready for a later structured-data implementation package alongside PlayerHeroesModel / PlayerHero.
