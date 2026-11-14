# PLANNER POLICY — Goal scoring, freshness, risk and recovery

Date: 2026-11-14

Purpose: define how the autonomous bot decides WHAT to do next, without coupling the planner to UI coordinates or individual game modes.

## External architecture research

Current patterns reviewed:
- OpenKore AI timing/retry/give-up behavior
- BehaviorTree.CPP reactive sequences, retry/timeout and blackboard concepts
- RuneLite EventBus / Scheduler / plugin lifecycle
- GOAP action preconditions/effects/cost planning
- utility-AI scoring with cooldowns and commitment/hysteresis

Research references:
- https://github.com/OpenKore/openkore/blob/master/control/timeouts.txt
- https://github.com/BehaviorTree/BehaviorTree.CPP/blob/master/docs/mainpage.md
- https://github.com/runelite/runelite/blob/master/runelite-client/src/main/java/net/runelite/client/plugins/PluginManager.java
- https://github.com/sploreg/goap
- https://github.com/stolk/GPGOAP
- https://github.com/erkan612/gmsmartagent

## Planner decision

Use a HYBRID planner:

1. hard eligibility/safety gates
2. utility scoring to select the best eligible Goal
3. deterministic Task/Skill plan for execution
4. reactive precondition re-check before important actions
5. replan after success, failure, stale evidence or higher-priority event

Do NOT introduce a full generic GOAP search planner yet.

Why:
- Invokers has many known menu/domain workflows rather than arbitrary world actions.
- deterministic skills are easier to test and diagnose.
- full GOAP would add search/state-model complexity before the required actions/effects are stable.
- GOAP concepts remain useful later for cross-domain quest routing.

## 1. Goal eligibility is a hard gate

A Goal is not scoreable until all mandatory gates pass.

Required gates may include:

- required capability/skill exists
- required structured facts exist
- required facts are fresh enough
- required screen/navigation path is known
- relevant resource balance is sufficient
- configured reserve will not be violated
- cooldown/reset window permits action
- no circuit breaker is active
- no unresolved conflicting evidence
- risk class is permitted by policy
- irreversible-action policy allows the operation

A high reward can NEVER compensate for a failed safety gate.

Example:
An attractive shop offer does not become selectable if purchase permission is disabled.

## 2. Goal model

Each candidate Goal should expose at least:

- id
- domain
- reason
- base_priority
- urgency/deadline
- expected_value
- progression_value
- resource_cost
- time_cost
- navigation_cost
- failure_probability or confidence
- risk_class
- required_facts
- freshness_requirements
- required_capabilities
- cooldown / next eligible time
- completion predicate
- cancellation predicate

Optional:
- event synergy
- quest synergy
- inventory-pressure relief
- current-goal continuation bonus

## 3. Risk classes

Recommended ordered classes:

R0 READ_ONLY
- inspect structured data
- inspect visible state

R1 REVERSIBLE
- navigate/open/close tabs
- select filters
- change temporary selection

R2 CONSUMABLE_LOW
- spend regenerating/common resource such as Energy or Arena token
- only under configured reserve/budget policy

R3 ACCOUNT_CHANGE
- upgrades
- equipping/replacing items
- spending scarce progression materials

R4 DESTRUCTIVE_OR_PAID
- sell/crush/dismiss
- irreversible fuse/material consumption
- premium/real-money purchase

Default policy:
- R0/R1 may run automatically when confidence passes threshold.
- R2 requires budget/reserve policy.
- R3 requires explicit domain policy and high-confidence structured state.
- R4 is blocked unless explicitly enabled with dedicated safeguards.
- real-money purchase remains blocked by default.

Risk is a gate first, penalty second.

## 4. Utility score

After eligibility gates, rank goals with a normalized utility score.

Recommended conceptual form:

Utility =
  BasePriority
+ DeadlineUrgency
+ RewardValue
+ ProgressionValue
+ QuestSynergy
+ EventSynergy
+ ResourceOverflowPressure
+ StarvationAgeBoost
+ ContinuationBonus
- ResourceCost
- TimeCost
- NavigationCost
- FailurePenalty
- RiskPenalty

