# ACCOUNTSTATE / PLANNER CONTRACT

Date: 2026-11-14

This document bridges low-level snapshot parsers and the future autonomous planner.

## Separation of concerns

Raw snapshot parser:
- knows MemoryPack/schema
- returns immutable parsed model

AccountState adapter:
- joins models
- creates normalized domain facts
- attaches source/version/freshness/confidence

Goal generators:
- inspect AccountState
- emit candidate Goals
- never click

Scheduler:
- applies hard gates
- scores eligible Goals
- chooses one Goal
- applies commitment/preemption rules

Task planner:
- decomposes Goal into registered Skills

Skill:
- navigates/acts/verifies
- publishes outcome/events

## Initial normalized AccountState domains

Account:
- level
- XP
- days played

Resources:
- current balances
- lifetime gained/spent
- regeneration sync timestamps
- configured reserves

Roster:
- heroes
- Animas/Titans
- locks
- equipment references
- progression levels

Gear:
- relic inventory
- accessory inventory when schema available
- equipped relationships

Quests:
- active quest states
- completed prototype IDs
- periodic reset windows
- achievement progress

Arena:
- points
- opponents
- refresh time
- battle stats
- token balance joined from Resources

Battle:
- level stats
- claimed rewards
- last battles
- tower data
- MultiBattle session
- presets

Clan:
- membership
- activity/chest state
- Boss2 state

Events:
- tournaments
- event progress/rewards when nested schemas are mapped

Inbox:
- availability / items when present

Shop:
- offers/history for read-only planning
- purchase actions remain blocked by default policy

Visual:
- current screen
- modal
- loading
- recognized targets
- confidence
- frame timestamp

Health:
- parser/source health
- capture health
- navigation circuit states
- repeated failure counters

## Cross-model joins

Examples:

Arena opportunity:
PlayerModel.Resources[Arena_Token]
+ PlayerArenaModel.Opponents
+ PlayerArenaModel.LastOpponentsRefreshTime
+ visual current screen

Hero loadout:
PlayerHeroesModel.HeroesById
+ PlayerHero.RelicIdBySlot
+ PlayerRelicsModel.RelicsById
+ later PlayerAccessoriesModel

Quest routing:
PlayerQuestsModel active state
+ static quest prototype definition
+ PlayerBattle/Resources/Roster facts
+ capability registry

Campaign reward opportunity:
PlayerBattleModel.LevelStats
+ ClaimedCampaign*Rewards
+ visual campaign navigation capability

## Fact identity

Facts should use stable semantic keys, not binary slot numbers.

Examples:
resources.gold
resources.arena_token
arena.points
arena.opponents
quests.daily.finish_time
heroes.by_id
battle.multibattle.status
visual.screen

Binary slot knowledge remains encapsulated inside parsers.

## Source versioning

When an aggregate snapshot is the source:
- preserve AggregateSnapshot.version
- preserve UpdatedAtUtc
- adapter writes both into StateFact provenance

When source version changes:
- publish SnapshotChanged(model)
- invalidate derived/joined facts dependent on that model
- rebuild them
- trigger planner only if relevant Goal inputs changed

## Derived facts

Derived facts must list dependencies.

Example:
arena.tokens_near_cap
depends on:
- resources.Arena_Token
- arena token cap/config
- ArenaTokenSyncTime

hero.safe_to_consume
depends on:
- hero Locked
- rarity/config metadata
- roster duplicate count
- configured protection policy

Derived facts are never treated as raw source truth.

## Planner-facing query examples

- get_fresh("resources.energy", max_age=...)
- require("arena.opponents")
- get_goal_inputs("spend_arena_token")
- explain("arena.tokens_near_cap")

Implementation names may differ; these describe behavior.

## No direct parser coupling

Goal code must not import:
- MemoryPack decoding functions
- slot numbers
- file paths

Goal code consumes normalized AccountState only.

This prevents schema changes from contaminating planner logic.
