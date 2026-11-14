# DEVELOPER HANDOFF

## Current package: ARENA-LIVE-005A — ArenaBattleStats + post-battle result verification core

Status: BEREIT ZUR ENTWICKLUNG

This package is deliberately chosen because ARENA-LIVE-004A needs a real Windows client and is blocked while the user is away from the PC.

Do not alter the Own Team Power rules from ARENA-LIVE-004A.

## Verified baseline

- ARENA-LIVE-004 code/CI accepted
- commit `047c99ac78ddc377d09e9beddabe8e4cb23ed478`
- CI `43645551854`
- `304 passed, 1 warning`
- own power remains UNKNOWN until live validation
- battle start remains disabled
- opponent identity/CombatPower/fingerprint already structured

## Why this package

Current official Arena documentation confirms:
- Offense wins can change Arena Points
- Offense wins award Trophies and Arena Coins
- losses may reduce Arena Points depending on league/position
- the game has an Arena Offense Results screen
- current-week Arena history/statistics exist

We therefore need a structured post-battle verifier before autonomous battle start is enabled.

## Part A — verify and parse ArenaBattleStats

Inspect the current IL2CPP v39 schema and archived/current project evidence for `ArenaBattleStats`.

Implement only fields whose exact MemoryPack slot/type layout can be verified.

Known semantic field names from current schema research include:
- TotalOffenseBattles
- TotalOffenseWins
- TotalDefenseBattles
- TotalDefenseWins
- MaxLeagueReached
- TotalBattlesByLeague
- current/previous week offense attack/battle counts
- current/previous week offense wins
- current/previous week defense counts/wins

Do not guess slot order from field names.
Unknown/reserved slots remain opaque.

Expose parsed stats through `ArenaState` / AccountState with provenance.

## Part B — post-battle evidence model

Create a domain model such as `ArenaBattleOutcomeEvidence`.

It must support evidence from:
- Arena points before/after
- ArenaBattleStats counters before/after
- PlayerModel Arena Token before/after
- Arena Coin resource before/after when resource ID is already verified
- FinishedOpponents change when a semantic identity can be verified safely
- CurrentBattleOpponent before/after where available
- visual result state as a separate evidence channel

Do NOT require all channels simultaneously.

Distinguish:
- WIN_CONFIRMED
- LOSS_CONFIRMED
- BATTLE_COMPLETED_RESULT_UNKNOWN
- BATTLE_START_ONLY
- INCONCLUSIVE
- CONFLICTED

No single file timestamp/digest change is enough.

## Part C — exact semantic predicates

Implement reusable predicates, where underlying fields are verified:

- `arena_offense_battles_increased`
- `arena_offense_wins_increased`
- `arena_points_changed`
- `arena_token_spent_exactly`
- `arena_coin_increased`
- `finished_opponent_added`

A win can be confirmed by a strong combination such as:
- offense battle count +1
- offense win count +1
plus compatible supporting evidence

A loss can be confirmed by:
- offense battle count +1
- offense wins unchanged
plus compatible evidence

Do not infer loss solely from Arena Points decreasing because point rules vary by league/position.
Do not infer win solely from Arena Coins because other game systems may affect resources.

## Part D — result reconciliation

Build a bounded reconciliation object/state machine for the future live flow:

1. battle start baseline
2. battle/result visual transition
3. AccountState refresh
4. evaluate structured deltas
5. if visual + structured agree -> CONFIRMED
6. if visual result appears before snapshot persistence -> PENDING/INCONCLUSIVE
7. retry observation only, never replay battle automatically
8. timeout -> INCONCLUSIVE
9. conflicting evidence -> CONFLICTED and stop Arena loop

No SendInput is required in this package.

## Part E — reward evidence

Official current Arena docs say Offense wins award Arena Points, Trophies and Arena Coins.

For code:
- Arena Coins may be verified only if ResourceTypeId mapping is already exact
- Trophies must remain unknown/opaque unless their exact resource/type mapping is verified in existing project data
- do not invent trophy IDs or reward amounts
- reward amount depends on league, so no hardcoded amount

## Part F — weekly/history safety

Do not confuse:
- an Offense result caused by our just-finished battle
with
- Defense battle updates or weekly reset changes

Use:
- pre-action baseline
- opponent identity where possible
- offense-specific counters
- short verification window
- source provenance

Weekly reset or unrelated defense changes must not be misclassified as our Offense result.

## Tests

At minimum:
1. valid verified ArenaBattleStats parse
2. malformed/truncated stats
3. unknown stats slots preserved opaque
4. offense battle +1 / win +1 -> WIN_CONFIRMED
5. offense battle +1 / win unchanged -> LOSS_CONFIRMED
6. Arena Points change alone -> INCONCLUSIVE
7. Arena Coin increase alone -> INCONCLUSIVE
8. token delta alone -> BATTLE_START_ONLY
9. visual victory + delayed stats -> pending/inconclusive, no replay
10. visual defeat + matching stats -> LOSS_CONFIRMED
11. visual victory conflicting with stats loss -> CONFLICTED
12. defense-only stats changes do not confirm our result
13. weekly/reset-like broad changes do not confirm our result
14. exact token delta predicate rejects wrong amount
15. unknown Trophy mapping is never guessed
16. no SendInput/battle-start authorization added
17. existing 304+ suite remains green

## Architecture constraints

- BotEngine remains generic.
- Result semantics belong to Arena domain/verifier modules.
- No battle start.
- No automatic replay.
- No Gem refresh.
- No broad OCR.
- No guessed MemoryPack slots.
- No guessed reward resource IDs.
- No snapshot writes.
- No process/packet manipulation.

## Completion report

Report:
- commit SHA
- changed files
- exact ArenaBattleStats fields and slot/type evidence
- fields left opaque
- outcome evidence rules
- conflict/inconclusive behavior
- verified resource IDs actually used
- full pytest count
- Windows Actions run/result
- remaining real-client validation needed
