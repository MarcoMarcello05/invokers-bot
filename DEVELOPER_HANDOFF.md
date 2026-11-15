# DEVELOPER HANDOFF

## ARENA-LIVE-006C1 — post-StartIntent attempt hardening

Status: BEREIT ZUR ENTWICKLUNG

Baseline:
- 006C commit `d3a1bf33e2074d534e132dd3dcb4da30f06df3dc`
- Windows CI `43652958684`
- `376 passed, 1 warning in 1.35s`

## Confirmed review defect

Current 006C incorrectly assumes battle visual + exact token balance delta -1 will both be observable inside the 5s start window.

Live evidence only proves:
- PRE balance 12
- result-screen POST balance 11
- ResourcesSpent[Arena_Token] increased by exactly +1
- exact persistence time after click is NOT measured.

Current synthetic end-to-end test passes POST account state to observe_start, so it does not model the real PRE -> running battle -> POST ordering.

If token persistence is delayed beyond 5s, current coordinator enters BLOCKED. Because BLOCKED is a STOP phase, later result observations are discarded. This can orphan a real in-flight battle.

## Required behavior change

### 1. Distinguish pre-input block from post-intent unresolved attempt

Once a StartIntent exists, do NOT use ordinary BLOCKED semantics for ambiguous start evidence.

Invariant:
**After StartIntent creation, the attempt remains owned until a TerminalRecord or explicit cancellation/recovery record closes it.**

No new attempt may be prepared while unresolved.

### 2. Visual battle evidence may establish non-terminal running state

If an attempt-bound battle visual is observed:
- transition to BATTLE_RUNNING or equivalent
- record spend confirmation separately, e.g. spend_confirmed=False
- retry_allowed remains false
- do not emit another StartIntent

Visual evidence is NOT sufficient for WIN/LOSS confirmation; it only prevents discarding a real running battle.

### 3. Start timeout becomes soft after credible start evidence

If no evidence at all arrives by start deadline:
- do not silently free/reuse the attempt
- produce a machine-readable unresolved/inconclusive state that still owns the attempt until reconciliation/recovery closes it.

If battle visual has already been seen:
- start deadline must NOT terminate observation
- continue waiting for result up to result deadline.

Wrong resource delta remains immediate conflict.

### 4. Result confirmation must require exact Arena token spend evidence

For current policy cost=1, WIN_CONFIRMED / LOSS_CONFIRMED must require exact spend corroboration.

Prefer monotonic PlayerModel `resources_spent[21]` delta +1 from attempt baseline.
Balance delta 12->11 remains supporting evidence but must not be the only spend channel because token regeneration can mask wallet delta.

Implement a reusable exact spend evidence helper rather than duplicating logic.

Accept:
- ResourcesSpent[21] delta == +1
- and/or balance delta == -1 when compatible
But a conflicting spend delta must block confirmation.

The final result path should use the strongest current evidence:
- offense battle counters
- win/loss counter behavior
- selected FinishedOpponent identity where applicable
- exact Arena token spend
- visual result as corroboration

### 5. Terminal/inconclusive record

A post-StartIntent timeout must not merely set a phase that causes later samples to disappear.

At final result deadline, create a metadata-only terminal/inconclusive record or equivalent durable result object that:
- keeps attempt_id/opponent_id
- records reason
- retry_allowed=false
- contains no raw snapshots/screenshots
- prevents a blind second attempt until caller explicitly starts a fresh planning cycle.

Do not invent WIN/LOSS if evidence is insufficient.

### 6. Runtime samples are not programmer errors

Do not let expected delayed/stale/wrong-attempt runtime samples crash a long-running loop.

Prefer explicit statuses such as:
- IGNORED_STALE
- WRONG_ATTEMPT
- PENDING
- CONFLICTED
- INCONCLUSIVE

Exceptions can remain for construction/programming-contract errors.

### 7. Clock contract

Use one monotonic time domain for coordinator observations.

Do not compare wall-clock/file mtime against monotonic coordinator deadlines.
Document/enforce this at the coordinator boundary.

Do not perform a broad engine clock refactor in this package unless needed for correctness.

### 8. Improve diagnostic reasons

Preparation failures should distinguish at least:
- traversal missing
- traversal digest mismatch
- traversal version mismatch
- traversal incomplete
- traversal count mismatch
- own-power unavailable
- own-power stale/context mismatch

Do not leave them as generic CHECK_TRAVERSAL / CHECK_POWER if the coordinator stops or waits there.

## Required regression tests

Use realistic temporal ordering.

At minimum:
1. PRE account at StartIntent
2. visual battle at t+1, PlayerModel still PRE/token still 12 -> coordinator remains active/running
3. t+6 beyond start_timeout -> still active because battle visual seen
4. POST at result with balance 11 and ResourcesSpent[21] +1 -> WIN_CONFIRMED
5. same flow -> synthetic LOSS_CONFIRMED
6. no token persistence during running battle, later exact spend at result
7. balance delta masked by simulated regeneration but ResourcesSpent +1 -> exact spend still confirmed
8. ResourcesSpent +2 -> CONFLICTED / no WIN/LOSS
9. visual-only followed by final result timeout -> terminal INCONCLUSIVE record, not ordinary BLOCKED
10. no start evidence before deadline -> unresolved attempt remains owned; no second StartIntent
11. late sample from wrong attempt does not crash coordinator
12. stale/nonmonotonic runtime sample handled explicitly
13. duplicate terminal sample is idempotent
14. existing victory fixture remains compatible
15. entire existing suite remains green

## Scope / constraints

- no SendInput integration
- no live battle start enablement
- no replay
- no Gem refresh
- no new major architecture layer
- no raw snapshot/screenshot persistence
- do not simplify away immutable attempt ownership
- keep 006C coordinator pure/domain-level

## Completion report

Report:
- commit SHA
- exact phase/record changes
- exact spend evidence logic
- realistic PRE/running/POST tests
- pytest count
- Windows CI run/result
- confirmation that battle input remains disabled
