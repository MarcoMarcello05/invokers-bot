# DEVELOPER HANDOFF

## Current package: LIVE-001B — AccountState-driven Goal eligibility + semantic resource verification

Status: BEREIT ZUR ENTWICKLUNG

Read first:
- PROJECT_WORKFLOW.md
- MASTER_STATUS.md
- MASTER_CHECKLIST.md
- TEST_RESULTS.md
- PLANNER_POLICY.md
- ACCOUNTSTATE_PLANNER_CONTRACT.md
- INVOKERS_GOAL_CATALOG.md
- PLANNER_DOMAIN_SCENARIOS.md
- ACTION_SOURCE_VERIFICATION_MATRIX.md
- LIVE_SKILL_VERIFICATION_CONTRACT.md
- LIVE_ACCOUNTSTATE.md
- src/invokers_bot/account_state.py
- src/invokers_bot/action_verification.py
- src/invokers_bot/engine.py

## Verified baseline

LIVE-001A:
- commit `43f665f37ec15b7d4b448f785184274e76b721ce`
- Windows CI run `43643095273`
- `215 passed, 1 warning`

## Goal

Make the scheduler/runtime consume live AccountState for the first real Goal eligibility decisions, while adding semantic resource predicates so structured verification does not stop at "some PlayerModel bytes changed".

Keep this package intentionally narrow.

## Part A — minimal AccountState-driven Goal eligibility

Implement the first planner-facing GoalCandidate/GoalEvaluation slice.

Required first candidates:

1. `G-MAINT-001 RefreshStructuredState`
2. `G-RES-001 SpendArenaTokensBeforeCap` / Arena opportunity eligibility

Do NOT implement the whole universal planner yet.

Arena eligibility must use:
- fresh PlayerModel
- ResourceTypeId.Arena_Token (21)
- configured threshold/reserve/cap policy values
- required Arena navigation capability
- source freshness

If AccountState is missing/stale:
- Arena Goal is BLOCKED with an explicit reason
- do not click

If token balance is below threshold:
- Arena Goal is not eligible

Expose deterministic evaluation/debug output showing:
- candidate id
- eligible bool
- blocked reasons
- source age/freshness used
- relevant resource value
- score components if scoring is introduced

## Part B — semantic resource verification

Extend ActionExpectation/verification in a minimal generic way so a state-changing action can declare semantic predicates against parsed AccountState.

First supported predicate family:
- resource delta / resource decreased / exact expected delta

Example concept:
`resource_decreased("player", ResourceTypeId.Arena_Token)`

or config representation with equivalent semantics.

Important:
- a changed PlayerModel digest alone is NOT enough to prove Arena token spend
- semantic predicate evaluates baseline vs post-action parsed PlayerModel resources
- missing resource value => failure/inconclusive, never guessed
- unrelated PlayerModel changes do not satisfy the predicate

Keep the predicate registry/contract extensible so future predicates can verify:
- hero level changed
- relic equipped relation
- quest claim state
without hardcoding all logic inside BotEngine.

## Arena start behavior

Current `arena.json` requires PlayerModel digest change within 5 seconds.

Do NOT hardcode the assumption that this is definitely the true live save timing.

For this package:
- support semantic ArenaToken decrease verification
- keep timeout configurable
- document that real-client testing may change whether Arena start is VISUAL_AND_STRUCTURED or staged visual-success + later structured reconciliation

If no real snapshot directory is configured:
- structured-required Arena action remains blocked before input

## Decision trace

Store/log the first minimal planner decision trace:
- AccountState observation/version/digest reference used
- Goal candidate
- eligibility result
- blocked reason or selected reason
- token balance/threshold
- timestamp

No sensitive raw snapshot bytes.

## Tests

Add tests at minimum for:

1. fresh PlayerModel + token above threshold -> Arena candidate eligible
2. token below threshold -> not eligible
3. missing PlayerModel -> blocked
4. stale PlayerModel -> blocked
5. missing Arena_Token resource -> blocked
6. exact resource decrease predicate succeeds
7. unchanged token with other PlayerModel change does NOT verify
8. token increase does NOT verify decrease
9. exact-delta predicate success/failure
10. corrupt post-action source cannot satisfy semantic predicate
11. decision trace contains no raw bytes
12. deterministic repeated evaluation
13. no live input occurs for blocked Goal

## Architecture constraints

- Planner/Goal code must consume AccountState, not MemoryPack slot numbers.
- No raw file parsing imports in Goal code.
- BotEngine must not grow domain-specific Arena resource logic inline.
- Semantic predicates belong in a reusable verification layer.
- No snapshot writes.
- Existing F12 / UNKNOWN no-input rules remain.

## Out of scope

Do not yet implement:
- Arena opponent parser/scoring
- full Goal utility engine across all domains
- Quest/Battle/Clan parsers
- automatic account directory discovery
- live retry policy
- real-client latency guessing
- purchases/destructive actions

## Completion

Run full pytest, push main, verify Windows CI and report:
- commit SHA
- full test count
- Actions run/result
- changed files
- exact Goal eligibility behavior
- semantic resource predicate API/config
- remaining live assumptions