Use bounded components rather than unbounded raw game values.

Suggested total output range:
0..100.

No single reward component should make a forbidden/risky goal eligible.

## 5. Deadline / expiry behavior

Urgency must rise as a known reset/expiry approaches.

Examples:
- daily quest reset
- weekly Arena processing
- event/tournament end
- claimable reward expiration
- capped/regenerating resource near overflow

Recommended urgency curve:
- far from deadline: near zero
- approaching useful window: gradual rise
- final safe execution window: strong rise
- insufficient remaining time: mark BLOCKED rather than thrash

## 6. Resource overflow pressure

Regenerating/capped resources should create positive pressure before they waste regeneration.

Examples:
- Arena tokens
- Energy
- mode-specific keys/tokens

Pressure should depend on:
- current balance
- effective cap if known
- regeneration rate/sync timestamp
- reserve policy
- available useful sink

Do not spend scarce non-regenerating resources just because balance is high.

## 7. Resource reserves

ResourcePlanner owns reserve rules.

Examples:
- minimum Gem reserve
- minimum Gold reserve
- save Stars/Orbs for event
- preserve ascension/awakening material for selected target
- spend Arena tokens before cap

A Goal consuming resources must request a budget decision rather than directly checking a raw balance.

Decision output:
- ALLOW
- ALLOW_WITH_LIMIT
- DENY_RESERVE
- DENY_EVENT_SAVE
- DENY_UNKNOWN_COST

## 8. Freshness-aware facts

Every normalized fact should use a wrapper conceptually like:

StateFact<T>:
- value
- source
- observed_at
- source_version
- confidence
- freshness_class

Freshness classes:

REALTIME_VISUAL
- current visible screen/dialog
- expires quickly

FAST_ACCOUNT
- resources, active battle state, arena opponent state
- refresh after relevant action/version change

SESSION
- roster/equipment facts that rarely change unless bot performs an account action

SLOW_META
- long-lived stats/settings

STATIC_BUILD
- enum/config/schema data tied to game build

Planner must ask for fresh required facts, not blindly consume the latest cached value.

## 9. Evidence conflict policy

Do not silently average conflicting sources.

Examples:
- structured Arena says opponent A selected
- UI recognition shows opponent B card
=> do not start battle; refresh/reconcile.

Rules:
- structured state is authoritative for account ownership/resources/progress
- visual state is authoritative for what screen/dialog is physically visible
- conflict creates STALE_OR_CONFLICTED prerequisite
- planner schedules observation/recovery, not action

## 10. Goal commitment / hysteresis

Utility AI can oscillate when two goals have similar scores.

Prevent thrashing with a continuation bonus.

Recommended behavior:
- current valid Goal gets a modest commitment bonus
- switch only when another Goal exceeds it by a configurable margin
- safety/expiry/emergency goals can preempt immediately
- commitment disappears if current Goal becomes blocked/stale/failed

This borrows the useful 'commitment' concept from utility AI without adding randomness.

No weighted-random action selection for the main bot. Determinism is preferred for testing.

## 11. Anti-starvation

Low-priority maintenance tasks must eventually run.

Use bounded age boost:
- waiting Goal slowly gains score
- boost has a hard cap
- cannot override safety/risk gates

Examples:
- inbox cleanup
- non-urgent reward claim
- diagnostics
- inventory housekeeping

## 12. Scheduler execution states

Use explicit statuses:

READY
RUNNING
SUCCESS
FAILURE_RETRYABLE
FAILURE_TERMINAL
BLOCKED
CANCELLED

Optional diagnostic reason codes:
- STALE_FACT
- UI_NOT_FOUND
- NAVIGATION_FAILED
- RESOURCE_RESERVE
- COOLDOWN
- CONFLICTED_EVIDENCE
- VERIFICATION_FAILED
- CIRCUIT_OPEN
- SAFETY_POLICY

