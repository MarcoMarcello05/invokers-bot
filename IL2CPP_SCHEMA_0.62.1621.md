# IL2CPP SCHEMA RESEARCH — Windows build 0.62.1621-0cc5

Date: 2026-11-14

Source files supplied by the user:
- GameAssembly.dll
- UnityPlayer.dll
- global-metadata.dat
- GAME_FILE_LIST.txt

Raw binaries are not committed to the public repository.

## Metadata format

The supplied `global-metadata.dat` starts with:
- magic: `0xFAB11BAF`
- metadata version: `39`

This is a newer counted IL2CPP metadata layout used by recent Unity 6 builds. Older Il2CppDumper implementations that only support up to v31 are not suitable as the primary parser for this build.

Research references:
- https://github.com/morluto/rea/blob/main/docs/il2cpp-metadata.md
- https://github.com/morluto/rea/blob/main/src/il2cpp/Il2cppMetadataFile.ts
- https://github.com/morluto/rea/blob/main/src/il2cpp/Il2cppMetadataMembers.ts
- https://github.com/Perfare/Il2CppDumper

The v39 header in this sample contains 31 counted sections and is structurally consistent with the current public v39 layout.

Observed high-level counts:
- type definitions: 35,395
- methods: 240,401
- fields: 148,031
- images: 199
- parameters: 238,669
- generic containers: 9,882
- metadata type-definition index width: 2 bytes
- generic-container index width: 2 bytes
- parameter index width: 4 bytes
- native TypeIndex width: 4 bytes

## Primary account aggregate schemas

### PlayerModel
Namespace: `Shared.Choreograph.Models`

Important fields/properties:
- PlayerId
- Name
- RegistrationDate
- Level
- Experience
- TotalExperience
- EnergySyncTime
- Resources
- ResourcesGained
- ResourcesSpent
- LastActivityDate
- Boosters
- ConfigVersion
- Tutorial
- Settings
- ClaimedPlayTimeRewards
- ClaimedPlayerLevelRewards
- DailyLoginPrograms
- SummonResults
- SummonBonusSystem
- MultiBattleTokensRefreshTime
- TodayTotalPlayedMinutes
- ArenaTokenSyncTime
- LiveOps
- RelicSwapPassFinish
- DaysPlayed
- VipStatus
- LobbySelectedHero
- LobbySelectedAnimaId

### PlayerQuestsModel
Important fields:
- LastQuestId
- ActiveQuestsById
- CompletedPrototypeIds
- PeriodicGroups
- AchievementGroups
- TotalCompletedQuests

Related types:
- `PlayerPeriodicGroup`: StartTime, FinishTime
- `PlayerAchievementGroup`: CurrentLevel, Progress

### PlayerHeroesModel
Important fields:
- LastId
- HeroesById
- LobbyHeroIds
- SeenHeroConfigIds
- ReceivedHeroesCount
- StarterHeroId
- FusedHeroesCountByOutputGdId
- RemovableFuseMaterialGdIds
- HeroRating
- ReceivedChromaHeroConfigIds

### PlayerHero
Important fields:
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
- SkillLevels
- RelicIdBySlot
- AccessoryIdBySlot
- AwakeLevel
- AwakeNodeIds
- ChromaEnabled
- Skin

This gives the bot a structured source for roster, progression, equipment references and protection decisions.

### PlayerRelicsModel
Important fields:
- LastId
- RelicsById
- Randoms

### PlayerRelic
Important fields:
- InventoryId
- Slot
- Rank
- Rarity
- Set
- EquippedHeroId
- Level
- IsSeen
- Bonuses

This strongly supports building a gear evaluator from structured state instead of OCR.

### PlayerAccessoriesModel
Important fields:
- LastId
- AccessoriesById
- Randoms

### PlayerAccessory
Important fields:
- InventoryId
- Slot
- Rank
- Rarity
- Faction
- EquippedHeroId
- Level
- IsSeen
- Bonuses

### PlayerAnimasModel
Important fields:
- LastId
- AnimasById
- SeenAnimaConfigIds
- ReceivedAnimasCount
- ReceivedChromaAnimaConfigIds

### PlayerAnima
Important fields:
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

