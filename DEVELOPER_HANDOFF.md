# DEVELOPER HANDOFF

## Current package: ARENA-LIVE-004 — Own Team Power validation + first opponent ranking

Status: BEREIT ZUR ENTWICKLUNG

Read first:
- PROJECT_WORKFLOW.md
- MASTER_STATUS.md
- MASTER_CHECKLIST.md
- TEST_RESULTS.md
- ARENA_MEMORYPACK_MAP_0.62.1621.md
- ARENA_GOAL_POLICY.md
- ARENA_REFRESH_POWER_SCORING_PLAN.md
- ARENA_OWN_POWER_SOURCE_ANALYSIS.md
- current arena_model.py / arena_opponent.py / arena_refresh.py / transition_probe.py

## Verified baseline

ARENA-LIVE-003 is accepted:
- final commit: `bca993439fae721158939b22f2e92559c39e6ffc`
- Windows CI run: `43645342539`
- result: `289 passed, 1 warning in 0.99s`
- opponent identity = 16-byte Player-ID
- exact opponent CombatPower is structured
- opponent-set fingerprint is order-independent
- semantic refresh invalidation exists
- own-power A/B/C passive probe exists

## Goal

Resolve the user's own Arena Team Power provenance and build the first deterministic opponent ranking policy.

Do not start battles automatically yet.

## Part A — own Team Power live validation path

Preferred source:
`PlayerBattleModel.LastMetaBattleSetup -> PlayerTeamSetup -> CombatPower`

Implement only if the nested MemoryPack path can be verified from IL2CPP/schema evidence.

If schema is not yet sufficiently verified:
- keep the passive A/B/C probe
- add a tiny numeric ROI fallback interface for manual/live validation only
- do not use broad OCR
- do not invent offsets

Required live experiment:
A. Arena list
B. click Fight on one opponent, reach formation
C. back out without starting battle

Record:
- BattleModel digest/version A/B/C
- ArenaModel digest/version A/B/C
- LastMetaBattleSetup null/non-null
- structured own CombatPower if available
- visible UI Team Power for comparison
- whether B -> C preserves or clears setup

## Part B — own-power provenance model

Represent own power with provenance:
- STRUCTURED_LAST_META_BATTLE_SETUP
- EXACT_LOCAL_CALCULATOR
- PREBATTLE_NUMERIC_ROI
- UNKNOWN

Every value must carry:
- numeric value
- source/provenance
- observed_at
- source digest/version if structured
- confidence / exactness flag

Approximate values are not allowed for autonomous matchup decisions.

## Part C — first opponent ranking policy

Use only verified fields:
- opponent CombatPower
- own Team Power
- opponent ArenaPoints
- optional previous result only if already verified

Initial deterministic rank components:
- power_ratio = opponent_power / own_power
- ArenaPoints as bounded secondary signal
- stable tie-break by Player-ID

Do NOT hardcode a “win guaranteed below X%” rule.

Config should support:
- max_power_ratio
- prefer_lower_power
- prefer_higher/lower ArenaPoints policy if desired
- minimum acceptable candidates

If own power is UNKNOWN:
- ranking may be diagnostic only
- no target may be authorized for autonomous fight start

## Part D — target selection object

Produce a structured selected-opponent candidate containing:
- Player-ID
- name
- level
- ArenaPoints
- CombatPower
- own power
- power ratio
- rank components
- arena source fingerprint/version
- scoring policy version

Selection becomes invalid immediately when:
- opponent-set fingerprint changes
- own-power provenance/version changes
- Arena source becomes stale
- scoring policy changes

## Part E — visual navigation contract

Do not assume structured opponent order equals visible order.

Prepare a target-location contract:
- selected opponent identity is semantic
- visual traversal locates/validates the corresponding card later
- no cached coordinate survives Arena refresh

No automatic click-to-fight in this package unless explicitly running the manual own-power probe.

## Tests

At minimum:
1. own power structured provenance object
2. unknown own power blocks autonomous ranking authorization
3. exact own power allows deterministic ranking
4. lower power_ratio ranks ahead under configured policy
5. tie-break deterministic by Player-ID
6. ArenaPoints secondary component bounded
7. candidate invalidated on opponent-set fingerprint change
8. candidate invalidated on own-power source/version change
9. stale Arena source blocks selection
10. no battle-start action authorized
11. passive probe never presses Start Battle
12. existing 289+ suite remains green

## Completion

Run full pytest, push to main, verify Windows CI and report:
- commit SHA
- total tests
- Actions run/result
- own-power source status
- ranking formula/config
- candidate invalidation rules
- remaining live-client requirements
