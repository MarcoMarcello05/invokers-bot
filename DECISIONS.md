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


### D019 — Hybrid planner instead of full GOAP for the current phase
The bot uses hard eligibility/safety gates first, deterministic utility scoring second, and registered Task/Skill plans for execution. Reactive replanning occurs when prerequisites change, facts become stale, actions fail or higher-priority events appear. A generic GOAP search planner is intentionally deferred until cross-domain quest routing demonstrates a real need for it.

### D020 — Safety gates are non-compensatory
Risk permission, resource reserve policy, freshness, capability availability and evidence consistency are hard prerequisites. A larger expected reward or progression value can never compensate for a failed safety gate.

### D021 — Deterministic utility selection with hysteresis
Eligible Goals are ranked by bounded utility components including priority, deadline urgency, progression/reward value, quest/event synergy, resource-overflow pressure and bounded starvation age, minus time/resource/navigation/failure/risk costs. The active valid Goal receives a modest continuation bonus to prevent oscillation; safety and urgent expiry conditions may preempt immediately.

### D022 — Parser layer is isolated from planner semantics
Low-level MemoryPack parsers expose immutable decoded models. AccountState adapters attach provenance, source version, freshness and semantic names. Goal code never depends on binary slot numbers, file paths or MemoryPack decoding.


### D023 — Overlapping objectives collapse into one executable domain Goal
If one game action advances several objectives (for example Arena token spending + daily quest + event progress), the planner should create one executable domain Goal and add synergy value from the dependent objectives. It should not create multiple competing loops for the same action.

### D024 — Broad priority tiers bound preemption, utility decides within the band
Safety/recovery outranks expiring/claim work, which outranks ordinary active-session/progression/development/maintenance work. Utility scoring chooses among eligible Goals within those broad bands. This prevents a small numeric score difference from causing nonsensical preemption across fundamentally different urgency classes.


### D025 — Action invalidation is scoped and separate from expected change
A live input only invalidates the structured sources that may have become stale because of that action. This list is distinct from the sources whose changed content is required to prove success. Navigation-only actions invalidate no account aggregates.

### D026 — Live action success is evidence-based
State-changing actions must capture relevant pre-action evidence and evaluate explicit post-action visual and/or structured predicates. A file timestamp change alone is not success; an unchanged digest is not immediate failure before the configured save grace expires.

### D027 — Verification can be inconclusive
The runtime must distinguish SUCCESS, FAILURE, TIMEOUT, CANCELLED and INCONCLUSIVE. Visual success combined with delayed structured persistence must not be silently promoted to semantic success for high-risk account-changing operations.

### D028 — Retries occur at Skill level after re-observation
A failed live action is not mechanically clicked again. The Skill re-observes screen/account state, re-checks preconditions, and only then decides whether a bounded retry is safe. This prevents duplicate spends and double confirmations.
