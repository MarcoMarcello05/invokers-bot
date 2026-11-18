# DEVELOPER HANDOFF

## QUEST-LIVE-001A — CI acceptance / stale Arena regression test

Status: BEREIT ZUR ENTWICKLUNG

Baseline implementation:
- QUEST-LIVE-001 commit: `d8f1ffeb7a660dbdd79a37366751342afa318e2f`
- Windows Actions run: `44280741108`
- actual result: **1 failed, 422 passed, 1 warning in 1.60s**

Failure:
`tests/test_arena_coordinator.py::test_visual_result_without_spend_pending`

Observed assertion:
expected `Phase.TERMINAL`, actual `Phase.RESULT_PENDING` at the old timeout point.

## Root cause

This failure is inherited from the previously merged Arena liveness hardening.

The Arena coordinator no longer treats a fixed 60-second result duration as battle duration. It now uses:
- soft start window
- inactivity/liveness timeout
- absolute hard cap

The failing test still asserts the pre-hardening timing behavior.

QUEST-LIVE-001 itself must not change Arena production behavior.

## Required fix

1. Inspect current `ArenaRunCoordinator` liveness semantics from commit history/current main.
2. Update only the stale Arena regression test(s) so they match the accepted state-driven watchdog behavior.
3. Do NOT weaken the liveness rules just to satisfy the old test.
4. Do NOT modify Arena production code unless an actual production defect is independently demonstrated.
5. Preserve the intended assertion:
   - visual result without exact spend remains RESULT_PENDING while within valid liveness window
   - it eventually becomes TERMINAL/INCONCLUSIVE only when the appropriate inactivity or hard watchdog deadline is actually reached
   - retry remains disallowed
6. Run the full pytest suite.
7. Push the correction to `main`.
8. Verify the real Windows Actions log, not only workflow status.

## QUEST-LIVE-001 acceptance checks after CI is green

Reconfirm:
- `quests_model.py` parses only verified PlayerQuestsModel fields
- union tags 1/2/3 only
- unknown numeric state/group values remain numeric; no guessed semantics
- dictionary QuestId/key invariant enforced
- Completed active state is only a claim candidate, not proof of UI claimability
- `PlayerQuestsModel.dat` integrated as scoped AccountState source
- no SendInput/OCR/navigation/claim code
- no raw snapshots committed
- no Arena production/config changes in the QUEST implementation commit

## Completion report

Report:
- corrective commit SHA
- exact stale test change
- final pytest count
- Windows Actions run ID and conclusion
- confirmation that no Arena production behavior was changed
- confirmation that QUEST-LIVE-001 remains read-only
