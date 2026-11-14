# MASTER CHECKLIST

Date: 2026-11-14

This file is the **permanent source-of-truth checklist** for the Invokers autonomous bot.

Rules:
- Every major feature has a stable ID.
- Status must be one of: OFFEN, IN ANALYSE, BEREIT ZUR ENTWICKLUNG, IN ENTWICKLUNG, TEST AUSSTEHEND, ABGESCHLOSSEN, BLOCKIERT.
- A feature is only ABGESCHLOSSEN when its acceptance criteria are actually met.
- Do not delete completed items. Keep history visible.
- New discoveries from research must be added here before implementation drifts.
- MASTER_STATUS.md should summarize this file, not replace it.

## A. Universal core

- [ ] CORE-001 | IN ENTWICKLUNG | Universal WorldState / Blackboard
- [ ] CORE-002 | IN ENTWICKLUNG | Goal model
- [ ] CORE-003 | IN ENTWICKLUNG | Central TaskScheduler
- [ ] CORE-004 | IN ENTWICKLUNG | Skill registry
- [ ] CORE-005 | OFFEN | Persistent run memory
- [ ] CORE-006 | OFFEN | Navigation graph
- [ ] CORE-007 | OFFEN | Recovery engine
- [ ] CORE-008 | OFFEN | Resource planner
- [ ] CORE-009 | OFFEN | Irreversible-action policy
- [ ] CORE-010 | OFFEN | Event-aware priority engine

## B. Perception / data

- [ ] DATA-001 | OFFEN | Fresh global UI screenshot inventory
- [ ] DATA-002 | IN ANALYSE | Fresh local Invokers data inventory
- [ ] DATA-003 | BEREIT ZUR ENTWICKLUNG | Structured snapshot readers: phase 1 envelope ready; PlayerModel/Resources phase 2 schema now verified
- [ ] DATA-004 | OFFEN | Action/event file watchers
- [ ] DATA-005 | IN ENTWICKLUNG | Window/client/DPI detection
- [ ] DATA-006 | IN ENTWICKLUNG | DXcam/MSS capture
- [ ] DATA-007 | IN ENTWICKLUNG | Template/ROI state recognition
- [ ] DATA-008 | OFFEN | Targeted OCR layer
- [ ] DATA-009 | OFFEN | Evidence fusion: structured data + vision + OCR
- [ ] DATA-010 | OFFEN | Replay dataset for offline recognition tests

## C. Global navigation / common interactions

- [ ] NAV-001 | OFFEN | Detect home/main screen
- [ ] NAV-002 | OFFEN | Navigate home from arbitrary known screen
- [ ] NAV-003 | OFFEN | Close generic popup
- [ ] NAV-004 | OFFEN | Detect/loading wait logic
- [ ] NAV-005 | OFFEN | Claim generic visible reward
- [ ] NAV-006 | OFFEN | Scroll/list handling
- [ ] NAV-007 | OFFEN | Tabs/submenus
- [ ] NAV-008 | OFFEN | Confirmation dialogs
- [ ] NAV-009 | OFFEN | Error/reconnect handling
- [ ] NAV-010 | OFFEN | Safe stop/resume

## D. Quests / rewards / progression

- [ ] QUEST-001 | OFFEN | Progress Quests inspect
- [ ] QUEST-002 | OFFEN | Progress Quest GO-navigation
- [ ] QUEST-003 | OFFEN | Progress Quest completion/reward claim
- [ ] QUEST-004 | OFFEN | Daily Quests
- [ ] QUEST-005 | OFFEN | Weekly Quests
- [ ] QUEST-006 | OFFEN | Monthly Quests
- [ ] QUEST-007 | OFFEN | Quest completion chests
- [ ] QUEST-008 | OFFEN | Achievements inspect
- [ ] QUEST-009 | OFFEN | Achievements claim
- [ ] QUEST-010 | OFFEN | Daily login reward
- [ ] QUEST-011 | OFFEN | Playtime rewards
- [ ] QUEST-012 | OFFEN | Inbox rewards
- [ ] QUEST-013 | OFFEN | First-clear rewards
- [ ] QUEST-014 | OFFEN | Other mode-specific reward tracks/chests

## E. Campaign