## 13. Retry / timeout / circuit breaker

OpenKore demonstrates the value of separate retry cadence and give-up windows.
BehaviorTree.CPP similarly separates retry and timeout behavior.

Each Skill declares:

- action timeout
- verification timeout
- max immediate retries
- retry delay/backoff
- failure classification
- circuit-break threshold
- cooldown after circuit open

Example:
open_arena:
- retry visual navigation once
- if still not found, navigate_home + retry once
- then open ARENA navigation circuit for N minutes / until state change
- scheduler chooses another Goal

Never infinite-loop a broken skill.

## 14. Replanning triggers

Re-evaluate Goal selection when:

- snapshot aggregate version changes
- resource count changes
- quest state changes
- battle result occurs
- current task succeeds/fails
- visual screen changes unexpectedly
- current required fact becomes stale
- event deadline crosses threshold
- skill circuit breaker opens/closes
- user configuration/policy changes

Do not recompute everything at 60 FPS.

Capture can be 60 FPS while planning remains event-driven.

## 15. Skill contract

Each Skill declares:

- name
- domain
- preconditions
- expected effects
- verification evidence
- risk class
- resource spends
- supported cancellation points
- retry policy
- timeout
- required sensors
- expected successor states

Planner selects Skill by capability ID.
Planner never emits raw clicks.

## 16. Action cost model

For multi-step Task plans, action cost can guide route/skill selection.

Cost dimensions:
- navigation steps
- expected duration
- resource consumption
- failure likelihood
- recovery difficulty

This borrows GOAP's cost idea without requiring global action-graph search.

Later, if cross-domain quest routing becomes complex, these same Preconditions / Effects / Costs can feed a bounded GOAP planner.

## 17. Initial Goal families

Recommended universal candidate Goals:

SAFETY / RECOVERY
- recover_known_screen
- resolve_blocking_modal
- reconnect
- stop_on_inconsistent_state

CLAIM
- claim_completed_quest
- claim_daily/weekly/monthly rewards
- claim_inbox reward
- claim campaign first-clear
- claim clan/event/tournament rewards

AVOID WASTE
- spend Arena tokens near cap
- spend Energy when near cap and valid farming target exists
- use expiring attempt/key

PROGRESSION
- advance campaign
- progress quest objective
- progress spire/boss
- improve selected hero/titan
- upgrade gear according to budget

FARM
- farm configured material/resource
- MultiBattle/background session

MAINTENANCE
- refresh Arena opponents when strategically justified
- inventory housekeeping
- diagnostics/state refresh

Never create a destructive maintenance Goal until irreversible-action policies are implemented.

## 18. Example scoring

Scenario:
- completed daily quest reward available
- Arena tokens near cap
- campaign progression available

All safety gates pass.

ClaimDaily:
- base 35
- deadline 20
- reward 15
- nav cost -3
= 67

SpendArenaToken:
- base 30
- overflow pressure 25
- reward/progression 12
- nav/time -8
= 59

CampaignProgress:
- base 25
- progression 20
- quest synergy 5
- resource/time cost -15
= 35

Bot claims daily first, then immediately replans.
Arena likely becomes next.

These numbers are configuration examples, not hard-coded game truth.

## 19. Current implementation sequencing

Do not implement the complete planner before structured AccountState is available.

Recommended order:

1. StateFact/provenance/freshness model
2. Goal data model + hard eligibility gates
3. deterministic utility scorer
4. Task status/reason contract
5. retry/timeout/circuit-break policy
6. simple scheduler with hysteresis
7. event-driven replanning
8. ResourcePlanner/reserves
9. domain goal generators
10. optional bounded GOAP only if cross-domain planning proves necessary

## Acceptance philosophy

The planner is successful when it can explain:

- what Goals were available
- which were rejected and why
- how eligible Goals scored
- why the winner was selected
- what facts and their ages were used
- what resources/risk policy allowed it
- why it switched or stayed committed
- what happened after execution

If the bot cannot explain a decision, diagnostics are insufficient.
