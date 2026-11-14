# DEVELOPER HANDOFF

## Current package: LIVE-002A — PlayerBattleModel + first Campaign Goal

Status: BEREIT ZUR ENTWICKLUNG

Read first:
- PROJECT_WORKFLOW.md
- MASTER_STATUS.md
- MASTER_CHECKLIST.md
- TEST_RESULTS.md
- BATTLE_MULTIBATTLE_MAP_0.62.1621.md
- ACCOUNTSTATE_PLANNER_CONTRACT.md
- PLANNER_POLICY.md
- INVOKERS_GOAL_CATALOG.md
- ACTION_SOURCE_VERIFICATION_MATRIX.md
- LIVE_SKILL_VERIFICATION_CONTRACT.md
- RESOURCE_PLANNER_POLICY.md
- current parser/account_state/goal code under src/invokers_bot

## Verified baseline

LIVE-001B:
- commit `6c12332548ff3c0e6d0d536fda7250156732f0ad`
- Windows CI run `43643490286`
- `242 passed, 1 warning`
- AccountState-driven Goal gating is working
- semantic resource predicates are working
- blocked Goals do not send input

Arena has served its purpose as the first vertical slice.
Do NOT deepen Arena in this package.

## Goal

Add the second autonomous domain: Campaign/Battle.

Implement the verified PlayerBattleModel top-level state and wire it into AccountState, then add the first Campaign eligibility Goal.

This package is intentionally a vertical slice, not a full Battle subsystem.

## Part A — PlayerBattleModel parser

Use the existing envelope + VersionTolerant infrastructure.

Follow `BATTLE_MULTIBATTLE_MAP_0.62.1621.md`.

Requirements:
- parse the verified top-level PlayerBattleModel slots
- preserve reserved/unknown slots safely
- expose immutable state
- parse only nested structures whose layout is already verified
- do not guess unknown nested schemas
- keep parser read-only
- unknown enum numeric values preserved

At minimum expose the fields needed for Campaign eligibility and later verification:
- version / updated_at
- LevelStats / campaign progress representation where verified
- claimed campaign reward state where verified
- MultiBattleSession top-level state where verified
- relevant timestamps / campaign progression fields documented as verified

If a nested LevelStats entry layout is not fully verified, preserve raw/opaque member content and expose only safely proven metadata/counts. Do not invent fields.

## Part B — AccountState integration

Add `battle` as a live source:
- PlayerBattleModel.dat
- freshness/error/digest semantics identical to existing sources
- scoped invalidation support
- no coupling between parser and planner

AccountState should expose:
- battle
- existing player/heroes/relics unchanged

## Part C — first Campaign Goal

Implement a narrow planner-facing candidate, e.g.:

`G-PROG-001 CampaignOpportunity`

Eligibility should use only facts currently proven available.

Required gates:
- fresh PlayerModel
- fresh PlayerBattleModel
- Campaign navigation capability configured
- no source error/awaiting_change
- Energy resource available if Campaign action requires Energy
- ResourcePlanner/policy approves any known configured spend

If exact Campaign Energy cost is not verified/configured:
- navigation/inspection may be eligible
- actual battle-start spend remains blocked
- do not guess cost

The Goal must remain outside BotEngine domain logic.

## Part D — structured verification hooks

Prepare Campaign action verification using the existing generic semantic predicate architecture.

Do not add Campaign-specific branches inside BotEngine.

Useful first semantic capability, only if supported by verified Battle state:
- a known campaign progress/claimed-state predicate
OR
- exact/decreased Energy predicate when configured cost is known

If campaign progress semantics are not yet safely parsed, keep structured verification limited to resource deltas and visual state.

## Part E — Decision Trace

Campaign candidate must emit the same diagnostic quality as Arena:
- candidate
- eligible/blocked
- battle source freshness/version/digest
- player source freshness/version/digest
- relevant Energy balance
- configured cost/reserve
- selected reason

No raw snapshot bytes.

## Tests

Add tests at minimum for:

1. valid PlayerBattleModel root
2. malformed/truncated Battle root
3. unknown/reserved slots preserved
4. AccountState battle source fresh
5. corrupt Battle source blocks Campaign Goal
6. missing Battle source -> refresh/block
7. stale Battle source -> block
8. fresh Player + Battle -> Campaign candidate eligible for navigation/inspection
9. missing Energy -> blocked when action requires Energy
10. unknown Campaign cost -> no battle-start authorization
11. configured exact Energy cost -> ResourcePlanner budget enforced
12. blocked Campaign Goal never sends input
13. Decision Trace deterministic and contains no raw bytes
14. existing Arena behavior remains regression-safe
15. full existing suite passes

## Architecture constraints

- Do not implement Quest parser in this package.
- Do not deepen Arena.
- Do not hardcode Campaign slot numbers in Goal code.
- BotEngine stays domain-agnostic.
- no snapshot writes
- no process injection/packet manipulation
- no invented Energy cost
- UNKNOWN remains no-input
- F12 remains immediate abort

## Out of scope

- full campaign stage selection
- team optimization
- automatic battle tactics
- Quest parser
- Clan/Event/Boss/Spire implementation
- MultiBattle execution
- opponent scoring
- destructive/purchase actions

## Completion

Run full pytest, push to main, verify Windows CI, update docs and report:
- commit SHA
- full test count
- Actions run/result
- changed files
- exact Battle fields implemented
- which Battle fields remain opaque
- Campaign eligibility behavior
- remaining assumptions
