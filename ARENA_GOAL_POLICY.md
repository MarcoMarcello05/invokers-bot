# ARENA GOAL POLICY

Date: 2026-11-14

Purpose: define the first live Arena Goal logic without pretending that opponent scoring or Arena parser support already exists in runtime.

## Current live inputs available

Implemented:
- PlayerModel.Resources
- Arena_Token resource id 21
- visual Arena states/navigation
- action-scoped verification
- semantic resource predicate work is assigned in LIVE-001B

Not yet live:
- PlayerArenaModel parser in AccountState
- structured opponent list
- opponent scoring
- Arena points/stats
- exact token cap
- exact token regeneration interval
- measured PlayerModel save latency

Therefore the first Arena Goal must be intentionally narrow.

## Initial Goal: ArenaOpportunity

This is NOT yet "fight best opponent".

It means:
"The account is eligible to enter Arena work because fresh token state and navigation capability exist."

Generate candidate only if:
- live AccountState exists
- PlayerModel source is fresh
- Arena_Token resource exists
- token balance > configured minimum_to_play
- Arena navigation capability is enabled
- no Arena circuit breaker
- current risk/resource policy allows spending

Blocked reasons:
- NO_ACCOUNT_STATE
- PLAYER_STALE
- ARENA_TOKEN_MISSING
- BELOW_TOKEN_THRESHOLD
- NAV_CAPABILITY_MISSING
- CIRCUIT_OPEN
- RESOURCE_POLICY_DENIED

## Token threshold

Use config, not game assumptions.

Suggested fields:

arena:
  token_policy:
    minimum_to_play: 1
    reserve: 0
    cap: null
    pressure_start: null

`minimum_to_play: 1` represents the Goal policy threshold, not proof of actual battle cost.

If the battle cost is later verified as one token, ResourcePlanner can use exact-cost verification.

## Initial score components

Until PlayerArenaModel is live, keep score simple and explainable:

BaseArenaPriority
+ TokenAvailability
+ OverflowPressure if cap known
+ QuestSynergy if quest layer later confirms Arena objective
+ EventSynergy if event layer later confirms Arena objective
+ StarvationAgeBoost
- NavigationCost
- RecentFailurePenalty

Do NOT score:
- opponent difficulty
- points gain
- win probability
until structured Arena/opponent data exists.

## TokenAvailability component

Should answer:
"Can Arena work be done now?"

Recommended:
- below threshold -> ineligible
- at/above threshold -> bounded positive value
- avoid making raw token count linearly dominate score

## OverflowPressure component

Only active when cap is known.

If cap unknown:
- component = 0
- add diagnostic: CAP_UNKNOWN
- do not block ordinary Arena opportunity solely because cap is unknown

## Quest/Event synergy

Later layers may attach bounded bonuses.

Example:
Daily quest requires Arena wins.

Do not create a separate "do quest Arena" execution loop.
The existing Arena Goal receives synergy.

## Opponent readiness gate

Before actual battle-start capability is enabled in autonomous planner:

Either:
- a validated opponent-selection Skill exists
OR
- a safe deterministic existing flow is explicitly configured for a known test setup

Until then the planner may navigate to Arena but should not claim it can choose the best opponent.

## Battle start verification

Current config:
- visual expected state = battle
- player source expected to change
- timeout = 5s

This remains provisional.

The correct semantic predicate should become:

Arena_Token after < Arena_Token before

and preferably exact delta once battle cost is verified.

However:
- visual battle transition can happen before snapshot persistence
- structured persistence latency must be measured

Recommended future staged result:

STEP 1:
visual transition confirms battle start UI

STEP 2:
structured reconciliation confirms token spend within configurable save grace

For autonomous retry safety:
- if STEP 1 succeeds and STEP 2 is delayed, status should be INCONCLUSIVE/PENDING_RECONCILIATION, not retry battle start

## Arena circuit breaker

Track:
- navigation failures
- battle-start verification failures
- structured reconciliation timeouts

Suggested policy:
- bounded immediate retries at Skill level
- repeated same failure opens Arena circuit
- circuit prevents Scheduler from reselecting Arena for a cooldown window or until relevant state changes

Do not endlessly fight the same broken template/state.

## Future PlayerArenaModel integration

Once live parser exists, upgrade Goal inputs:

- points
- opponents
- finished opponents
- current battle opponent
- LastOpponentsRefreshTime
- HallBonuses
- Stats

Then split Arena work into:
- ArenaOpportunity
- RefreshOpponents
- FightBestAcceptableOpponent

## Future opponent scoring

Candidate opponent score should be a separate policy.

Possible inputs:
- opponent Arena points
- account level
- team composition
- prior result
- own team estimate
- quest/event bonus
- refresh opportunity cost

Hard gates:
- opponent data fresh
- team data fresh
- no unresolved source/UI conflict

Do not use OCR to rebuild structured opponent data once PlayerArenaModel is available.

## Acceptance examples

A. fresh PlayerModel, token balance 0, minimum_to_play 1
=> ArenaOpportunity ineligible.

B. fresh PlayerModel, token balance 3, threshold 1, no cap known
=> eligible; overflow component zero; diagnostic CAP_UNKNOWN.

C. PlayerModel awaiting_change
=> blocked PLAYER_STALE.

D. Arena token key missing
=> blocked ARENA_TOKEN_MISSING.

E. tokens available but Arena circuit open
=> blocked CIRCUIT_OPEN.

F. tokens available and daily Arena quest later applies
=> same Arena Goal gains QuestSynergy; no duplicate execution goal.

G. visual battle starts but token snapshot has not persisted yet
=> do not click Start again; reconcile first.
