# ACCOUNTSTATE SOURCE MATRIX — INITIAL

Date: 2026-11-14

This matrix defines the preferred source of truth for bot decisions.

## Source priority

1. local structured snapshot state
2. structured event/update signal
3. visual recognition/template
4. targeted OCR
5. fixed geometry only for action coordinates

## Core account facts

| Fact | Primary source | Secondary/verification |
|---|---|---|
| account level / XP | PlayerModel | UI only for diagnostics |
| Gold/Gems/Energy | PlayerModel.Resources | HUD visual sanity check optional |
| Arena token count | PlayerModel.Resources | Arena UI |
| MultiBattle tokens | PlayerModel.Resources | UI |
| roster | PlayerHeroesModel | hero screen |
| hero rank/level/XP/lock | PlayerHeroesModel | hero details screen |
| hero relic links | PlayerHero.RelicIdBySlot | relic screen |
| hero accessory links | PlayerHero.AccessoryIdBySlot | accessory screen |
| Titan/Anima roster | PlayerAnimasModel | anima screen |
| relic inventory | PlayerRelicsModel | relic UI |
| accessory inventory | PlayerAccessoriesModel | accessory UI |
| active quests | PlayerQuestsModel | quest UI |
| quest progress/status | PlayerQuestsModel | quest UI |
| periodic quest windows | PlayerQuestsModel.PeriodicGroups | clock/UI |
| Arena points | PlayerArenaModel | Arena UI |
| Arena opponents | PlayerArenaModel | opponent cards |
| Arena refresh time | PlayerArenaModel | Arena UI |
| Arena weekly stats | PlayerArenaModel.Stats | Arena UI |
| campaign level progress/stars | PlayerBattleModel.LevelStats | campaign map |
| claimed campaign rewards | PlayerBattleModel ClaimedCampaign* | campaign map |
| MultiBattle state | PlayerBattleModel.MultiBattleSession | battle UI |
| tower/spire progress | PlayerBattleModel TowerData/Statistics | tower UI |
| presets | PlayerBattleModel | team-selection UI |
| clan membership/activity | PlayerClanModel | clan UI |
| clan boss state | PlayerClanModel.Boss2 | boss UI |
| tournament/event state | PlayerGlobalEventsModel | event UI |
| inbox state | PlayerInboxModel | inbox UI |
| shop purchase/offers state | PlayerShopModel | shop UI |

## Important source split

Structured state answers:
- what the account owns
- what progress exists
- what resources are available
- what candidate action is rational

Vision answers:
- what screen is visible right now
- whether a modal is blocking
- where the intended UI control is
- whether the expected UI transition occurred

Do not use OCR to rediscover structured account facts unless structured state is unavailable/stale.

## Freshness policy idea

Each AccountState fact should include:
- source
- source_version
- observed_at
- confidence
- stale_after or freshness class

Suggested classes:
- REALTIME_VISUAL: 0.5-2s
- FAST_ACCOUNT: refresh after any relevant action or snapshot version change
- SESSION: valid until scene/account transition
- SLOW_META: safe for minutes/hours
- STATIC: versioned by game build/config version

Exact thresholds belong in later implementation policy, not in the parser.

## QUEST-LIVE-001 implemented source

Source quests / PlayerQuestsModel.dat / union 8 uses the existing stat guard, digest, freshness and invalidation path. QuestView requires fresh typed source with digest. QuestGoalFacts exposes unknown (None) when unavailable, not false/zero. No scheduler registration. Completed active state is a candidate only.
