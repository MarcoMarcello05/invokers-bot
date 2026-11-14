# DEVELOPER HANDOFF

## Current package: ARENA-LIVE-002 — PlayerArenaModel + bounded scrollable opponent-list traversal

Status: BEREIT ZUR ENTWICKLUNG

Read first:
- PROJECT_WORKFLOW.md
- MASTER_STATUS.md
- MASTER_CHECKLIST.md
- TEST_RESULTS.md
- ARENA_MEMORYPACK_MAP_0.62.1621.md
- ARENA_GOAL_POLICY.md
- RESOURCE_PLANNER_POLICY.md
- ACTION_SOURCE_VERIFICATION_MATRIX.md
- LIVE_SKILL_VERIFICATION_CONTRACT.md
- ACCOUNTSTATE_PLANNER_CONTRACT.md
- current AccountState / Goal / Input / Vision code

## Verified baseline

LIVE-001B:
- commit `6c12332548ff3c0e6d0d536fda7250156732f0ad`
- CI run `43643490286`
- `242 passed, 1 warning`
- AccountState-driven Arena opportunity gating works
- semantic Arena-token verification infrastructure exists
- fight start remains blocked by default unless explicit spend policy is configured

## Product direction

Do NOT pivot to Campaign yet.

Arena is now the first domain to be completed end-to-end before moving to the next domain.

User-confirmed UI behavior:
- the Arena opponent list is vertically scrollable
- opponents below the initial viewport must be discoverable

## Arena completion roadmap

This package is stage 1 of completion:

1. LIVE PlayerArenaModel source
2. bounded opponent-list scrolling/traversal
3. opponent observation inventory

Following packages:
4. verified ArenaOpponent semantic model
5. opponent scoring/ranking
6. target selection + formation
7. battle start + token verification
8. result/win/loss handling
9. refresh-opponents logic
10. circuit/recovery + real-client validation

Do not skip directly to scoring before the opponent data model is verified.

## Part A — PlayerArenaModel parser and AccountState source

Implement the verified PlayerArenaModel top-level layout from `ARENA_MEMORYPACK_MAP_0.62.1621.md`.

Requirements:
- reuse existing envelope + VersionTolerant readers
- add `arena` source to AccountObserver/AccountState
- expose verified top-level fields only
- preserve unknown/unverified nested fields opaque
- no guessed ArenaOpponent member layout
- numeric unknown enum values preserved
- read-only snapshot access

Expose at minimum all top-level fields whose types/layout are verified in the map, including where verified:
- version / updated_at
- points
- opponents collection metadata/raw entries
- finished opponents
- current battle opponent
- last opponents refresh time
- HallBonuses
- Stats
- other verified root fields

If opponent entry internals are not yet verified, keep individual entries opaque/bounded rather than inventing semantic fields.

## Part B — generic wheel-scroll input support

The Windows input layer currently supports click/key paths.

Add a reusable vertical wheel action through the existing SendInput path.

Requirements:
- generic action type, e.g. `scroll_wheel`
- signed wheel delta
- use Windows wheel semantics; WHEEL_DELTA = 120 per wheel notch
- no obsolete mouse_event implementation
- cursor must be positioned over a configured client-relative list ROI before wheel input if required by the game
- action remains client/DPI aware
- F12 abort still applies

Do not hardcode Arena into InputController.

## Part C — bounded Arena opponent-list traversal Skill

Implement a reusable Arena opponent-list traversal mechanism.

Behavior:

1. start from recognized `arena_list`
2. observe current opponent-list ROI
3. record visible opponent rows/cards
4. scroll downward by a configured bounded amount
5. wait for the list ROI to visually change/stabilize
6. observe newly visible rows
7. de-duplicate already seen entries
8. repeat until end-of-list or safety limit
9. optionally restore list to top if policy requires deterministic selection

### End-of-list detection

Do NOT use a fixed arbitrary number of scrolls as the only stop condition.

Support at least:
- ROI/content fingerprint unchanged after a scroll
OR
- no new opponent observations after repeated bounded scroll attempts

Also enforce:
- max scroll count
- max traversal duration

If the UI contains a scrollbar/thumb and robust detection already exists, it may be used as supplemental evidence, not required.

### De-duplication

Preferred identity order:
1. structured Arena opponent identifier once ArenaOpponent schema is verified
2. stable visual/card fingerprint
3. bounded fallback row fingerprint for traversal only

Do not use player display name alone as guaranteed identity.

## Part D — opponent observation inventory

This package does NOT need final opponent scoring yet.

It must produce a diagnostic inventory for one traversal:
- traversal id
- viewport/page index
- visible row/card regions
- visual fingerprints
- structured opponent entry count if available
- number of unique observations
- stop reason: END_UNCHANGED / NO_NEW_ROWS / MAX_SCROLLS / TIMEOUT / CANCELLED
- screenshots/fingerprints for failures only, not raw private snapshot bytes in Git

This inventory is the bridge to the ANALYSER mapping the nested ArenaOpponent structure.

## Part E — Planner/Goal behavior

Existing ArenaOpportunity remains the entry Goal.

Before FightBestAcceptableOpponent exists:
- Arena navigation may be selected when eligible
- list traversal may run as a read/reversible R1 Skill
- actual battle start stays blocked by existing spend policy unless explicitly configured

Do not make list scrolling spend Arena tokens.

## Verification

A wheel-scroll is successful only if:
- the opponent-list ROI changes and stabilizes
OR
- end-of-list is explicitly detected by unchanged content after the attempt

UNKNOWN screen:
- stop traversal
- no additional input

Unexpected screen transition:
- cancel traversal and return control to recovery/replan

## Tests

Add tests at minimum for:

1. valid PlayerArenaModel root
2. malformed/truncated Arena root
3. opaque opponent entry preservation
4. AccountState exposes fresh arena source
5. corrupt arena source becomes unavailable
6. signed wheel delta/action contract
7. scroll action does not mutate account sources
8. one-page opponent list stops without unnecessary scroll
9. multi-page list discovers new rows across scrolls
10. duplicate visible rows are de-duplicated
11. unchanged ROI after scroll -> end-of-list
12. no-new-rows repeated -> end-of-list
13. max-scroll safety bound
14. timeout safety bound
15. F12 cancellation
16. UNKNOWN cancels/no further input
17. unexpected screen transition cancels
18. battle start remains blocked by default
19. existing 242+ regression tests remain green

## Architecture constraints

- BotEngine remains domain-agnostic
- scroll action belongs to generic input/action layer
- Arena traversal belongs to Arena Skill/domain layer
- no OCR unless a specific field cannot be obtained structurally/visually otherwise
- no guessed ArenaOpponent schema
- no snapshot writes
- no packet/process manipulation
- no infinite scroll loops

## Completion report

Report:
- commit SHA
- branch/push result
- total pytest count
- Windows Actions run/result
- changed files
- exact PlayerArenaModel fields implemented
- what remains opaque
- scroll delta/config used
- end-of-list detection behavior
- number of synthetic traversal cases
- unresolved live-client assumptions
