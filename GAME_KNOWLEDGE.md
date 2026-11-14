# GAME KNOWLEDGE

Date: 2026-11-14
Current researched public game baseline: Update 0.62 era.

## Product interpretation

The bot target is the **whole account loop**, not only battle modes. It must understand both:
1. PLAY systems: Campaign, Arena, Bosses, Spires, Clan Bosses, Events.
2. ACCOUNT MANAGEMENT systems: summoning, roster development, gear, skills, resources and reward claiming.

## Battle / progression domains

### Campaign
- Normal / Hard / Insane progression and farming.
- Stage Challenge Stars and first-clear rewards.
- Relic/rune farming.
- Multi-Battle and Background Battle support.

### Arena
- Offense opponent list and defense team.
- Arena tokens.
- Opponent/team inspection.
- Formation/team selection.
- Battle/result/reward loop.

### Boss Mode
Relic Bosses:
- Ulgorim
- Althar
- Sakiel

Crest/resource Bosses:
- Pentiax
- Yskara
- Galvos
- Hyxxis
- Koltmos

Garudas:
- Astral
- Water
- Fire
- Earth
- Wind
- Light
- Dark

Boss decisions require stage, drops, Corruptions/Tolerances, ACC/RES needs, team composition and farming targets.

### Spires
- Six elemental Spires.
- Normal and Hard.
- Keys, floor progression, rewards and boss floors.
- Auto Climb / Multi-Battle relevant.

### Clans
- Clan Activity Quests / Activity Stars.
- Clan Quest Chests.
- Sorgott clan boss, Accessories and Rubies.
- Sedula clan boss, four difficulties, personal damage rewards and clan-kill rewards.
- Contributors/reward claiming.

### Events / tournaments
- Chase-style events and tournament objectives.
- Timing-specific resource use can increase event value.
- Planner must be event-aware rather than blindly spending summon/farm resources.

## Quests / achievements / rewards

### Progress Quests
- 40+ pages and roughly 500 quests according to current official guide.
- GO links can route directly to required systems.
- Page-completion chests.

### Recurring Quests
- Daily.
- Weekly.
- Monthly.
- Claim individual and completion rewards.

### Achievements
Categories include at least:
- General.
- Summon.
- Development.
- Gear.
- Battle.
- Tactics-related achievements added in 0.62.
- Claim newly completed achievements after relevant actions.

### Other reward systems
- Daily Login.
- Playtime Rewards at timed milestones.
- Inbox.
- Weekly personal promo-code reward (external official portal + in-game inbox).
- First-clear rewards.
- Mode-specific chests/reward tracks.

## Invoker management

The bot must support:
- inspect Collection / Index,
- summon Invokers with Stars,
- identify new/duplicate/rarity/faction/element/class/tags where data is available,
- level Invokers with XP Potions,
- use Auto Select intelligently,
- Ascend up to 6 stars,
- choose Echoes / expendable Invokers as ascension material,
- Awaken Invokers and unlock Soul Sign nodes,
- upgrade Invoker Skills using Codexes + Gold,
- bind appropriate Titans,
- equip/optimize Relics and Accessories,
- Dismiss unwanted Invokers for XP Potions,
- protect valuable Invokers from irreversible consumption.

Legendary Invokers cannot be dismissed.

## Titan management

The bot must support:
- summon Titans with Orbs,
- level Titans with XP Potions,
- Ascend with Dragonsouls / expendable Titans,
- Empower with Titanhearts / duplicates,
- upgrade Titan Skills / Invokation effects with Prisms + Gold,
- choose bindings by Faction and use-case,
- protect valuable Titans from irreversible consumption.

## Relics

The bot must support:
- inspect inventory,
- equip / replace,
- Auto Equip where appropriate,
- Preview loadouts,
- optimize sets/stats,
- upgrade Relics to level 20 using Gold + Memorium,
- filter by rarity/rank/type/main stat/substats/set,
- sell for Gold,
- crush for Memorium,
- batch sell/crush,
- dispose directly from battle results where appropriate,
- manage storage pressure,
- preserve valuable/high-potential Relics.

Relic Rank/Rarity cannot be increased; only Level can.

## Accessories

The bot must support:
- faction-aware equipping,
- slot unlock rules tied to Invoker Awakening,
- level to 20,
- Auto Equip support,
- sell/crush,
- evaluate stats similarly to Relics,
- preserve strong Accessories.

Accessory types:
- Amulets
- Earrings
- Banners
- Talismans
- Flasks

## Skills / Tactics

### Invoker Skills
- Upgrade with Rare/Epic/Legendary Codexes and Gold.

### Titan Skills
- Upgrade with Rare/Epic/Legendary Prisms and Gold.

### Tactics
- Tactics can be upgraded to level 20 using Playbooks + Gold as of update 0.62.
- Planner should choose upgrade spending based on account goals rather than spending blindly.

## Resource management

Planner must track and budget resources including, where relevant:
- Energy
- Gold
- Gems
- Arena Tokens
- Multi-Battle Tokens
- Spire Keys
- XP Potions
- Memorium
- Stars / Star fragments
- Orbs / Orb fragments
- Echoes
- Dragonsouls
- Codexes
- Prisms
- Titan Spark
- Titanhearts / Elder Titanhearts
- Astral / Elemental Essences
- Class Crests
- Faction Runes
- Playbooks
- event currencies / rewards
- clan-specific Rubies / Pearls or reward progress where exposed.

## Battle execution

The bot must understand:
- pre-battle team selection,
- filtering/sorting Invokers,
- Titan binding,
- Tactics,
- Auto Mode,
- Manual combat where necessary,
- Skills / Combo attacks / Ultimates / Titan Invokation,
- Multi-Battle,
- Background Battles,
- result screens,
- battle reports,
- replay/retry/stop decisions.

## Safety / irreversible-action gates

These actions require much stronger decision rules than ordinary navigation:
- Dismiss Invoker.
- Consume Invoker/Echo for Ascension.
- Consume Titan/Dragonsoul for Ascension.
- Consume duplicate/Titanheart for Empowerment.
- Sell/crush Relics or Accessories.
- Spend Gems.
- Spend rare summon resources.
- Spend rare upgrade resources.
- Replace/equip gear with Gold cost.

The autonomous bot can perform them, but only through registered policy rules based on account state, never through generic click logic.

## Architectural consequence

A complete bot needs:
- universal world/account model,
- inventory/resource model,
- task/quest parser,
- progression planner,
- gear evaluator,
- roster evaluator,
- battle-team builder,
- boss matchup logic,
- event-aware scheduler,
- reward collector,
- irreversible-action policy engine,
- reusable navigation/interaction skills.

Arena is only one skill among these systems.

## Primary official sources researched

- https://invokers.com/guides/invokers-master-guide/
- https://invokers.com/guides/levelling-up-invokers/
- https://invokers.com/guides/invoker-ascension/
- https://invokers.com/guides/invoker-awakening/
- https://invokers.com/guides/invoker-skills/
- https://invokers.com/guides/titans-master-guide/
- https://invokers.com/guides/upgrading-titans/
- https://invokers.com/guides/titan-ascension/
- https://invokers.com/guides/titan-empowerment/
- https://invokers.com/guides/relics/
- https://invokers.com/guides/accessories/
- https://invokers.com/guides/bosses/
- https://invokers.com/guides/clans/
- https://invokers.com/hub/spires/
- https://invokers.com/guides/arena/
- https://invokers.com/guides/multi-battle/
- https://invokers.com/guides/how-to-progress-and-earn-free-rewards/
- https://invokers.com/guides/how-to-get-free-stars-and-orbs/
- https://invokers.com/news/66/
