# ARCHITECTURE

## Target architecture

```
Sensors
  |- local structured files/events
  |- window/client geometry + DPI
  |- DXcam/MSS frames
  |- templates / CV / targeted OCR
  v
WorldState / Blackboard
  v
GoalManager
  v
TaskScheduler
  v
Skill / Navigator
  v
SafetyGate
  v
ActionExecutor
  v
Verification
  v
WorldState refresh -> replan
```

## Hierarchy

**Goal -> Task -> State -> Action**

Examples:

- Goal: complete available daily quests
  - Task: inspect quest screen
  - Task: choose completable quest
  - Task: navigate to required game mode
  - Task: execute activity
  - Task: return and claim reward

- Goal: spend Arena tokens efficiently
  - Task: navigate to Arena
  - Task: inspect opponents
  - Task: choose opponent
  - Task: fight
  - Task: verify result

- Goal: process clan work
  - Task: open clan
  - Task: inspect available clan actions
  - Task: execute eligible actions
  - Task: collect claimable rewards

## Core components

### WorldState
Single typed snapshot of everything currently known:
- current screen,
- visible badges/claim markers,
- resource counters,
- quest availability,
- local-file facts,
- cooldowns/timers,
- current task,
- confidence and evidence age.

### GoalManager
Creates possible goals from WorldState. A goal has:
- availability,
- priority,
- expected value,
- resource cost,
- risk,
- cooldown,
- success condition.

### TaskScheduler
Chooses the highest-value eligible goal and decomposes it into executable tasks. It may interrupt a lower-priority goal when a higher-priority condition appears.

### Skills
Reusable capabilities, not mode-specific monoliths:
- navigate(screen)
- click_target(template)
- close_popup()
- wait_for_state()
- claim_visible_reward()
- inspect_task_list()
- select_battle_target()
- start_battle()
- return_home()

### Verification
No task is considered complete because an input was sent. Completion requires fresh evidence from screen/local state.

## Rules

- UNKNOWN never clicks.
- Fresh observation before every world-changing action.
- Prefer structured state over OCR when validated.
- Prefer reusable navigation edges over duplicated mode flows.
- Any coordinate action must be client-normalized and state-gated.
- F12 abort.
- Purchase-like actions blocked unless explicitly permitted.
- Persistent UNKNOWN saves diagnostics and triggers recovery/replan.
- Planner never emits raw arbitrary input; it selects registered skills.


## Reactive input/performance policy

The runtime must not use fixed post-click sleeps as its normal synchronization mechanism.

Preferred hot path:

```
recognized state
 -> registered action
 -> SendInput
 -> immediately observe buffered DXcam frames
 -> look for expected successor state
 -> continue as soon as fresh evidence appears
```

Performance rules:
- DXcam runs as a buffered stream at 60 FPS by default.
- Decision loop runs independently from capture rate.
- Post-action synchronization is state-driven with a timeout only as a failure bound.
- Expected successor states should be declared per transition.
- Future optimization: verify only small ROIs for known hot transitions.
- Irreversible actions remain deliberately slower/stricter and require stronger evidence.
- Windows input uses SendInput rather than obsolete mouse_event/keybd_event paths.
