# MASTER PLAN

## Product goal

Build **one universal autonomous Invokers bot**, not a collection of isolated mode scripts.

The bot should eventually be able to:
- inspect the current game/account state,
- discover available work,
- prioritize goals,
- navigate to the required screen,
- execute the task,
- verify completion,
- collect rewards,
- recover from interruptions,
- continue with the next best task without human clicks.

Target domains include:
- daily/weekly quests,
- campaign,
- Arena,
- clan tasks,
- events,
- inbox/reward collection,
- resource claims,
- progression tasks,
- repeatable farming,
- roster/team maintenance where safe and rule-driven.

## Development strategy

### Phase 1 - Universal core
- Goal/task model.
- Central scheduler.
- Reusable navigation skills.
- Shared perception/state store.
- Shared action executor.
- Verification/recovery.
- Resource and risk gates.
- Persistent run memory/logging.

### Phase 2 - World model
- Fresh screenshots and local structured files.
- Map every important top-level screen and transition.
- Map task/reward indicators.
- Build typed observations instead of mode-specific booleans.

### Phase 3 - First complete skills
Implement several end-to-end skills against the same core:
1. collect obvious free rewards,
2. inspect quest/task lists,
3. Arena,
4. campaign,
5. clan/tasks.

Arena is a validation skill, not the architecture center.

### Phase 4 - Autonomous scheduler
The scheduler repeatedly:
1. observes,
2. builds available goals,
3. scores priority/benefit/cost/risk,
4. chooses one goal,
5. decomposes it into tasks,
6. executes one safe action at a time,
7. verifies the world changed,
8. replans.

### Phase 5 - Expansion
Add remaining game systems incrementally until the bot can handle the practical daily account loop end to end.

## Non-goals
- No giant hard-coded linear script.
- No separate duplicated navigation stack per mode.
- No blind clicking on timers.
- No OCR-everything architecture.
