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


### D029 — Unknown resource caps and costs are never inferred
Resource overflow logic may use only verified static/runtime data or explicit configuration. If a cap or action cost is unknown, the planner records that uncertainty and does not invent a value.

### D030 — ResourcePlanner owns spend authorization
Domain Goals request permission to spend a resource; they do not implement reserve/event-save/session-limit logic themselves. Decisions are explicit (ALLOW / limited allow / deny reason) and require fresh structured balance data.

### D031 — Visual success may require later structured reconciliation
If a state-changing live action reaches its expected visual state before the relevant snapshot persists, the runtime must not immediately retry the action. It reconciles structured state first and may remain INCONCLUSIVE/PENDING rather than risking duplicate spend.


### D032 — Finish Arena end-to-end before starting the next domain
Arena remains the first complete vertical slice. Campaign work is deferred until Arena includes opponent discovery, selection, battle/result handling and recovery. This gives one fully proven autonomous domain rather than several half-finished ones.

### D033 — Scrollable lists require bounded verified traversal
The Arena opponent list is scrollable. The bot must use generic SendInput wheel actions, verify list-ROI change, de-duplicate overlapping observations, detect end-of-list semantically where possible, and enforce max-scroll/time bounds. A fixed blind scroll count alone is insufficient.

### D034 — Scrolling is navigation, not account mutation
Arena list scrolling is R1/reversible UI navigation. It must not invalidate Player/Arena/account snapshots merely because a wheel input was sent. Structured state is invalidated only by actions that can change account state.


### D035 — Opponent-set refresh invalidates Arena target state
A confirmed PlayerArenaModel opponent-set change invalidates traversal inventory, visual row mapping, candidate ranking and selected target. The bot must reread/retraverse/rerank before clicking a target from the new list.

### D036 — Premium Arena refresh remains blocked
Official current Arena behavior allows opponent-list refreshes over time and manual refresh for Gems. The bot may observe automatic refreshes, but must not perform a Gem-cost refresh under the default policy. Unknown refresh cost is treated as blocked, not assumed free.

### D037 — Own Arena Team Power requires provenance
Preferred source order is structured LastMetaBattleSetup.PlayerTeamSetup.CombatPower after live validation, then an exact reproduced calculator only after parity is proven, then a tiny pre-battle numeric ROI as fallback. Approximate Team Power is not accepted for autonomous matchup decisions. Trophy Room bonuses must be represented because current Arena Team Power includes them.


### D038 — Build result verification while Own-Power live validation is blocked
ARENA-LIVE-004A requires the real Windows client and remains pending. Development may continue on independent Arena completion work that does not weaken the Own-Power gate or enable battle start. The next parallel package is ArenaBattleStats parsing and post-battle outcome reconciliation.

### D039 — Arena outcome is multi-evidence, not one-field inference
A completed Arena Offense battle is classified from offense-specific counters plus compatible visual/resource/opponent evidence. Arena Points, Arena Coins, token deltas or generic snapshot changes alone do not prove win/loss. Conflicting evidence stops the Arena loop rather than guessing.


### D040 — Current official Arena token pressure facts are policy inputs, not immutable schema
Current official Arena documentation states Arena Tokens regenerate +1 per hour and stop at 10. These values may be used as versioned/configurable policy defaults for token-pressure scoring, not as hardwired parser facts. Exact per-battle token cost remains unknown until verified; unknown cost continues to block autonomous spend authorization.

### D041 — Pre-start authorization is a pure decision object before any SendInput
Arena battle start authorization must be computed from a fresh selected candidate, exact validated OwnPower, fresh PlayerModel token balance, immutable attempt baseline, current opponent-set fingerprint and explicit expected token cost. The authorization object itself cannot send input.
