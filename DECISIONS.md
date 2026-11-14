# DECISIONS

- D001: Clean restart accepted; history/archive retained.
- D002: Python 3.11+ for first Windows MVP.
- D003: DXcam primary capture, MSS fallback.
- D004: Template/ROI perception plus structured local state; targeted OCR later.
- D005: External Windows input only, no injection/packet manipulation.
- D006: UNKNOWN=no action, F12 abort, purchases blocked by default.
- D007: **Superseded**. Arena is not the product scope.
- D008: Product architecture is universal Goal -> Task -> State -> Action.
- D009: One central scheduler decides what to do next across all game systems.
- D010: Modes are implemented as reusable skills and navigation graphs, not separate bots.
- D011: Every world-changing action requires fresh verification before further action.
- D012: Structured account/task data should drive planning whenever it can be read reliably.

- D013: ANALYSER plans/researches/reviews; DEVELOPER implements production code from explicit prompts.
- D014: Every new technical/architecture topic requires current web/GitHub research before implementation decisions.
- D015: Raw player/account snapshot data is never pushed to the public repository; only sanitized derived analysis is committed.


### D016 — Research patterns, do not import a bot framework
Current bot/automation architectures were reviewed before extending the planner. The project keeps its own deterministic Sensors -> WorldState -> Goal -> Task -> Skill -> SafetyGate -> Executor -> Verification pipeline. We adopt proven patterns selectively: event publication, blackboard-style state, reactive precondition re-checks, explicit execution statuses, bounded retry/timeout/circuit-breaker behavior, plugin-like skill lifecycle, and decision tracing. We do not introduce a third-party behavior-tree/RPA framework as a runtime dependency.

### D017 — WorldState facts require provenance and freshness
Future normalized AccountState/WorldState facts should carry source/provenance and observation freshness (including aggregate version where available). Structured account state and visual screen state are complementary, not interchangeable. Planner actions may reject stale prerequisites.

### D018 — Structured state decides; vision navigates/verifies
Where a confirmed local structured source exists, it is the preferred source for ownership, progress, resources and candidate selection. Vision remains authoritative for currently visible UI state, navigation targets, blocking dialogs and transition verification. OCR is a gap-filler, not the primary account database.
