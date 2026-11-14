# DEVELOPER HANDOFF

## Current package: ARENA-LIVE-003 — ArenaOpponent semantics + exact opponent power + refresh fingerprint + own-power probe

Status: BEREIT ZUR ENTWICKLUNG

Read first:
- PROJECT_WORKFLOW.md
- MASTER_STATUS.md
- MASTER_CHECKLIST.md
- TEST_RESULTS.md
- ARENA_MEMORYPACK_MAP_0.62.1621.md
- ARENA_GOAL_POLICY.md
- ARENA_REFRESH_POWER_SCORING_PLAN.md
- ARENA_OWN_POWER_SOURCE_ANALYSIS.md
- ACCOUNTSTATE_PLANNER_CONTRACT.md
- LIVE_SKILL_VERIFICATION_CONTRACT.md
- current arena_model.py / arena_traversal.py / arena_skill.py / account_state.py

## Verified baseline

ARENA-LIVE-002:
- commit `84eadeb436e707c3e9157252fc6b3f66c5fa009c`
- Windows CI run `43644672629`
- `269 passed, 1 warning in 0.66s`
- PlayerArenaModel top-level source is live
- bounded scroll traversal is implemented
- stale Arena source cancels traversal
- scroll input does not invalidate account sources
- live ROI/template/scroll calibration remains pending

## Goal

Turn opaque Arena opponent entries into verified structured matchup data and establish a reliable opponent-set identity.

Also instrument the own-Team-Power probe so a real client test can answer whether formation opening materializes `PlayerBattleModel.LastMetaBattleSetup.PlayerTeamSetup.CombatPower`.

Do NOT implement autonomous battle start in this package.

## Part A — ArenaOpponent nested parser

Research the current IL2CPP v39 schema and implement only verified fields.

Target fields, where byte layout is verified:
- stable opponent identifier if present
- Name
- Level
- ArenaPoints
- TeamSetup
- Avatar
- Frame
- ClanAbbreviation
- CreatorsInfo
- IsVip
- VipLevel
- Result

Do not guess field order from names alone.
Preserve unknown/reserved members opaque.

## Part B — TeamSetup + opponent CombatPower

Decode the nested opponent TeamSetup far enough to expose the exact displayed opponent Team Power / CombatPower.

Requirements:
- exact integer/FixedPoint conversion must match stored representation
- no OCR needed for opponent power once structured field is verified
- unknown team member fields remain opaque
- preserve raw IDs for future team composition mapping

Acceptance:
- parser returns exact opponent power from saved/synthetic fixtures
- historical project evidence indicating exact opponent CombatPower should be used as cross-check where available

## Part C — opponent identity and set fingerprint

Create a stable semantic opponent identity.

Preferred:
- explicit opponent/player id if verified

Fallback:
- stable tuple of verified immutable-ish structured identifiers

Do NOT use:
- row index
- scroll position
- display name alone

Create `OpponentSetFingerprint` from sorted semantic opponent identities + relevant matchup state.

Use it to detect list refreshes.

A refresh is semantically confirmed when:
- arena source changed
AND
- opponent-set fingerprint changed

Update WorldState/arena cache behavior so a changed fingerprint invalidates:
- traversal inventory
- row mapping
- candidate ranking placeholder/cache
- selected opponent placeholder/cache

## Part D — refresh semantics

Expose:
- LastOpponentsRefreshTime
- opponent-set fingerprint
- arena source digest/version

Automatic refresh:
- detected and causes replan

Manual refresh:
- still blocked if cost is Gem/unknown
- do not click refresh in this package

## Part E — own Team Power probe instrumentation

Add a diagnostic probe for:

A. arena_list before Fight
B. formation after Fight
C. back to arena_list without starting battle

Capture metadata for:
- PlayerBattleModel envelope digest/version
- PlayerArenaModel digest/version
- selected opponent semantic identity if known

If PlayerBattleModel nested parsing support is sufficient and verified, decode:
- LastMetaBattleSetup
- PlayerTeamSetup
- CombatPower

Otherwise:
- keep envelope probe and log whether payload/digest changed
- do not invent nested Battle offsets

The probe must never start a battle.

## Part F — traversal integration

Once structured opponent identities exist:
- traversal inventory may join visual rows/cards to structured opponent candidates only when evidence is sufficient
- keep visual fingerprint as navigation evidence
- do not assume list order from structured data equals viewport order unless verified

A refresh during traversal remains STALE and forces restart.

## Tests

Add at minimum:

1. valid ArenaOpponent parse
2. malformed/truncated opponent entry
3. unknown/reserved nested slots preserved
4. exact opponent CombatPower parse
5. opponent Name/Level/ArenaPoints parse
6. stable semantic identity deterministic
7. same opponents different order -> same set fingerprint
8. one opponent changed -> different set fingerprint
9. arena digest changed but same opponent set -> no semantic refresh
10. opponent set changed -> traversal/ranking cache invalidated
11. stale traversal inventory rejected after set change
12. display name collision does not collapse two different opponents
13. LastOpponentsRefreshTime exposed
14. own-power probe records A/B/C metadata safely
15. probe never sends Start Battle
16. Gem/unknown manual refresh remains blocked
17. existing 269+ regression suite remains green

## Architecture constraints

- no broad OCR
- no guessed opponent schema
- BotEngine remains domain-agnostic
- semantic Arena parsing stays in arena domain/model layer
- no snapshot writes
- no packet/process manipulation
- no automatic Gem refresh
- no battle start
- no final opponent scoring yet

## Completion report

Report:
- commit SHA
- branch/push result
- full pytest count
- Actions run/result
- exact ArenaOpponent fields implemented
- exact TeamSetup/CombatPower field implemented
- semantic identity definition
- opponent-set fingerprint definition
- refresh invalidation behavior
- own-power probe outputs
- what still requires the real client
