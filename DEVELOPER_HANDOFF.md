# DEVELOPER HANDOFF

## Current package: ARENA-LIVE-006A — live-validated cost + pre-start OwnPower ROI + victory fixtures

Status: BEREIT ZUR ENTWICKLUNG

## Newly verified live evidence

A real Windows-client offense battle was captured PRE / result-screen POST / return.

### Exact live deltas
- Arena Token ResourceTypeId 21: 12 -> 11
- ResourcesSpent[21]: +1
- Arena Coin ResourceTypeId 22: +50
- ArenaMedal_Bronze ResourceTypeId 23: +1
- Arena Points: 534 -> 543
- total offense battles: 13 -> 14
- total offense wins: 13 -> 14
- weekly offense battles: 13 -> 14
- weekly offense wins: 13 -> 14
- FinishedOpponents: +1 exact selected Player-ID
- POST == RETURN byte-for-byte for Player/Arena/Battle
- LastMetaBattleSetup stayed null

UI:
- pre-start formation own power: 9368
- result-screen own team power: 9425
- do NOT treat those values as equivalent
- Arena list top -> bottom: 3 normal wheel steps
- live token display can exceed regen ceiling: 12/10

## Goals

### Part A — configure exact observed battle cost
Update ArenaTokenPolicy default expected_battle_cost from null to 1 for current policy version.

Requirements:
- remain configurable/versioned
- document live evidence
- do not make 1 a parser constant
- no Gem refill
- reserve semantics unchanged

### Part B — calibrated pre-start OwnPower numeric ROI
Implement the existing PREBATTLE_NUMERIC_ROI fallback as a real read-only sensor for the formation screen.

Reference capture:
- screen resolution: 1536x864
- own pre-start power text: 9.368
- normalized ROI approximately:
  - x 0.521 .. 0.651
  - y 0.139 .. 0.255
Use the narrowest robust ROI around the own 'Stärke' numeric value.

Requirements:
- targeted digits only, no broad OCR
- accept German thousands punctuation and normalize 9.368 -> 9368
- exact integer output only
- confidence must be 1.0 only after strict parse/template validation
- source PREBATTLE_NUMERIC_ROI
- exact=True only when strict ROI recognition succeeds
- validated=True only when calibrated screen/client geometry matches
- reject malformed/multiple-number/ambiguous ROI
- reject if screen state is not confirmed formation
- no result-screen ROI reuse
- result-screen 9425 must not contaminate pre-start OwnPower
- keep structured source preferred if ever independently validated in future

### Part C — live victory regression fixture
Do NOT commit raw user snapshots.
Create sanitized synthetic fixtures reproducing the verified deltas:
- token -1
- coin +50
- Bronze medal +1
- points +9
- offense battle +1
- offense win +1
- weekly offense battle/win +1
- new FinishedOpponent exact selected Player-ID
- POST/RETURN equivalence behavior

Expected result:
- WIN_CONFIRMED
- exact token spend true
- finished_added true
- replay_allowed false
- one terminal record only

### Part D — result timing contract
Update docs/tests so result verification may reconcile on result screen.
Returning to Arena is not required for persistence.
Delayed persistence remains supported conservatively.

### Part E — token cap semantics
Ensure 10 means regeneration ceiling/pressure threshold, not wallet clamp.
Observed balance 12 must remain valid and classify AT_CAP.
Never clamp to 10.

## Tests

At minimum:
1. expected current policy cost == 1
2. observed token balance 12 remains 12, pressure AT_CAP
3. formation ROI parses 9.368 -> 9368
4. integer 9368 produces exact validated PREBATTLE_NUMERIC_ROI under calibrated geometry
5. malformed/ambiguous ROI rejected
6. wrong visual state rejected
7. result-screen 9425 cannot be consumed as pre-start own power
8. stale/unmatched geometry rejected
9. authorization with exact ROI power + fresh target + cost 1 can ALLOW planning
10. spend verification 12 -> 11 confirms exact -1 only with required visual/structured contract
11. sanitized live-victory fixture => WIN_CONFIRMED
12. selected FinishedOpponent exact Player-ID supports result
13. same-name/different-ID remains rejected
14. POST==RETURN does not generate duplicate terminal
15. no raw client snapshots in Git
16. no SendInput/battle-start/replay/Gem refresh enabled
17. existing 342+ suite green

## Constraints
- read-only sensing/policy/tests only
- no battle-start activation yet
- no raw user data committed
- no broad OCR
- no result-screen power substitution
- BotEngine remains generic

## Completion report
Include:
- commit SHA
- exact cost policy change
- ROI coordinates/normalization and recognition method
- OwnPower provenance flags
- live victory fixture behavior
- pytest count
- Windows CI run/result
- remaining live blocker(s), especially loss-path validation and final start-action integration
