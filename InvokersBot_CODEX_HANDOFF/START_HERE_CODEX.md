> Current scope: Arena Integration Sprint 01. Follow research/MASTER_STATUS.md
> and docs/ARENA_SPRINT_01.md. Earlier D1 assignments below are historical context;
> do not expand GUI/release work or unrelated reverse engineering for this sprint.

# Invokers Bot — Codex Handoff

## Read this first
This directory is the canonical handoff from the prior ChatGPT development session for an autonomous Windows bot / structured-state reader for **Invokers: Titan Legacy**.

Before changing code, read in this order:
1. `research/MASTER_STATUS.md` — source of truth for project status and priorities.
2. `research/RESEARCH_FINDINGS.md` — reverse-engineering findings.
3. `src/state_reader.py` — current D1 structured state work.
4. `src/arena_snapshot.py` and `src/arena_actor.py` — current Arena reader/navigation.
5. `tests/test_state_reader.py` and `tests/test_arena_priority.py`.

Do **not** create a new version/ZIP after every small fix. Work in substantial milestones, run regression tests, update `research/MASTER_STATUS.md`, and only produce a consolidated build when a meaningful milestone is complete.

## Immediate assignment: finish D1 GameState
Continue autonomously until a useful test boundary. Do not stop for routine confirmation.

Target pipeline:
`LIVE SNAPSHOTS + STATIC DATA + DUMP SCHEMAS -> READERS -> GameState -> PLANNER -> ACTOR`

D1 completion goals:
- robustly decode `PlayerModel.Resources`, `ResourcesGained`, `ResourcesSpent`;
- robustly decode `PlayerBattleModel.LevelStats` and derive campaign safe/highest/failed progression;
- decode Arena attack preset / formation and determine whether own CombatPower can be obtained from snapshot data (prefer data over OCR);
- decode useful `PlayerGlobalEventsModel` tournament participation fields;
- combine all validated readers into one typed/structured `GameState`;
- add regression tests against `tests/fixtures/*.dat`;
- keep unknown/unproven fields explicitly unknown rather than guessing;
- update `research/MASTER_STATUS.md` with evidence and test status.

## Confirmed facts from real fixtures
- MemoryPack / IL2CPP schemas are available in `raw/dumps/` and schema catalogs in `research/`.
- `PlayerArenaModel.dat` currently exposes 27 opponent records. Exact combat powers observed include Vinescia98=2522, ArchieA=2555, xKrollx=2587, Cre4t1ve=2641, pikx7=2656, BloodAxe=7172, Ellesher=11141.
- Arena UI must select the weakest valid snapshot candidate, not the first visible snapshot name. A regression test covers the prior bug where visible Ellesher was selected instead of Vinescia98.
- `PlayerModel.Resources.RawValues` is `ResourceTypeId -> Int32`. Confirmed IDs: Gem=1, Gold=2, Energy=3, Memorium=4, Arena_Token=21, Arena_Coin=22, SI_WildStar=101.
- A real snapshot decoded current values including Gems=310, Gold=631640, Energy=1362, Memorium=6815, MultiBattle token=20, ClanBoss key=1, Arena tokens=12, Arena coins=6650, WildStars=37. Revalidate from fixtures rather than hard-coding these values.
- `PlayerBattleModel.LevelStats` is usable. In the captured fixture Normal campaign Chapter 7 levels 1-5 are wins; Chapter 7 Level 6 has 0 victories and 2 defeats. Planner rule: first campaign defeat stops blind pushing; remember/use safe won level.
- `LevelProgressionIdentifier` is sequential 16 bytes: AreaId, RegionId, Difficulty, Number.
- `AsyncPvpPreset` / TeamPreset structures contain formation slots with HeroInventoryId and HeroConfigId.
- `BattlePlayerTeamSetup.CombatPower` exists in the dumped schema and should be investigated as the preferred source for own power.
- `PlayerGlobalEventsModel` fixture contains 6 tournament dictionary entries; observed keys 935, 939, 991, 1000, 1006, 1007. Participation payload fields are not yet fully proven.

## Non-negotiable bot policy
- Main team: first 6 Invokers in UI list are the primary team and should be developed first.
- Campaign: push highest available until FIRST defeat, then stop; do not retry forever. Specific quest targets may override generic farming.
- Quest priority: Daily > current Progress quests > Weekly > Monthly occasionally > Achievements mostly passive/claim.
- Exploit overlap/synergy between objectives while keeping the current priority category primary.
- Quest reward click only when the UI text explicitly says `ANNEHMEN`; never click ordinary reward icons.
- Hero standard leveling: `Automatische Auswahl` then `Leveln` when appropriate.
- Summoning automation: green `Stern der Wildnis` only.
- Send-away: grey/green only; blue+ forbidden; keep at least 30 Invokers.
- Gems/premium purchases: NEVER automatic.
- Relics: protect equipped/high-value/important; only sell/upgrade after value/resource decoding is reliable.
- Defeat handling: remember failures and avoid loops.
- Profile rewards: periodic/level-up check; only actual active `Annehmen`.

## Engineering rules
- Data precedence: game files / structured state > static game data / dump schema > explicit project rules > targeted UI state > OCR heuristic.
- OCR is fallback/navigation, not the game brain.
- Avoid full-screen OCR in loops. Use small ROIs and event/state-change verification.
- Actor should follow: `OBSERVE -> PLAN -> VERIFY PRECONDITION -> ACT -> WAIT FOR STATE CHANGE -> VERIFY RESULT -> UPDATE MEMORY -> REPLAN`.
- Separate pure decision/navigation logic from PyAutoGUI so it can be unit tested headlessly.
- F8 / mouse-corner emergency stop must remain.
- Never infer a successful action only because a click occurred. Verify state transition.

## PC paths used by the user
Game launcher/data context:
- `%APPDATA%\\zone.hitzone.invokers.launcher`
- `%USERPROFILE%\\AppData\\LocalLow\\Hit_Zone\\Invokers`
- snapshots under `aggregate_snapshots\\`

## Included data
- `tests/fixtures/`: captured live Player*.dat snapshots for reproducible tests.
- `raw/dumps/InvokersDump(2).zip`: C# / IL2CPP dump material.
- `raw/dumps/InvokersIL(1).zip`: IL material.
- `raw/static/static-data.0.62.1655(1).dat`, `catalog.bin`, `de_DE.bin.br`: static/localization material available from prior analysis.
- `reference/screenshots/`: selected Arena UI screenshots only, not the full screenshot archive.

## Deliberately not included
- dozens of obsolete V1-V9 intermediate ZIPs;
- `GameAssembly.dll` (~96 MB), because the supplied dump/IL outputs are the primary analysis input. If a new native-level question requires it, ask the user to add the original DLL.
- manipulated hero test files not needed for D1; they can be added later if a hero-specific regression requires them.

## Working style requested by user
Work for longer stretches. Critically evaluate decisions and research relevant official/current approaches when useful. Do not repeatedly ask for confirmation. Ask only if a required file/fact is missing, a consequential irreversible choice needs approval, or a real on-PC test is necessary.
