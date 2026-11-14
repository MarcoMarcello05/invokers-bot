# BOT ARCHITECTURE BENCHMARK — 2026-11-14

Purpose: compare proven automation/bot architectures and extract patterns that improve Invokers Autopilot without blindly copying any one framework.

## Sources reviewed

### OpenKore
Relevant current sources:
- https://github.com/OpenKore/openkore
- https://github.com/OpenKore/openkore/blob/master/src/AI/Attack.pm
- https://github.com/OpenKore/openkore/blob/master/plugins/eventMacro/eventMacro.pl
- https://github.com/OpenKore/openkore/blob/master/control/config.txt

Useful patterns:
- explicit AI action queue
- action preconditions
- hooks before/after commands and AI phases
- interruptible macro/AI work
- queue inspection/debugging
- task-specific timeout/give-up behavior

### RuneLite
Relevant current source:
- https://github.com/runelite/runelite/blob/master/runelite-client/src/main/java/net/runelite/client/plugins/PluginManager.java

Useful patterns:
- PluginManager lifecycle
- EventBus
- Scheduler
- dependency/conflict handling
- clean registration/unregistration
- failure isolation during plugin startup/shutdown

### BehaviorTree.CPP
Relevant current sources:
- https://github.com/BehaviorTree/BehaviorTree.CPP
- https://github.com/BehaviorTree/BehaviorTree.CPP/blob/master/docs/mainpage.md
- https://github.com/BehaviorTree/BehaviorTree.CPP/blob/master/src/controls/reactive_sequence.cpp

Useful patterns:
- Blackboard shared state
- ReactiveSequence / ReactiveFallback
- retry / timeout decorators
- explicit RUNNING / SUCCESS / FAILURE status
- interruptible execution
- reusable subtrees

### Robot Framework
Relevant current sources:
- https://github.com/robotframework/robotframework
- https://github.com/robotframework/robotframework/blob/master/doc/userguide/src/GettingStarted/Introduction.rst

Useful pattern:
- framework core stays generic
- concrete systems are controlled through external libraries/drivers
- automation intent is separated from technology-specific interaction

## Decision for Invokers

Do NOT replace the current architecture with a third-party framework.

Instead retain:

Sensors -> WorldState -> GoalManager -> TaskScheduler -> Skill -> SafetyGate -> ActionExecutor -> Verification -> refresh/replan

and strengthen it with these borrowed patterns.

## A. Event-driven state updates

Adopt RuneLite-style event publication internally.

Examples:
- SnapshotChanged(PlayerModel)
- SnapshotChanged(PlayerArenaModel)
- VisualStateChanged
- BattleEnded
- ResourceChanged
- QuestCompleted
- SkillFailed
- StaleStateDetected

Consumers subscribe rather than every subsystem polling every source.

Benefits:
- fewer repeated reads
- clearer dependencies
- easier testing
- easier replay/debugging

## B. Blackboard entries must carry freshness

Every WorldState fact should carry:
- value
- source
- observed_at
- source_version if available
- confidence
- freshness policy

Example:
Arena.points:
- value: 534
- source: PlayerArenaModel
- aggregate_version: 3587
- observed_at: snapshot UpdatedAtUtc
- confidence: STRUCTURED_CONFIRMED

The planner should be allowed to reject stale facts.

This is inspired by blackboard-driven reactive control but adapted to our multi-sensor situation.

## C. Goal / Task / Skill status contract

Use explicit status values:

- READY
- RUNNING
- SUCCESS
- FAILURE_RETRYABLE
- FAILURE_TERMINAL
- BLOCKED
- CANCELLED

Avoid Boolean-only task results.

This gives recovery logic enough information to make a sane next decision.

## D. Reactive preemption

Borrow the useful part of ReactiveSequence:

Before each irreversible or expensive step, re-evaluate critical preconditions.

Example Arena flow:
1. navigate Arena
2. select opponent
3. before spending token, refresh ArenaToken + current opponent + visual dialog
4. if facts changed, cancel and replan

Do not let a long task blindly continue from stale assumptions.

## E. Skills as plugins, not giant condition chains

Each domain should expose reusable skills, e.g.:

Arena:
- open_arena
- refresh_opponents
- select_opponent
- start_arena_battle
- claim_arena_reward

Campaign:
- open_campaign
- choose_level
- start_battle
- claim_first_clear_reward

Skill metadata should declare:
- required state
- produced state/events
- risk level
- retry policy
- timeout
- required sensors
- whether it spends resources
- whether it is reversible

This mirrors the lifecycle/isolation benefits of plugin-based systems.

## F. Recovery as first-class behavior

Each Skill should define a bounded recovery policy.

Examples:
- visual target absent -> one state refresh, then alternate navigator path
- unexpected modal -> classify/close if safe, then re-evaluate
- structured state stale -> reread file, no click
- action verification failure -> stop the task and replan
- repeated failure -> circuit-breaker for that skill/domain

No infinite retries.

## G. Action trace / observability

Borrow the queue/debug visibility idea from OpenKore.

Maintain a compact structured trace:
- goal chosen + score
- task selected
- preconditions used
- source ages
- skill started
- action issued
- expected transition
- observed transition
- success/failure reason
- recovery path

This should later support a human-readable diagnostic timeline.

## H. Source arbitration

For each fact, define preferred sensors.

Priority:
1. structured local game state
2. deterministic event/update signal
3. CV/template recognition
4. targeted OCR
5. fixed coordinates only as last-resort action geometry

When two sources conflict:
- prefer authoritative structured state for account facts
- prefer current visual state for what screen/dialog is actually visible
- do not merge silently; record conflict and re-evaluate

## I. Planner guardrails

The planner must not directly click.

Only Skills can request Actions.
Only SafetyGate can approve risky Actions.
Only ActionExecutor can produce input.

This is a hard architecture boundary.

## J. Useful future additions

Recommended after core AccountState works:
- event bus
- StateFact wrapper with freshness/confidence
- per-skill retry/timeout/circuit-breaker
- replayable decision trace
- action cost/risk metadata
- capability registry so planner knows which features are currently usable
- source health monitor (snapshot parser healthy? CV healthy? window visible?)

## What NOT to copy

Do not copy:
- giant global mutable state
- unbounded AI queues
- action scripts that assume screen state remains unchanged
- polling everything every loop
- plugin systems without dependency/risk metadata

The target is a small deterministic autonomous core, not a framework zoo.
