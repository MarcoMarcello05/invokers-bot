# DEVELOPER HANDOFF

## Current package: LIVE-001A — Action-scoped AccountState invalidation and verification

Status: BEREIT ZUR ENTWICKLUNG

Read first:
- PROJECT_WORKFLOW.md
- MASTER_STATUS.md
- MASTER_CHECKLIST.md
- TEST_RESULTS.md
- LIVE_ACCOUNTSTATE.md
- PLANNER_POLICY.md
- ACCOUNTSTATE_PLANNER_CONTRACT.md
- src/invokers_bot/account_state.py
- src/invokers_bot/engine.py

## Context

Phase 4 is complete and live AccountState integration exists.

Verified live integration:
- commit: `371ab08015cb0bd9ec3e2a3ca4723a187133e80f`
- Actions run: `43642665870`
- result: `179 passed, 1 warning`

ANALYSER review found one architectural issue that should be fixed before AccountState-driven Goal selection:

After every real input, `AccountObserver.invalidate()` currently invalidates ALL tracked aggregates.

This is too coarse.

Example:
- user/bot opens a menu
- no Hero or Relic data changes
- Heroes and Relics become awaiting_change anyway
- because the files may never change, fresh Hero/Relic state can remain unavailable unnecessarily

## Goal

Replace blanket invalidation with ACTION-SCOPED invalidation and verification expectations.

## Required design

Each live action/Skill should be able to declare:

- `invalidates_sources`
- `expects_source_change`
- `expects_visual_transition`
- optional `verification_timeout`

Examples:

Navigation-only click:
- invalidates_sources = []
- expects_source_change = []

Start Arena battle:
- likely invalidates player/resources and arena when Arena parser exists
- does NOT invalidate heroes/relics unless the action itself can change them

Equip Relic:
- invalidates heroes + relics
- expects source change in both or whichever exact model changes

Claim reward:
- invalidates only the aggregate(s) that contain the claim/resource state

Unknown legacy flow without metadata:
- use a conservative compatibility default, but do not permanently poison unrelated sources

## AccountObserver API

Support scoped invalidation, e.g.:
`invalidate({"player", "relics"})`

Do not require all sources to change before unrelated sources remain usable.

A source marked awaiting_change should become fresh again only after:
- changed content is observed, OR
- verification policy explicitly says no source change was required and visual success is sufficient

Do not use unchanged bytes as proof of a state-changing action.

## Verification model

Introduce a small explicit action verification contract rather than ad-hoc checks in BotEngine.

Suggested concept:

ActionExpectation:
- invalidates_sources
- expects_changed_sources
- expected_visual_states
- timeout
- success_mode

Possible success modes:
- VISUAL_ONLY
- STRUCTURED_ONLY
- VISUAL_AND_STRUCTURED
- VISUAL_OR_STRUCTURED

Keep implementation minimal and deterministic.

Do not build full planner/Goal scoring yet.

## Engine behavior

Before action:
- capture pre-action relevant source versions/digests
- keep unrelated sources fresh

After action:
- wait for expected visual transition and/or relevant structured source change
- only poll/force-refresh relevant sources aggressively
- do not globally invalidate all AccountState

If verification fails:
- return a failure result/reason
- do not silently assume success
- main loop may re-observe/recover

## Tests

Add synthetic tests for at minimum:

1. navigation action invalidates nothing
2. player-only action invalidates only player
3. hero/relic action leaves player untouched
4. unrelated unchanged source remains fresh
5. expected source change satisfies structured verification
6. unchanged expected source does not satisfy structured verification
7. visual-only success does not wait for irrelevant files
8. structured-only success
9. visual+structured success
10. timeout/failure reason
11. corrupt changed source produces verification failure, not success
12. compatibility behavior for old flow actions
13. read-only behavior remains intact

Run full pytest, push to main, verify Windows GitHub Actions, update status/docs.

## Out of scope

Do NOT yet implement:
- full Goal utility scoring
- Arena parser
- Battle parser
- automatic account-directory discovery
- filesystem watcher dependency
- snapshot writes
- packet/injection behavior

## Completion report

Report:
- commit SHA
- branch
- push result
- full pytest result/count
- Actions run/result
- changed files
- exact compatibility default for legacy flow actions
- unresolved assumptions
