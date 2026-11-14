# ARENA MEMORYPACK MAP — 0.62.1621

Date: 2026-11-14

Sources:
- current IL2CPP v39 dump
- fresh PlayerArenaModel.dat
- MemoryPack VersionTolerant behavior

Raw account files are not committed.

## PlayerArenaModel

Current payload:
- member count: 18
- current IL2CPP model fields: 12
- six historical/reserved slots

Verified current slot layout:

| Slot | Field | Bytes | Evidence |
|---:|---|---:|---|
| 0 | Points | 4 | int32, current value 534 |
| 1 | Defense | 150 | ArenaDefenseSetup object |
| 2 | RESERVED | 0 | historical gap |
| 3 | RESERVED | 0 | historical gap |
| 4 | RESERVED | 0 | historical gap |
| 5 | LastWeekProcessTime | 8 | DateTime |
| 6 | RESERVED | 0 | historical gap |
| 7 | LastOpponentsRefreshTime | 8 | DateTime |
| 8 | LastWeeklyPoints | 4 | int32 |
| 9 | HallBonuses | 61 | list count = 3 |
| 10 | Stats | 91 | nested VersionTolerant object, header count = 18 |
| 11 | RESERVED | 0 | historical gap |
| 12 | Opponents | 24167 | list count = 10 |
| 13 | RESERVED | 0 | historical gap |
| 14 | CurrentBattleOpponent | 1 | null MemoryPack object in current snapshot |
| 15 | FinishedOpponents | 179766 | list count = 23 |
| 16 | ShopStateByPeriod | 4 | empty dictionary in current snapshot |
| 17 | LastWeeklyReward | 1 | null MemoryPack object in current snapshot |

Evidence level:
- HIGH for all scalar/date/list/null assignments above.
- The slot map is uniquely constrained by exact MemoryPack shapes and current IL2CPP field types.

## Useful nested models

### ArenaOpponent

Current fields include:
- Name
- Level
- ArenaPoints
- TeamSetup
- Avatar
- Frame
- ClanAbbreviation
- CreatorsInfo
- IsVip
- VipLevel
- Result

This means opponent selection can eventually use structured data for:
- opponent level
- opponent Arena points
- team composition
- previous result state

before any UI click.

### PlayerArenaHallBonus

Fields:
- Element
- Stat
- Level

Current HallBonuses list contains 3 entries.

### ArenaBattleStats

Current model exposes:
- TotalOffenseBattles
- TotalOffenseWins
- TotalDefenseBattles
- TotalDefenseWins
- MaxLeagueReached
- TotalBattlesByLeague
- current/previous week attack and defense counts/wins

This can feed performance-aware Arena strategy.

### ArenaShopPeriodState

Fields:
- RefreshTime
- ItemPurchaseCount

## Architecture consequence

Arena should not be modeled as "open screen and OCR opponent cards".

Preferred flow:
1. read PlayerArenaModel
2. know token balance from PlayerModel.Resources
3. rank candidate opponents from structured opponent data
4. navigate UI to selected candidate
5. verify visible card/team matches expected structured candidate
6. only then start battle

This separates decision-making from visual navigation.

## Future parser acceptance checks

- Points
- opponent counts
- LastOpponentsRefreshTime
- CurrentBattleOpponent null/non-null
- HallBonuses
- Stats
- LastWeeklyReward
- LastWeeklyPoints
- ShopStateByPeriod

Opponent/team parsing should be a separate nested-schema package after top-level Arena parsing.
