# Invokers structured-data research

## D1 follow-up — 2026-11-13

See [D1_DECODING.md](D1_DECODING.md) for exact wire positions, fixture results,
limitations and the required Windows comparison capture. VersionTolerant wire
positions include reserved members and differ from the simplified backing-field
catalog. Resources, LevelStats, Arena preset and captured event participation now
use bounded field readers. Current own power is unknown because LastMetaBattleSetup
is null. The legacy 27-opponent scanner combines two lists and drops a Unicode
name; the structural lists contain 10 and 21 records, with field 12 now correlated to the current UI list by `_SILVA00`/6151; the
other list's exact history/cache semantics remain unproven. Unified GameState and planner-bridge integration are implemented;
event definition/name mapping still requires the runtime tournament catalog.

## Validated from IL2CPP dump
- PlayerModel.Resources -> Resources.RawValues -> SortedDictionary<ResourceTypeId,int>
- ResourceTypeId includes Gem=1, Gold=2, Energy=3, Arena_Token=21, Arena_Coin=22, AccountXp=34, HeroXp=35, WildStar=101 and all other listed resources.
- PlayerBattleModel.LevelStats -> LevelProgressionIdentifier => LevelStats(Victories, Defeats, LastBattleTime, BestTimeInSeconds, BestTimeTeamPreset, LastUsedTeamPreset, Stars).
- PlayerBattleModel.AsyncPvpPreset -> TeamPresetData(Formation, Slots, LeadPosition); TeamPresetSlot includes HeroInventoryId/HeroConfigId and anima IDs.
- PlayerBattleModel.LastMetaBattleSetup -> MetaBattleSetup.PlayerTeamSetup -> BattlePlayerTeamSetup.CombatPower.
- PlayerGlobalEventsModel -> TournamentsById, FinishedNoviceTournament, CompletedNoviceTournamentGroupIds.
- PlayerArenaModel additionally exposes FinishedOpponents, CurrentBattleOpponent, refresh time, HallBonuses, ShopStateByPeriod and ArenaBattleStats.
- PlayerBattleStatistics exposes campaign/dungeon/tower counts, max stages, hero/anima usage and highest hits.
- PlayerClanModel exposes pending activity/boss chests and Boss2 state.
- PlayerShopModel exposes offers/purchases, but autonomous purchasing remains blocked by policy.

## Architecture decision
Priority: structured snapshots/static data > UI Automation when actually exposed > small ROI/template matching > OCR fallback.
Actor transitions must be verified by state changes instead of fixed sleeps wherever possible.
MemoryPack VersionTolerant parsing should be schema-driven from dumped C# fields and field deltas rather than ad-hoc magic offsets.

## Original validation targets (see updated status above)
1. Capture/diff PlayerBattleModel before and after opening Arena formation to validate PlayerTeamSetup.CombatPower update.
2. Implement schema decoder for PlayerModel.Resources and PlayerBattleModel top-level VersionTolerant fields.
3. Decode LevelStats keys/values for campaign safe/highest level logic.
4. Decode AsyncPvpPreset slots and map inventory IDs to PlayerHeroesModel.
5. Decode GlobalEvents tournaments and map IDs through static data.
6. Probe Windows UIA tree once; use only if meaningful game controls are exposed.

Windows follow-up: all twelve A/B/C models are unchanged across navigation; own UI power 9368 is not persisted as a proven field. See the private local comparison result (not versioned).
