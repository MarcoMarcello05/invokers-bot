# DEVELOPER HANDOFF

## Current package: ARENA-LIVE-005B — FinishedOpponents + result correlation + battle-attempt context

Status: BEREIT ZUR ENTWICKLUNG

ARENA-LIVE-004A remains blocked on a real Windows-client Own Team Power test.
ARENA-LIVE-005A is code/CI accepted.

## Verified baseline

- ARENA-LIVE-005A commit `779d5b4106f031b24fa5361763ac716b206eabcf`
- Windows CI run `43646254157`
- `323 passed, 1 warning in 1.06s`
- ArenaBattleStats parser exists
- read-only outcome reconciliation exists
- battle start still disabled
- replay never authorized

## Goal

Strengthen future post-battle correlation so the verifier can tie a completed Arena result to the exact selected opponent and exact battle attempt.

This package must remain fully read-only and synthetic/offline-testable.

## Part A — FinishedOpponents semantic model

Research and verify the exact nested MemoryPack layout for entries in `PlayerArenaModel.FinishedOpponents`.

Implement only confirmed fields.

Target semantic fields where verified:
- opponent/player identity
- result / win-loss marker if present
- opponent metadata needed to correlate to `ArenaOpponent`
- any battle/result timestamp only if exact slot/type is verified

Unknown fields stay opaque.

Do not assume FinishedOpponents entries have the same wire layout as ArenaOpponent unless verified.

## Part B — result correlation key

Create a deterministic `ArenaBattleAttemptContext` captured before battle start.

It should contain:
- selected opponent Player-ID
- opponent-set fingerprint
- Arena source digest/version
- Player source digest/version
- token balance baseline
- Arena points baseline
- offense stats baseline
- created_at / attempt id
- expected token cost only if verified/configured

No click coordinates.

## Part C — FinishedOpponent correlation

Implement correlation rules:

Strong match:
- finished entry contains the exact selected opponent Player-ID

Possible additional evidence:
- result field matches visual/counter outcome
- battle/result timestamp falls inside the attempt window, if verified

Never correlate by:
- display name alone
- list position
- screen coordinates

If multiple finished entries match ambiguously:
- mark correlation ambiguous
- do not confirm result from FinishedOpponents alone

## Part D — attempt-scoped reconciliation

Update the result-verification core so evidence is explicitly attached to one `ArenaBattleAttemptContext`.

Requirements:
- evidence from before the attempt cannot bleed into a later attempt
- stale target/opponent-set fingerprint invalidates the attempt before battle start
- once battle is started, later opponent-list refresh must not erase the attempt identity used for result correlation
- post-battle verifier compares against the immutable attempt baseline
- duplicate/late observations do not create a second result

## Part E — terminal result record

Create an immutable terminal record for future run history:
- attempt id
- opponent id
- outcome
- supporting evidence summary
- start/end observation times
- points/token/coin deltas if known
- stats deltas
- result source/provenance
- conflict flags

No raw snapshot bytes.
No private account dump persisted to Git.

## Tests

At minimum:
1. valid FinishedOpponents entry parse
2. malformed/truncated entry rejected
3. unknown fields stay opaque
4. exact Player-ID correlation
5. same display name/different Player-ID does not correlate
6. ambiguous duplicate matches -> INCONCLUSIVE/CONFLICTED
7. attempt context immutable
8. pre-battle opponent fingerprint mismatch blocks attempt
9. post-start refresh does not erase opponent identity
10. late duplicate observation does not create second terminal result
11. result record contains no raw snapshot bytes
12. no SendInput/battle-start/replay path added
13. existing 323+ suite remains green

## Constraints

- no guessed FinishedOpponents schema
- no fight start
- no replay
- no Gem refresh
- no broad OCR
- no snapshot writes
- BotEngine remains generic

## Completion report

Report:
- commit SHA
- exact FinishedOpponents fields/slots verified
- correlation key
- ambiguity behavior
- terminal record schema
- full pytest count
- Windows CI result
- remaining live-client assumptions
