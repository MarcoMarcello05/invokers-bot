# DEVELOPER HANDOFF

## ARENA-LIVE-006A-CI — migrate legacy Arena policy tests

Status: FIX REQUIRED

Implementation commit under review:
`d0432a49479578afa0ac7d1847cb0544044c90bf`

Windows CI run:
`43649926909`

Result:
`3 failed, 356 passed, 1 warning in 1.11s`

## Failure analysis

All three failures are legacy expectations in `tests/test_goal_eligibility.py`.

### Failure 1
`test_configured_predicate`

Old expectation:
- kind == `resource_decreased`

Current verified config:
- kind == `resource_delta`
- resource_id == 21
- delta == -1

Fix the test to assert the exact live-validated predicate. Do not revert production config.

### Failure 2
`test_unknown_cap_allows_opportunity_but_not_spend`

Old expectation:
- Arena cap is None

Current policy:
- cap = 10 as regeneration ceiling
- observed balances may exceed it, e.g. 12
- cap must NOT clamp wallet balance

Update the test semantics accordingly:
- cap == 10
- token balance 12 remains 12
- goal may still be eligible above cap
- start remains blocked when allow_test_battle_start=false

Rename the test if needed so it no longer describes an unknown cap.

### Failure 3
`test_explicit_cost_required_and_predicate_matches`

Old expectation:
- config cost initially None -> DENY_UNKNOWN_COST

Current live-validated policy:
- cost == 1

Update the test so:
- current config with allow_test_battle_start=true and exact predicate -1 passes the cost gate
- explicit synthetic override cost=None must still produce DENY_UNKNOWN_COST
- mismatched predicate must still produce COST_PREDICATE_MISMATCH
- exact resource_delta -1 must pass

## Guardrails

Do NOT:
- revert cost to null
- revert cap to null
- revert resource_delta to resource_decreased
- weaken exact cost matching
- enable battle start
- enable replay/Gem refresh
- change ROI sensor behavior just to satisfy CI

## Required verification

Run full suite on Windows.

Expected:
- 359 tests total or more
- 0 failures
- existing live-victory and formation-power tests remain green

Push fix to `main` and report:
- new commit SHA
- exact changed tests
- pytest result
- Windows Actions run ID/conclusion

006A is not accepted until CI is green.
