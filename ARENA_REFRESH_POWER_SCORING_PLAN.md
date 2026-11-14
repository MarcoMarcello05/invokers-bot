# ARENA REFRESH + OWN POWER + SCORING PLAN

Date: 2026-11-14

## Purpose

Close the remaining information gap before Arena opponent scoring:
1. detect when the opponent set changes
2. never reuse stale opponent candidates after refresh
3. determine the user's exact Arena Team Power source
4. keep premium/Gem refresh actions blocked unless explicitly authorized

## Current official Arena behavior

Current Hit Zone Arena documentation/update notes establish:
- Arena Offense uses an opponent list.
- The opponent list refreshes automatically over time.
- Manual refresh can cost Gems.
- Arena opponents are shuffled before being shown.
- Arena Team Power for both player and opponent includes Trophy Room bonuses.
- Arena tokens regenerate up to a cap of 10, at +1 per hour.

These web facts are version-sensitive and must not be hardcoded without provenance/config versioning.

## Consequence 1 — list order is not identity

Never identify an Arena opponent by:
- visible row index
- viewport position
- "first/second/third opponent"

The list may be shuffled and is scrollable.

Preferred identity:
1. structured opponent id / stable structured identity
2. structured opponent tuple with stable identifiers
3. visual fingerprint only as navigation fallback

## Consequence 2 — refresh invalidates the whole candidate ranking

Any confirmed opponent-set refresh must invalidate:
- scroll traversal inventory
- opponent row-to-viewport mapping
- target ranking
- selected target locator

After refresh:
1. reread PlayerArenaModel
2. obtain new opponent set
3. rerun traversal if UI target mapping is needed
4. rerank from scratch
5. never click cached coordinates from old list

## Refresh detection

Preferred structured evidence:
- PlayerArenaModel digest/version changed
AND
- semantic opponent-set fingerprint changed

Additional useful signals:
- LastOpponentsRefreshTime changed
- opponent collection membership changed

A raw file change alone is insufficient.

Define:

OpponentSetFingerprint =
stable hash over sorted structured opponent identities plus relevant matchup fields

Do NOT include:
- viewport order
- screen coordinates

If structured IDs are not yet mapped:
use bounded opaque-entry hashes temporarily for change detection, not for final semantic scoring.

## Automatic refresh vs manual refresh

Automatic server/game refresh:
- may happen while bot is idle or elsewhere
- detected by AccountObserver polling
- should trigger Arena candidate invalidation/replan

Manual refresh:
- R2/R4 depending on cost
- if Gems may be spent, blocked by default
- bot may only invoke manual refresh when UI/config proves the action is free or an explicit premium-spend policy exists

Current project policy:
Gems/premium spending remains blocked.

Therefore:
- do not implement automatic Gem refresh
- if refresh button cost is unknown, do not click
- free/timer-based refresh can be supported only after cost state is observable and verified

## Own Team Power source hierarchy

### A. Preferred direct structured source

PlayerBattleModel.LastMetaBattleSetup
 -> PlayerTeamSetup
 -> CombatPower

Live probe required:
- A: Arena list
- B: after Fight opens formation
- C: after backing out without starting battle

Compare PlayerBattleModel A/B/C.

Success criterion:
B exposes CombatPower equal to the visible own Team Power.

If true:
- pressing Fight is an R1 observation/navigation step
- no token spend yet
- own power can be read structurally after formation opens

### B. Exact local calculation

Potential inputs exist:
- AsyncPvpPreset team
- PlayerHeroesModel
- PlayerRelicsModel
- PlayerAccessoriesModel
- PlayerArenaModel
- formation data
- Trophy Room/Arena bonuses
- internal GetHeroPower logic

Do not ship until exact parity is demonstrated across multiple live examples.

Important:
Since current Arena Team Power includes Trophy Room bonuses, any local calculator that omits them is invalid.

### C. Tiny pre-battle numeric ROI

Fallback only if A fails and B is not exact.

Read only the own Team Power number from formation.
Do not expand into full-screen OCR.

## Opponent Team Power

Opponent power should come from structured PlayerArenaModel/ArenaOpponent.TeamSetup once nested schema is verified.

UI value is used only to:
- locate/confirm the intended opponent
- cross-check during development

## Scoring plan

Do not score until both values have reliable provenance.

Initial score can use:
- opponent CombatPower
- own Team Power
- Arena Points
- previous result state if available
- later team composition/element matchup

Initial safety threshold should be configurable.

Examples:
power_ratio = opponent_power / own_power

Possible policy bands are configuration, not game truth:
- safer candidate
- neutral candidate
- high-risk candidate

Do not hardcode ratio cutoffs until live results are collected.

## Refresh policy after scoring

If no acceptable opponent exists:

1. check whether opponent set is already stale/auto-refreshed
2. if stale/new set exists, reread and rerank
3. inspect manual refresh availability/cost
4. if cost is free and verified, refresh
5. if cost is Gems/unknown, block manual refresh
6. choose another Goal rather than spend premium currency

## Cache/freshness

Arena candidate cache key should include:
- Arena source digest/version
- opponent-set fingerprint
- own Team Power provenance/version
- relevant team/preset version
- scoring policy version

Any change invalidates ranking.

## Live diagnostic event

When entering formation for the own-power probe, log:
- PlayerBattleModel digest/version before
- PlayerArenaModel digest/version before
- selected opponent structured identity if available
- visible own Team Power if tiny ROI is temporarily used
- PlayerBattleModel digest/version after
- whether LastMetaBattleSetup became non-null
- structured CombatPower if present
- equality/mismatch to UI number
- back-out state

No raw private snapshots in Git.

## Next implementation slices

ARENA-LIVE-002:
- PlayerArenaModel live source
- bounded scroll traversal
- opponent observation inventory
- generic wheel input

ARENA-LIVE-003:
- nested ArenaOpponent/TeamSetup parser
- structured opponent CombatPower
- opponent-set fingerprint
- refresh detection/invalidation
- own-power A/B/C probe instrumentation

ARENA-LIVE-004:
- own power source finalized
- initial opponent scoring
- target selection/navigation
- no battle start yet unless token cost verified

ARENA-LIVE-005:
- formation verification
- start battle
- exact token semantic verification
- result/win/loss handling
