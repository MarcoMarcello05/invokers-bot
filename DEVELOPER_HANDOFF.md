# DEVELOPER HANDOFF

## NEXT PHASE — REAL CLIENT INTEGRATION

Status: BLOCKIERT BIS USER AM WINDOWS-CLIENT IST

Accepted baseline:
- ARENA-LIVE-006C1 commit `a7d8400d7f1c49ab40feaa730cd09a08cc8c2276`
- Windows CI `43694893685`
- `387 passed, 1 warning in 1.09s`

006C1 resolved the delayed token-persistence defect:
- visual battle can keep the attempt active without immediate spend persistence
- start timeout is soft after StartIntent
- unresolved post-intent ownership is retained
- exact result spend prefers ResourcesSpent[Arena_Token]
- terminal INCONCLUSIVE records preserve unresolved attempts
- no battle input is enabled

## Do not start another large offline package

The project is now integration-bound.

Next work requires the real Windows client:
1. capture client size + DPI
2. calibrate current Arena UI states/templates/ROIs
3. validate Home -> Arena -> list -> formation navigation
4. choose the MVP OwnPower strategy from real evidence
5. run live dry/shadow observation
6. enable one supervised navigation input
7. then one supervised Arena StartIntent execution
8. observe start timing and PlayerModel/ResourcesSpent persistence
9. reconcile result
10. capture any popup/loading/recovery cases encountered

## Specific live measurement

For one supervised battle, sample at ~1s cadence from PRE through result:
- visual state
- PlayerModel digest/version
- Arena token balance
- ResourcesSpent[Arena_Token]
- PlayerArenaModel digest/version
- CurrentBattleOpponent if available

This is diagnostic observation only until explicit start integration is enabled.

## While user is mobile

Allowed:
- code review for defects
- CI maintenance
- documentation corrections
- tiny scaffolding directly needed for the next live session

Do not:
- expand planner/GOAP architecture
- add Campaign
- invent templates/coordinates
- enable battle input
- enable replay
- enable Gem refresh
