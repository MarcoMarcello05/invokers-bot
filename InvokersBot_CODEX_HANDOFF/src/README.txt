INVOKERS v9 - AUTONOMOUS READY FOUNDATION

Status: prepared for autonomous play, but ships in DRY_RUN with actor_enabled=false.
This is deliberate: the data brain is live; destructive/currency actions remain locked until their value/cost readers are validated.

Run START_DRY_RUN.cmd. It continuously writes runtime\action_plan.json from live snapshots.
Safety: gems/premium blocked; WildStar allowed; equipped relics protected; campaign must stop after first defeat; min hero count 30.

Prepared execution paths:
- Quest LOS navigation for safe quest actions
- Campaign push job with stop-on-first-defeat semantics
- Main-six development job
- Persistent failure-memory schema
- State-confirmation plan file

Still calibration-gated before switching actor_enabled=true:
1) PlayerModel resource balances/cost confirmation
2) relic bonus/value parser before selling/upgrading
3) exact screen navigation calibration for Arena/Dungeon/Main-team list from planner jobs
4) end-to-end dry-run log on Marco's PC

v9 executable planner update
----------------------------
The bridge now separates abstract planning from executable actor commands.
Meta actions such as QuestUpgradeProgress and QuestComplete can add context/priority but are NEVER executable.
runtime/action_plan.json contains:
- queue: reasoning/account-development jobs
- executable_queue: only concrete safe actor commands
- next_executable: command selected for the actor
Concrete command examples: ARENA_BATTLE, CAMPAIGN_BATTLE, DUNGEON_BATTLE, CLAN_BOSS_BATTLE, SUMMON_WILDSTAR, HERO_LEVEL, HERO_AWAKE, HERO_ASCEND, CAMPAIGN_PUSH, MAIN_TEAM_LEVEL.
Inventory spending/selling/destruction and ShopPurchase remain locked.

=== ARENA ACTOR v9 ===
START_ARENA_DRY_RUN.cmd: liest Arena, klickt NICHTS. Erwartete Ausgabe WOULD_ATTACK oder WOULD_REFRESH.
START_ARENA_LIVE.cmd: Arena-only Live-Test. Regeln: eigene Kampfkraft muss erkannt sein; nur Gegner darunter; niedrigste Kampfkraft zuerst; wenn keiner vorhanden max. 3x AKTUALISIEREN; danach SAFE_STOP. OCR unsicher/Screen unbestätigt => kein Angriff.
Hinweis: Die vollständige Navigation vom Planner in die Arena wird erst nach erfolgreicher Arena-Dry-Run-Kalibrierung freigeschaltet.

=== ARENA V3 ===
Gegner-Kampfkraft wird NICHT mehr per OCR gelesen.
PlayerArenaModel.dat liefert Name/Level/Arena-Punkte/CombatPower.
OCR identifiziert nur sichtbare Gegnernamen und Buttons.
START_ARENA_DRY_RUN.cmd muss zuerst getestet werden.
Erwartung auf Marcos Testscreen: BloodAxe / combat_power 7172.
LIVE erst nach erfolgreichem Dry-Run verwenden.
Nach Aktualisieren wartet der Actor auf eine echte Aenderung von PlayerArenaModel.dat.

V4 ARENA DATA + SCROLL
- PlayerArenaModel.dat is authoritative for opponent name/power/points.
- UI OCR is only used to locate opponent names and confirm own formation power.
- Searches scrollable list current->down->up with stable-end detection.
- Candidate order is exact CombatPower ascending; losses/session rejects are skipped.
- If no candidate can be located, LIVE may refresh at most 3 times and waits for snapshot signature change.
- DRY_RUN may scroll the opponent list but never presses Fight or Refresh.
- Gems/premium/shop/relic destructive actions remain disabled elsewhere.