- [ ] CAMP-001 | OFFEN | Detect campaign screen
- [ ] CAMP-002 | OFFEN | Normal campaign progression
- [ ] CAMP-003 | OFFEN | Hard campaign progression
- [ ] CAMP-004 | OFFEN | Insane campaign progression
- [ ] CAMP-005 | OFFEN | Stage selection
- [ ] CAMP-006 | OFFEN | Challenge Stars logic
- [ ] CAMP-007 | OFFEN | Campaign farming target selection
- [ ] CAMP-008 | OFFEN | Multi-Battle
- [ ] CAMP-009 | OFFEN | Background Battle
- [ ] CAMP-010 | OFFEN | Campaign result/retry/stop logic

## F. Arena

- [ ] ARENA-001 | OFFEN | Detect Arena screen
- [ ] ARENA-002 | OFFEN | Opponent list parsing
- [ ] ARENA-003 | OFFEN | Opponent scoring
- [ ] ARENA-004 | OFFEN | Team/formation selection
- [ ] ARENA-005 | OFFEN | Arena token awareness
- [ ] ARENA-006 | OFFEN | Start battle
- [ ] ARENA-007 | OFFEN | Battle/result verification
- [ ] ARENA-008 | OFFEN | Win/loss handling
- [ ] ARENA-009 | OFFEN | Refresh logic
- [ ] ARENA-010 | OFFEN | Defense team management

## G. Boss Mode

- [ ] BOSS-001 | OFFEN | Ulgorim
- [ ] BOSS-002 | OFFEN | Althar
- [ ] BOSS-003 | OFFEN | Sakiel
- [ ] BOSS-004 | OFFEN | Pentiax
- [ ] BOSS-005 | OFFEN | Yskara
- [ ] BOSS-006 | OFFEN | Galvos
- [ ] BOSS-007 | OFFEN | Hyxxis
- [ ] BOSS-008 | OFFEN | Koltmos
- [ ] BOSS-009 | OFFEN | Astral Garuda
- [ ] BOSS-010 | OFFEN | Water Garuda
- [ ] BOSS-011 | OFFEN | Fire Garuda
- [ ] BOSS-012 | OFFEN | Earth Garuda
- [ ] BOSS-013 | OFFEN | Wind Garuda
- [ ] BOSS-014 | OFFEN | Light Garuda
- [ ] BOSS-015 | OFFEN | Dark Garuda
- [ ] BOSS-016 | OFFEN | Boss stage selection
- [ ] BOSS-017 | OFFEN | Corruption/Tolerance-aware team logic
- [ ] BOSS-018 | OFFEN | Boss drop-target planner
- [ ] BOSS-019 | OFFEN | Boss Multi-Battle
- [ ] BOSS-020 | OFFEN | Boss Background Battle

## H. Spires

- [ ] SPIRE-001 | OFFEN | All six elemental Spires
- [ ] SPIRE-002 | OFFEN | Normal Spires
- [ ] SPIRE-003 | OFFEN | Hard Spires
- [ ] SPIRE-004 | OFFEN | Key awareness
- [ ] SPIRE-005 | OFFEN | Floor progression
- [ ] SPIRE-006 | OFFEN | Boss-floor handling
- [ ] SPIRE-007 | OFFEN | Auto Climb
- [ ] SPIRE-008 | OFFEN | Multi-Battle
- [ ] SPIRE-009 | OFFEN | Reward claiming

## I. Clan

- [ ] CLAN-001 | OFFEN | Detect/navigate clan
- [ ] CLAN-002 | OFFEN | Clan Activity Quests
- [ ] CLAN-003 | OFFEN | Activity Stars
- [ ] CLAN-004 | OFFEN | Clan Quest Chests
- [ ] CLAN-005 | OFFEN | Sorgott
- [ ] CLAN-006 | OFFEN | Sorgott reward handling
- [ ] CLAN-007 | OFFEN | Sedula
- [ ] CLAN-008 | OFFEN | Sedula difficulty selection
- [ ] CLAN-009 | OFFEN | Sedula personal damage rewards
- [ ] CLAN-010 | OFFEN | Sedula clan-kill rewards
- [ ] CLAN-011 | OFFEN | Clan contributors/reward claims

## J. Events / tournaments

