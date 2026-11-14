# DEVELOPER HANDOFF

## ARENA-LIVE-006C — Shadow end-to-end Arena run coordinator

Status: BEREIT ZUR ENTWICKLUNG

006B real-client glyph calibration remains BLOCKIERT until the user is back at the Windows client.

Current accepted baseline:
- 006A implementation `d0432a49479578afa0ac7d1847cb0544044c90bf`
- CI fix `f3e0e6d702e155c27d8fad5a6e6b57161ae74efe`
- Windows CI `43650628167`
- `359 passed, 1 warning in 1.31s`
- Arena battle cost 1 token live verified
- victory reconciliation live verified
- battle start remains disabled

## Purpose

Build the pure orchestration layer that joins the existing Arena components into one attempt-scoped state machine without performing any game input.

This should expose integration bugs before enabling a real battle-start action.

Research rationale:
- long-running actions should be stateful and return RUNNING while awaiting evidence, not block on fixed sleeps
- waits should poll explicit conditions and finish as soon as evidence appears
- stale observations must be re-observed/rebound, not blindly reused
- cancellation/halt should terminate the in-flight attempt quickly

## New pure ArenaRunCoordinator

Implement a deterministic coordinator driven only by supplied observations/events.

Suggested phases:
1. IDLE
2. NEED_ARENA_STATE
3. NEED_TRAVERSAL
4. NEED_OWN_POWER
5. NEED_RANKING
6. NEED_AUTHORIZATION
7. PREPARED
8. START_OBSERVED
9. BATTLE_RUNNING
10. RESULT_PENDING
11. TERMINAL
12. BLOCKED
13. CANCELLED

Exact naming may vary, but semantics must remain explicit and testable.

## Inputs

Coordinator may consume:
- fresh AccountState
- arena traversal inventory
- OwnPower
- Ranking / selected Candidate
- PreStartAuthorization
- externally observed visual state
- token spend observation
- AttemptObservation / result reconciliation evidence
- cancellation signal
- monotonic time

It must NOT:
- capture the screen itself
- parse raw files itself
- call SendInput
- click buttons
- construct guessed coordinates

## Attempt ownership

Once PREPARED:
- freeze the selected Player-ID and immutable ArenaBattleAttemptContext
- later opponent-list refresh cannot replace the attempt opponent
- a new attempt cannot start until previous attempt is terminal/cancelled
- wrong attempt-id observations are rejected
- duplicate terminal observations return the existing terminal result

## Pre-start invalidation

Before START_OBSERVED, any of these returns to a safe replan/block state:
- opponent fingerprint changed
- selected candidate changed
- OwnPower became stale/unknown
- token/player source changed
- authorization expired
- policy version changed
- Arena source stale
- cancellation

Never auto-recreate and immediately spend in the same tick after invalidation.

## Start transaction contract

Do not enable actual input.

Create a pure `StartIntent` / equivalent only when authorization is valid.

It should contain:
- attempt id
- opponent id
- expected token cost = 1
- expected visual transition to battle
- exact resource delta predicate Arena Token -1
- authorization digest/provenance
- created_at / deadline

The coordinator can accept an externally supplied `START_OBSERVED` event later.

Rules:
- visual battle alone => start PENDING
- exact token -1 alone => start PENDING
- both compatible => START_CONFIRMED / BATTLE_RUNNING
- mismatched resource delta => CONFLICTED/BLOCKED
- timeout => INCONCLUSIVE/BLOCKED
- retry_allowed=false

## Battle/result flow

After start confirmation:
- preserve attempt context
- consume result observations using existing AttemptReconciliation
- WIN_CONFIRMED becomes terminal success
- LOSS_CONFIRMED supported synthetically but clearly marked not live-validated
- BATTLE_COMPLETED_RESULT_UNKNOWN remains pending until timeout
- CONFLICTED becomes terminal blocked/failure
- timeout becomes terminal inconclusive
- no replay

## Synthetic loss contract

Add a sanitized synthetic loss fixture:
- token 12 -> 11
- total offense battles +1
- total offense wins +0
- weekly offense battles +1
- weekly offense wins +0
- selected FinishedOpponent exact ID if compatible with existing semantics
- visual defeat
Expected: LOSS_CONFIRMED under current reconciliation rules.

Document clearly: this validates code behavior only; real loss persistence still requires later live capture.

## Recovery/cancellation

Coordinator must:
- cancel immediately from any non-terminal phase
- never emit a second StartIntent after cancellation
- never blind-retry a start
- require fresh re-observation/replanning after BLOCKED/INCONCLUSIVE
- expose a machine-readable reason and small trace of phase transitions
- keep trace metadata-only, no screenshots/raw snapshots

## Shadow scenario tests

At minimum:
1. happy-path synthetic victory end-to-end
2. synthetic loss end-to-end
3. stale Arena before authorization -> blocked/replan
4. target fingerprint changes before start -> invalidate
5. target refresh after start does not replace opponent identity
6. OwnPower stale before start -> blocked
7. token source changes before start -> invalidate
8. exact token -1 + battle visual confirms start
9. battle visual without token persistence remains pending
10. token -1 without battle visual remains pending
11. wrong token delta conflicts
12. timeout never retries
13. cancellation in PREPARED
14. cancellation in BATTLE_RUNNING
15. wrong attempt ID rejected
16. duplicate terminal observation is idempotent
17. one coordinator cannot own two active attempts
18. no SendInput/action executor dependency
19. no raw snapshots/screenshots persisted
20. existing 359+ suite green

## Architecture constraints

Keep BotEngine generic.
Coordinator must be pure/domain-level.
Do not add fixed sleeps.
Use monotonic deadlines and explicit condition polling.
No battle-start activation.
No Gem refresh.
No replay.
No broad OCR.
006B calibration remains separate.

## Completion report

Report:
- commit SHA
- coordinator phases
- StartIntent schema
- invalidation/recovery rules
- synthetic victory/loss behavior
- cancellation semantics
- pytest count
- Windows CI run/result
- confirmation that no input path was enabled