### PlayerArenaModel
Important fields:
- Points
- Defense
- Opponents
- FinishedOpponents
- CurrentBattleOpponent
- LastWeekProcessTime
- LastOpponentsRefreshTime
- LastWeeklyReward
- LastWeeklyPoints
- HallBonuses
- ShopStateByPeriod
- Stats

### PlayerBattleModel
Important fields:
- FormationLevelById
- LevelStats
- LastMetaBattleSetup
- Presets
- LastBattles
- TowerData
- ClaimedCampaignNormalRewards
- ClaimedCampaignHardRewards
- ClaimedCampaignBrutalRewards
- AutoBattleDataByArea
- Statistics
- CampaignChapterPresets
- AsyncPvpPreset
- MultiBattleSession
- TowerPresets
- LastTournamentBattleContext
- DailyBattleStartCounts

### MultiBattleSession
Important fields:
- CurrentStatus
- Settings
- Stats
- TotalHeroesPerformance
- TeamFormation
- AccumulatedHeroXp
- StartedAt
- UnboostedAccumulatedReward
- BoostedAccumulatedRewardByBooster
- Lpi
- VipBonusAccumulatedReward
- HeroXpBreakdown

### PlayerClanModel
Important fields:
- Membership
- DailyActivity
- PendingActivityChest
- DailyBossActivity
- PendingBossChest
- LastClaimedActivityChestDayUtc
- LastClaimedBossChestDayUtc
- Boss2

### PlayerClanBoss2State
Important fields:
- DayUtc
- ReplaysUsed
- StartedDifficulties
- Chests
- BestDamageByDifficulty

### PlayerClanBoss2Chest
Important fields:
- ClanId
- DayUtc
- DifficultyId
- Damage
- Tier
- BossDefeated
- PersonalClaimed
- KillClaimed
- Forfeited
- derived: Claimed
- derived: HasPendingReward

### PlayerGlobalEventsModel
Important fields:
- TournamentsById
- FinishedNoviceTournament
- CompletedNoviceTournamentGroupIds

The metadata also exposes tournament participation state, unlocked/claimed rewards and scoring-related models.

### PlayerInboxModel
Important fields:
- LastInboxItemId
- ItemsById

### PlayerShopModel
Important fields:
- LastPurchaseId
- LastPurchaseTime
- ShopHash
- Purchases
- Offers
- FirstPurchaseTime
- TotalUsd
- AppliedTriggers
- RewardStateByPurchase

## Resource model

`PlayerModel.Resources` points to a structured `Resources` model whose raw values are stored in `RawValues`.

The metadata contains a large `ResourceTypeId` enum. Confirmed resource identifiers include:
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
- summon Stars and Star fragments
- summon Orbs and Orb fragments
- Codexes
- Prisms
- elemental/awakening resources
- rank/class/faction materials
- event currencies
- VIP-duration resources

This is a major finding: the universal resource planner should be driven from structured Resources/ResourceTypeId state, not OCR counters wherever possible.

## Irreversible-action evidence in metadata

Relevant event/model names found:
- SellHeroEvent
- AscendHeroEvent
- LevelUpHeroSkillEvent
- LockHeroesEvent
- SummonHeroEvent
- AddHeroExperienceEvent
- Lock/selection state on PlayerHero
- Relic and Accessory structured inventories

The presence of explicit lock state is especially useful for the future irreversible-action policy.

## Architectural conclusion

The clean bot architecture should now assume that a large part of account intelligence can come from structured local state:

1. Parse player aggregate snapshots read-only.
2. Normalize into AccountState / WorldState.
3. Use vision mostly for navigation, dialogs and visual state verification.
4. Use structured data for:
   - resources,
   - quests,
   - roster,
   - gear,
   - Arena state,
   - campaign/multi-battle state,
   - clan state,
   - event/tournament state,
   - inbox/reward availability where exposed.
5. Use OCR only for values not available reliably in structured models.

## Next analysis step

Before any production parser coding is handed to DEVELOPER:

1. map the snapshot serialization for the top-priority models,
2. identify their formatter/serialization contracts,
3. determine whether current snapshot files can be decoded directly from the generated formatter logic/schema,
4. create an AccountState field-source matrix,
5. only then issue a narrowly scoped developer prompt.

No production parser coding has been assigned yet.
