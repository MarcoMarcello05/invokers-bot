# DEVELOPER HANDOFF

## Current package: ARENA-LIVE-004A — Real-client Own Team Power validation

Status: LIVE-TEST AUSSTEHEND

No further autonomous Arena ranking code should be added before this validation.

## Verified code baseline

- commit `047c99ac78ddc377d09e9beddabe8e4cb23ed478`
- Windows CI run `43645551854`
- `304 passed, 1 warning in 0.69s`
- opponent ranking is diagnostic only
- battle start disabled
- unvalidated own power cannot authorize selection/fight

## Objective

Determine the exact real-client source for the user's own Arena Team Power.

Preferred:
`PlayerBattleModel.LastMetaBattleSetup -> PlayerTeamSetup -> CombatPower`

Fallback:
small pre-battle numeric ROI, but only after live calibration and repeated parity checks.

## Required A/B/C experiment

A. Open Arena opponent list and let diagnostics observe the baseline.
B. Press Fight on any opponent so the formation screen opens. Do NOT start the battle.
C. Return/back to the Arena list.

Capture/record:
- PlayerBattleModel digest/version at A/B/C
- PlayerArenaModel digest/version at A/B/C
- LastMetaBattleSetup present/null and digest if available
- visible own Team Power on the formation screen
- if tiny ROI diagnostic is enabled for the test, its raw numeric result/confidence
- whether B -> C preserves or clears the Battle setup

## Acceptance

Best case:
- a structured CombatPower value appears at B
- it exactly equals the UI Team Power
- repeated tests remain equal

If structured value does not materialize:
- calibrate the tiny numeric ROI
- validate it across multiple formation openings
- keep provenance PREBATTLE_NUMERIC_ROI until proven exact enough for policy

Do not:
- start a battle
- spend Arena tokens
- refresh with Gems
- change formation
- broaden OCR

After the live probe, report the captured diagnostics and exact UI Team Power number. Do not guess missing fields.
