# Invokers Autonomous Bot — Master Status
Updated: 2026-11-12

## Source of truth
This file controls project direction. Do not create release ZIPs for isolated fixes. Work in consolidated milestones.

## Non-negotiable policy
- Data/state first: live snapshots > static data/dump > UIA if exposed > small screen regions/templates > OCR fallback.
- Gems/premium purchases: NEVER automatic.
- Wild Star automatic summon: allowed.
- Send away only grey/green, keep >=30 Invokers.
- First six UI Invokers are main team and get development priority.
- Campaign push stops after first defeat; remember safe highest win.
- Daily > Progress > Weekly > occasional Monthly > passive Achievements.
- Avoid repeated failed actions / infinite retries.
- Quest rewards only actual ANNEHMEN button; never reward icon guessing.

## Current milestone D1 — unified structured GameState
### DONE / validated against real snapshots
- [x] PlayerArenaModel opponent extraction: 27 opponents + exact CombatPower.
- [x] Arena candidate ordering from data.
- [x] Arena UI target-priority bug fixed in working tree: visible unrelated opponent cannot replace selected weakest target.
- [x] PlayerModel Resources current dictionary decoded structurally.
- [x] PlayerModel ResourcesGained decoded structurally.
- [x] PlayerModel ResourcesSpent decoded structurally.
- [x] Resource accounting invariant validated: gained - spent == current for Gold/Energy/Memorium/ArenaToken/WildStar; Gems have no spent entry and gained == current.
- [x] ResourceTypeId enum extracted from dump.
- [x] PlayerBattleModel LevelProgressionIdentifier recognized as 16-byte sequential key.
- [x] LevelStats primitive fields decoded: victories, defeats, best time.
- [x] Campaign Normal state proven: Chapter 7-5 won; Chapter 7-6 has 0 wins / 2 defeats.
- [x] Campaign planner implication: safe level 7-5, do not blindly retry 7-6.
- [x] GlobalEvents tournament dictionary count observed: 6; candidate keys isolated: 935,939,991,1000,1006,1007.

### IN PROGRESS
- [ ] Decode TeamPresetData / AsyncPvpPreset into hero inventory IDs.
- [ ] Determine reliable own Arena CombatPower source. Current stored snapshots do NOT contain literal 9368; test whether formation-screen state updates a snapshot before battle. Until proven, tiny OCR ROI remains fallback.
- [ ] Decode GlobalEvents TournamentParticipationState fields and map tournament IDs to static definitions/names.
- [ ] Add hero/quest/relic readers to unified GameState object.
- [ ] Add confidence/provenance per field (structured / inferred / OCR).

### NEXT after D1
- [ ] D2 Planner consumes only GameState, not raw UI/OCR.
- [ ] Resource budgets + hard premium safety gates.
- [ ] Campaign progression policy using LevelStats.
- [ ] Arena policy using exact opponent data and own power source.
- [ ] Event-aware priority modifiers.
- [ ] Main-six development policy.
- [ ] Relic value model only after bonuses/costs are decoded.

## Release gate
No new ZIP until:
1. D1 GameState combines resources + campaign + arena + quests/heroes + event basics.
2. Automated offline tests pass against saved real snapshots.
3. Arena target navigation regression test passes.
4. Premium/gem safety tests pass.
5. One concise PC test can validate multiple improvements at once.