- [ ] EVENT-001 | OFFEN | Detect active events
- [ ] EVENT-002 | OFFEN | Detect active tournaments
- [ ] EVENT-003 | OFFEN | Read objectives/progress
- [ ] EVENT-004 | OFFEN | Event reward claiming
- [ ] EVENT-005 | OFFEN | Tournament reward claiming
- [ ] EVENT-006 | OFFEN | Chase-style event planning
- [ ] EVENT-007 | OFFEN | Save/spend resources around event windows

## K. Invoker management

- [ ] INV-001 | OFFEN | Collection/index inspection
- [ ] INV-002 | OFFEN | Summon Invokers with Stars
- [ ] INV-003 | OFFEN | Detect new/duplicate Invokers
- [ ] INV-004 | OFFEN | Rarity/faction/element/class/tag model
- [ ] INV-005 | OFFEN | Level Invokers with XP Potions
- [ ] INV-006 | OFFEN | Smart Auto Select
- [ ] INV-007 | OFFEN | Ascend Invokers
- [ ] INV-008 | OFFEN | Echo/material selection
- [ ] INV-009 | OFFEN | Awaken Invokers
- [ ] INV-010 | OFFEN | Soul Sign nodes
- [ ] INV-011 | OFFEN | Upgrade Invoker Skills
- [ ] INV-012 | OFFEN | Bind appropriate Titans
- [ ] INV-013 | OFFEN | Equip/optimize Relics
- [ ] INV-014 | OFFEN | Equip/optimize Accessories
- [ ] INV-015 | OFFEN | Dismiss unwanted Invokers
- [ ] INV-016 | OFFEN | Valuable-Invoker protection policy

## L. Titan management

- [ ] TITAN-001 | OFFEN | Summon Titans with Orbs
- [ ] TITAN-002 | OFFEN | Detect duplicates/rarity/faction
- [ ] TITAN-003 | OFFEN | Level Titans
- [ ] TITAN-004 | OFFEN | Ascend Titans
- [ ] TITAN-005 | OFFEN | Dragonsoul/material selection
- [ ] TITAN-006 | OFFEN | Empower Titans
- [ ] TITAN-007 | OFFEN | Titanheart/duplicate policy
- [ ] TITAN-008 | OFFEN | Upgrade Titan Skills/Invokation effects
- [ ] TITAN-009 | OFFEN | Titan binding strategy
- [ ] TITAN-010 | OFFEN | Valuable-Titan protection policy

## M. Relics

- [ ] RELIC-001 | OFFEN | Inventory inspection
- [ ] RELIC-002 | OFFEN | Evaluate rarity/rank/type/stats/set
- [ ] RELIC-003 | OFFEN | Equip / replace
- [ ] RELIC-004 | OFFEN | Auto Equip
- [ ] RELIC-005 | OFFEN | Preview/loadout evaluation
- [ ] RELIC-006 | OFFEN | Upgrade Relics to level 20
- [ ] RELIC-007 | OFFEN | Gold/Memorium budget
- [ ] RELIC-008 | OFFEN | Filter/sort
- [ ] RELIC-009 | OFFEN | Sell Relics
- [ ] RELIC-010 | OFFEN | Crush Relics
- [ ] RELIC-011 | OFFEN | Batch sell/crush
- [ ] RELIC-012 | OFFEN | Battle-result disposal
- [ ] RELIC-013 | OFFEN | Inventory/storage pressure logic
- [ ] RELIC-014 | OFFEN | Valuable-Relic protection policy

## N. Accessories

- [ ] ACC-001 | OFFEN | Inventory inspection
- [ ] ACC-002 | OFFEN | Faction compatibility
- [ ] ACC-003 | OFFEN | Awakening slot rules
- [ ] ACC-004 | OFFEN | Amulets
- [ ] ACC-005 | OFFEN | Earrings
- [ ] ACC-006 | OFFEN | Banners
- [ ] ACC-007 | OFFEN | Talismans
- [ ] ACC-008 | OFFEN | Flasks
- [ ] ACC-009 | OFFEN | Equip / Auto Equip
- [ ] ACC-010 | OFFEN | Upgrade to level 20
- [ ] ACC-011 | OFFEN | Sell
- [ ] ACC-012 | OFFEN | Crush
- [ ] ACC-013 | OFFEN | Valuable-Accessory protection policy

## O. Tactics / skills / account development

