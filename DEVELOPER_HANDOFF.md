# DEVELOPER HANDOFF

## Current package: ARENA-LIVE-005C — Pre-start authorization + token pressure policy

Status: BEREIT ZUR ENTWICKLUNG

ARENA-LIVE-004A remains blocked on real-client Own Team Power validation.
ARENA-LIVE-005A/005B are code/CI accepted.

## Verified baseline

- 005B commit `4b4ced808b9fb00553c86e81c02dbc46a6467d63`
- Windows CI `43646510502`
- `329 passed, 1 warning in 0.71s`
- immutable ArenaBattleAttemptContext exists
- exact opponent ID correlation exists
- battle start still disabled
- fight authorization still false

## Current official policy facts

Current official Arena documentation states:
- Arena Tokens regenerate +1 per hour
- regeneration stops at 10 Tokens
- extra tokens may come from Playtime Rewards / Gem Shop

Treat 10-cap and +1/hour as versioned/configurable policy defaults, not parser constants.

The exact token cost for one Arena Offense battle is still not verified in current project evidence. Do not guess it.

## Goal

Build the pure pre-start decision layer that can say whether an already-selected Arena opponent is eligible to start, without sending any input.

## Part A — ArenaTokenPolicy

Create a versioned policy object with configurable:
- token_cap default 10
- regeneration_seconds default 3600
- pressure_start configurable
- reserve default 0
- expected_battle_cost nullable
- max_balance_age
- policy_version

Requirements:
- cap/regeneration defaults are policy values
- expected_battle_cost=None => spending BLOCKED
- no Gem refill behavior

## Part B — token pressure

Create deterministic pressure state:
- UNKNOWN
- NORMAL
- HIGH
- AT_CAP

Inputs:
- fresh Arena Token balance
- configured cap
- optional last-change/regeneration timing if actually available

No inferred balance from wall-clock regeneration alone.

Pressure can affect Goal priority but cannot override:
- unknown cost
- stale balance
- reserve
- invalid selected target
- unknown/unvalidated Own Power

## Part C — PreStartAuthorization

Create immutable result with:
- allowed bool
- reason code
- selected opponent id
- candidate fingerprint/version
- own power provenance/version
- token balance
- expected cost
- reserve
- resulting balance
- attempt id if created
- policy version

Reason codes at minimum:
- ALLOW
- BLOCK_OWN_POWER_UNKNOWN
- BLOCK_OWN_POWER_STALE
- BLOCK_TARGET_MISSING
- BLOCK_TARGET_STALE
- BLOCK_ARENA_STALE
- BLOCK_TOKEN_BALANCE_STALE
- BLOCK_TOKEN_COST_UNKNOWN
- BLOCK_INSUFFICIENT_TOKENS
- BLOCK_RESERVE
- BLOCK_ATTEMPT_BASELINE
- BLOCK_POLICY

## Part D — attempt creation

Only when every pre-start gate passes:
- create ArenaBattleAttemptContext from current fresh state
- bind selected opponent ID
- bind current opponent-set fingerprint
- bind exact expected token cost

Still do NOT send input.

If any dependency changes between authorization and future click:
- authorization invalid
- attempt must be recreated/revalidated

## Part E — token semantic verification contract

Prepare the future start-action expectation:
- exact token delta must equal -expected_battle_cost
- unrelated PlayerModel digest change is not sufficient
- visual transition to battle alone is not sufficient for structured spend confirmation
- delayed PlayerModel persistence => PENDING/INCONCLUSIVE, no blind second click

Do not enable the start action.

## Part F — current official behavior note

Document that current official docs say:
- token cap 10
- +1/hour regeneration
- extra tokens can come from rewards/shop

Do not assume token balance can only change by regeneration.
Do not implement automatic Gem purchase/refill.

## Tests

At minimum:
1. cap=10 produces AT_CAP at balance 10
2. balance below cap produces NORMAL/HIGH per config
3. unknown/stale balance -> UNKNOWN
4. unknown battle cost blocks
5. insufficient tokens blocks
6. reserve violation blocks
7. UNKNOWN/unvalidated OwnPower blocks
8. stale candidate/fingerprint blocks
9. fresh exact candidate + exact own power + exact known cost can produce ALLOW object
10. allowed authorization creates immutable attempt context
11. dependency change invalidates previous authorization
12. exact token delta predicate requires exact negative cost
13. delayed token persistence does not authorize retry
14. Gem refill remains absent/blocked
15. battle start config remains disabled
16. existing 329+ suite remains green

## Constraints

- pure policy/decision layer only
- no SendInput
- no battle start enablement
- no Gem spending
- no guessed token cost
- no broad OCR
- no snapshot writes
- BotEngine remains generic

## Completion report

Report:
- commit SHA
- policy defaults/config
- authorization reason codes
- token pressure behavior
- attempt creation rules
- exact spend-verification contract
- full pytest count
- Windows CI result
- remaining live blockers
