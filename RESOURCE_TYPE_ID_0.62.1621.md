# RESOURCE TYPE ID VERIFICATION — 0.62.1621

Date: 2026-11-14

Purpose: remove the remaining DATA-003 Phase 2 uncertainty around ResourceTypeId.

## Sources compared

1. Archived project enum:
   `archive/pre-analyser-2.0-restart-2026-11-14`
   `InvokersBot_CODEX_HANDOFF/src/schemas/ResourceTypeId.cs`

2. Current Windows build IL2CPP dump:
   build `0.62.1621-0cc5`
   metadata v39 / Unity 6000.3.0b1+

## Result

The current IL2CPP dump contains 181 ResourceTypeId constants.

The archived ResourceTypeId.cs contains the same named numeric mapping for the current enum set.

Therefore the archived enum mapping is valid as a source for the Phase 2 parser, provided that:

- the implementation remains read-only,
- unknown numeric IDs are preserved rather than rejected,
- parser correctness never depends on every future resource ID being known,
- enum names are convenience metadata and the numeric ID remains canonical.

## Examples verified in current dump

- Unknown = 0
- Gem = 1
- Gold = 2
- Energy = 3
- Memorium = 4
- Token_MultiBattle = 11
- ClanBoss2Key = 12
- Arena_Token = 21
- Arena_Coin = 22
- ArenaMedal_Bronze = 23
- ArenaMedal_Silver = 24
- ArenaMedal_Gold = 25
- AccountXp = 34
- HeroXp = 35
- XpPotion_Small = 51
- XpPotion_Regular = 52
- XpPotion_Big = 53
- XpPotion_Premium = 54
- SI_WildStar = 101
- SI_FateStar = 102
- SI_DestinyStar = 103
- SI_DivineStar = 104
- SI_RadiantStar = 105
- SI_DreamOrb = 106
- SI_WonderOrb = 107
- SI_MiracleOrb = 108
- SI_LegendaryStar = 111
- SI_MythicOrb = 112
- VIP_1d = 1000
- VIP_7d = 1001
- VIP_30d = 1002

The full enum is recoverable from the current IL2CPP dump and need not be guessed.

## Development decision

DATA-003 Phase 2 has no remaining schema blocker for ResourceTypeId.

Developer may port the archived enum into the clean project or generate an equivalent Python IntEnum/map, but should preserve unknown IDs as integers.

Do not couple binary parsing to display/localization text.