- [ ] DEV-001 | OFFEN | Invoker Codex spending policy
- [ ] DEV-002 | OFFEN | Titan Prism spending policy
- [ ] DEV-003 | OFFEN | Tactics inventory
- [ ] DEV-004 | OFFEN | Upgrade Tactics to level 20
- [ ] DEV-005 | OFFEN | Playbook/Gold budget
- [ ] DEV-006 | OFFEN | Development priority planner

## P. Resources

- [ ] RES-001 | OFFEN | Energy
- [ ] RES-002 | OFFEN | Gold
- [ ] RES-003 | OFFEN | Gems
- [ ] RES-004 | OFFEN | Arena Tokens
- [ ] RES-005 | OFFEN | Multi-Battle Tokens
- [ ] RES-006 | OFFEN | Spire Keys
- [ ] RES-007 | OFFEN | XP Potions
- [ ] RES-008 | OFFEN | Memorium
- [ ] RES-009 | OFFEN | Stars / fragments
- [ ] RES-010 | OFFEN | Orbs / fragments
- [ ] RES-011 | OFFEN | Echoes
- [ ] RES-012 | OFFEN | Dragonsouls
- [ ] RES-013 | OFFEN | Codexes
- [ ] RES-014 | OFFEN | Prisms
- [ ] RES-015 | OFFEN | Titan Spark
- [ ] RES-016 | OFFEN | Titanhearts / Elder Titanhearts
- [ ] RES-017 | OFFEN | Astral / Elemental Essences
- [ ] RES-018 | OFFEN | Class Crests
- [ ] RES-019 | OFFEN | Faction Runes
- [ ] RES-020 | OFFEN | Playbooks
- [ ] RES-021 | OFFEN | Event currencies
- [ ] RES-022 | OFFEN | Clan-specific currencies/progress

## Q. Battle intelligence

- [ ] BATTLE-001 | OFFEN | Pre-battle team selection
- [ ] BATTLE-002 | OFFEN | Invoker filtering/sorting
- [ ] BATTLE-003 | OFFEN | Titan binding
- [ ] BATTLE-004 | OFFEN | Tactics selection
- [ ] BATTLE-005 | OFFEN | Auto Mode handling
- [ ] BATTLE-006 | OFFEN | Manual combat fallback
- [ ] BATTLE-007 | OFFEN | Skills
- [ ] BATTLE-008 | OFFEN | Combo attacks
- [ ] BATTLE-009 | OFFEN | Ultimates
- [ ] BATTLE-010 | OFFEN | Titan Invokation
- [ ] BATTLE-011 | OFFEN | Result parsing
- [ ] BATTLE-012 | OFFEN | Battle reports
- [ ] BATTLE-013 | OFFEN | Retry/replay/stop decisions
- [ ] BATTLE-014 | OFFEN | Team-builder / matchup model

## R. Operational quality

- [ ] OPS-001 | IN ENTWICKLUNG | F12 emergency stop
- [ ] OPS-002 | IN ENTWICKLUNG | UNKNOWN means no input
- [ ] OPS-003 | OFFEN | Failure screenshot/log bundle
- [ ] OPS-004 | OFFEN | Metrics: success/failure/recovery rates
- [ ] OPS-005 | OFFEN | Long-run stability test
- [ ] OPS-006 | IN ENTWICKLUNG | CPU/RAM/capture performance targets
- [ ] OPS-010 | TEST AUSSTEHEND | Reactive input pipeline: SendInput + 60 FPS capture + state-driven transition waits
- [ ] OPS-011 | OFFEN | ROI-only transition verification for hot paths
- [ ] OPS-012 | OFFEN | Per-action confidence policy: fast normal actions, stricter irreversible actions
- [ ] OPS-007 | OFFEN | Windows scaling/resolution matrix
- [ ] OPS-008 | OFFEN | Installer/portable launcher later
- [ ] OPS-009 | OFFEN | Safe configuration/version migration

## Final project acceptance

The project is only considered functionally complete when the bot can:
- start from a normal known game state,
- inspect the account,
- discover available useful work,
- choose and execute tasks across multiple domains,
- manage development/resources safely,
- collect rewards,
- recover from expected interruptions,
- continue without human clicks for an extended session,
- avoid destructive mistakes under the configured policies,
- produce logs explaining what it did and why.

This checklist remains open-ended: newly discovered Invokers systems must be appended with stable IDs.
