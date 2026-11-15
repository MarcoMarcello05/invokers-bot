# DEVELOPER HANDOFF

## NEXT PHASE — REAL CLIENT INTEGRATION

Status: BLOCKIERT BIS USER AM WINDOWS-CLIENT IST

Accepted baseline:
- ARENA-LIVE-006C1 commit `a7d8400d7f1c49ab40feaa730cd09a08cc8c2276`
- Windows CI `43694893685`
- `387 passed, 1 warning in 1.09s`

## Important

Do not start another large offline architecture package.

The next work requires the real Windows client.

Primary objectives:
1. calibrate live UI states/templates/ROIs,
2. validate real driver loop wiring against ArenaRunCoordinator,
3. measure actual start/result timing and persistence,
4. solve OwnPower pragmatically,
5. supervised navigation input,
6. supervised Arena start with no blind retry,
7. automatic result reconciliation.

## Required live timing probe

For one supervised Arena attempt, observe at ~1s cadence:
- visual state
- PlayerModel digest/version
- Arena Token wallet
- ResourcesSpent[Arena_Token]
- CurrentBattleOpponent if present
- Arena offense counters
from pre-click through result screen.

This validates when spend and structured battle evidence actually persist.

## Constraints
- no speculative coordinates/templates
- no battle input until live calibration is explicitly ready
- no replay
- no Gem refresh
- no new planner/GOAP abstractions
- no Campaign implementation yet
