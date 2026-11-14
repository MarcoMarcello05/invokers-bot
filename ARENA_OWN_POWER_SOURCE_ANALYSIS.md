# ARENA OWN COMBAT POWER SOURCE ANALYSIS

Date: 2026-11-14

## User-confirmed UI behavior

- Arena opponent list shows all available opponents and their displayed team strength.
- The opponent list is vertically scrollable.
- Pressing Fight opens the pre-battle / formation screen.
- The user's own currently selected team's Team Power is visible on the pre-battle screen.

## External documentation

Official Invokers Arena documentation confirms that the Offense list shows:
- enemy Invokers and Titans
- their levels
- total Team Power

Official pre-battle documentation/screenshots show a Team Power value for the selected own lineup before entering battle.

The official Arena documentation describes Team Power as a general overall-strength indicator influenced by Invoker level, relics, awakening and related progression. It is not a guaranteed win predictor.

Official Arena mechanics currently state:
- Arena Token cap: 10
- regeneration: 1 token/hour
- free refresh every 15 minutes
- instant refresh can cost Gems

These current web facts should be version-tagged and not silently treated as immutable game constants.

## Structured-data findings

### Opponent power

Historical project validation already extracted opponent names and exact CombatPower from PlayerArenaModel for real snapshots.

Therefore opponent strength should be sourced from structured Arena data, not OCR, once the nested ArenaOpponent/TeamSetup parser is restored/verified in the clean architecture.

### Own power candidate 1: PlayerBattleModel.LastMetaBattleSetup

IL2CPP analysis has already validated:

PlayerBattleModel.LastMetaBattleSetup
 -> MetaBattleSetup.PlayerTeamSetup
 -> BattlePlayerTeamSetup.CombatPower

This is the strongest direct structured candidate.

Current supplied clean snapshot had LastMetaBattleSetup = null, so it does NOT prove that the value is available before entering the formation screen.

Required live validation:
compare PlayerBattleModel immediately before and after opening an Arena opponent's formation screen.

Question to answer:
Does LastMetaBattleSetup become non-null and expose the same Team Power shown by the UI before the actual battle starts?

If yes:
- preferred own-power source is structured BattlePlayerTeamSetup.CombatPower
- no OCR required
- pressing Fight may be necessary only to materialize the pre-battle setup

### Own power candidate 2: compute from selected preset + account models

IL2CPP exposes HeroExtensions.GetHeroPower with inputs including:
- CompositeStaticData
- PlayerHero
- PlayerRelicsModel
- PlayerAccessoriesModel
- PlayerArenaModel
- optional FormationType / formation level / slot position

This proves the client has enough structured inputs to calculate per-Hero Arena-aware power.

PlayerBattleModel.AsyncPvpPreset also exists and TeamPresetSlot includes HeroInventoryId/HeroConfigId and Anima IDs.

In principle, own Team Power may therefore be reproducible without entering formation by:
1. decode AsyncPvpPreset
2. map selected hero IDs to PlayerHeroesModel
3. join equipped Relics
4. join Accessories
5. join PlayerArenaModel hall bonuses
6. apply formation information
7. reproduce the game's CharacterPowerCalculator / team aggregation

However this is NOT implementation-ready yet because:
- PlayerAccessory inner schema is not byte-verified in the clean project
- exact team aggregation/rounding has not been independently reproduced
- Titan/Anima contribution to displayed Team Power must be confirmed
- formation/tactic bonuses and Arena modifiers must be reproduced exactly

Therefore do not use a home-grown approximation for autonomous opponent decisions.

### Own power candidate 3: pre-battle Team Power ROI

If candidate 1 does not persist structured CombatPower and candidate 2 is not yet exact, use a very small OCR/number-recognition ROI on the pre-battle Team Power display.

This is acceptable as a fallback because:
- it is one stable numeric field
- it is visible before resource spend
- the Fight button only opens formation and does not itself start the Arena battle
- no token should be spent until the final Start Battle confirmation

This fallback must be verified against screenshot/template state and should not expand into broad-screen OCR.

## Recommended decision hierarchy

1. PlayerBattleModel.LastMetaBattleSetup.PlayerTeamSetup.CombatPower if live test confirms it.
2. Exact locally reproduced Team Power only after formula parity is proven against several real UI values.
3. Tiny pre-battle Team Power OCR/number ROI.
4. Never guess own power from Account Level or sum of visible opponent-style card values.

## Arena selection flow

Preferred future flow:

1. read PlayerArenaModel opponent list
2. collect/parse all opponents, independent of current viewport
3. obtain exact opponent CombatPower values
4. obtain own Team Power
   - cached structured value if known current
   - otherwise open one candidate's Fight/formation screen to materialize/read own power
5. return/back if necessary without starting battle
6. rank candidates
7. navigate/scroll to chosen opponent
8. open formation
9. verify selected opponent identity and own team
10. optionally adjust team
11. final pre-spend safety gate
12. press Start Battle
13. verify Arena Token delta and battle transition

Important:
Opening Fight/formation is an R1 reversible observation/navigation action.
Starting the battle is R2 and must remain separately gated.

## Minimal real-client experiment needed

Capture snapshots at three points:

A. Arena opponent list before selecting an opponent
B. after pressing Fight and reaching the formation screen
C. after backing out to Arena without starting the battle

For each point preserve/check:
- PlayerBattleModel.dat
- PlayerArenaModel.dat
- PlayerHeroesModel.dat
- PlayerRelicsModel.dat
- PlayerAccessoriesModel.dat if present

Also record the own Team Power number visible on the formation screen.

Primary comparison:
- Does PlayerBattleModel change from A -> B?
- Does LastMetaBattleSetup become non-null?
- If yes, does PlayerTeamSetup.CombatPower equal the UI number?
- Does backing out B -> C preserve or clear the setup?

Secondary:
- Does AsyncPvpPreset change on opening formation or only when lineup is edited?

No battle needs to be started for this experiment.

## Implementation implication

Do not require broad opponent-list OCR.

Opponent power:
structured PlayerArenaModel.

Own power:
structured if LastMetaBattleSetup validation succeeds; otherwise pre-battle tiny ROI fallback until exact calculator parity is proven.

This keeps the bot data-first while allowing Arena completion without waiting for every equipment formula.

## Live result 006A

User/ANALYSER measured formation 9368 vs victory 9425. LastMetaBattleSetup remained null through post/return. Narrow formation ROI profile is the chosen fallback; no structured own-power field established. Reference normalized ROI is approximate desktop geometry, not yet confirmed client calibration. Local glyph assets and repeated parity checks remain required.
