# BATTLE / MULTIBATTLE MEMORYPACK MAP — 0.62.1621

Date: 2026-11-14

Sources:
- current IL2CPP v39 dump
- fresh PlayerBattleModel.dat
- MemoryPack VersionTolerant behavior

Raw account files are not committed.

## PlayerBattleModel

Current payload:
- member count: 28
- current IL2CPP fields: 25
- reserved slots: 3, 7, 10

Because there are exactly 25 nonzero slots and their binary shapes match the 25 current fields, the current mapping is strongly verified.

| Slot | Field | Bytes |
|---:|---|---:|
| 0 | FormationLevelById | 148 |
| 1 | LevelStats | 46856 |
| 2 | LastMetaBattleSetup | 1 |
| 3 | RESERVED | 0 |
| 4 | Presets | 4 |
| 5 | LastBattleNotUsedBoostedRewards | 4 |
| 6 | Randoms | 2572 |
| 7 | RESERVED | 0 |
| 8 | LastBattles | 5087 |
| 9 | ScheduleDungeonsPassExpiration | 8 |
| 10 | RESERVED | 0 |
| 11 | TowerData | 28 |
| 12 | ClaimedCampaignNormalRewards | 44 |
| 13 | ClaimedCampaignHardRewards | 4 |
| 14 | ClaimedCampaignBrutalRewards | 4 |
| 15 | TotalValidationFailures | 4 |
| 16 | CurrentPeriodValidationFailures | 4 |
| 17 | ValidationPeriodStartDate | 16 |
| 18 | AutoBattleDataByArea | 139 |
| 19 | RegionPassExpiresAt | 4 |
| 20 | MostUsedHeroesUsageByDay | 164 |
| 21 | Statistics | 554 |
| 22 | CampaignChapterPresets | 2276 |
| 23 | AsyncPvpPreset | 272 |
| 24 | MultiBattleSession | 257 |
| 25 | TowerPresets | 4 |
| 26 | LastTournamentBattleContext | 1 |
| 27 | DailyBattleStartCounts | 73 |

## Strong structural checks

FormationLevelById:
- dictionary count 18
- payload = 4 + 18 * 8 = 148 bytes exactly

ClaimedCampaignNormalRewards:
- list count 10
- payload = 4 + 10 * 4 = 44 bytes exactly

Campaign Hard / Brutal rewards:
- 4-byte empty lists in current snapshot

LastBattles:
- list count 10

AutoBattleDataByArea:
- dictionary count 15

DailyBattleStartCounts:
- dictionary count 3

## LevelStats

Each LevelStats exposes:
- Victories
- Defeats
- LastBattleTime
- BestTimeInSeconds
- BestTimeTeamPreset
- LastUsedTeamPreset
- Stars

This is a key structured source for campaign/dungeon progression and star completion.

## PlayerBattleStatistics

Structured statistics include:
- TotalCampaignBattles
- CampaignBattlesByRegion
- TotalDungeonBattles
- TotalDungeonVictories
- TotalDungeonGearPieces
- DungeonBattleCountsByLevel
- DungeonMaxStageByRegion
- TowerMaxStageByRegion
- TowerVictoriesByRegion
- TowerFullClearsByRegion
- HeroUsageByConfigId
- AnimaUsageByConfigId
- AnimaInvokeCountByConfigId
- highest single-hit hero/anima IDs and damage

These are useful for long-term optimization/analytics, not immediate navigation.

## MultiBattleSession

Current nested payload:
- VersionTolerant member count = 14
- no reserved slots observed

| Slot | Field | Current bytes |
|---:|---|---:|
| 0 | CurrentStatus | 4 |
| 1 | Settings | 27 |
| 2 | Stats | 57 |
| 3 | TotalHeroesPerformance | 4 |
| 4 | TeamFormation | 18 |
| 5 | AccumulatedHeroXp | 4 |
| 6 | StartedAt | 8 |
| 7 | UnboostedAccumulatedReward | 38 |
| 8 | BoostedAccumulatedRewardByBooster | 4 |
| 9 | Lpi | 16 |
| 10 | RelicCreationRandoms | 4 |
| 11 | VipBonusAccumulatedReward | 38 |
| 12 | AccessoryCreationRandoms | 4 |
| 13 | HeroXpBreakdown | 16 |

CurrentStatus is 0 in the supplied snapshot.

### StartMultiBattleSettings

Fields:
- Mode
- TotalTokensTaken
- StopIfLossesExceed
- Energy
- IsBackgroundBattle

This is enough to know how the active/background multi-battle was configured.

## Architecture consequence

Battle state should be a structured domain sensor, not a screen-state approximation.

Examples:
- Campaign first-clear reward eligibility: LevelStats + claimed reward lists
- Current multi-battle state: MultiBattleSession
- Existing presets: CampaignChapterPresets / AsyncPvpPreset / TowerPresets
- last battle history: LastBattles
- auto-battle configuration: AutoBattleDataByArea
- tower progress: TowerData + Statistics

Vision remains necessary to operate UI, but not to answer most "what should I do?" questions.

## Recommended implementation sequence

After PlayerModel/Resources and Hero core:
1. top-level PlayerBattleModel slot parser
2. LevelStats minimal parser
3. ClaimedCampaign* reward lists
4. MultiBattleSession
5. presets only when team-builder needs them
6. battle history/statistics later

Do not implement every nested type at once.
