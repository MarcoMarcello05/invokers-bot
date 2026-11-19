# DEVELOPER HANDOFF

## AUTOPILOT-MVP-001 — Exort-style first working loop

Status: BEREIT ZUR ENTWICKLUNG

## Strategic direction

Use Exort only as a public behavioral/product reference, not as source code.

Public Exort behavior to emulate at architecture level:
- read account/game state
- maintain a visible current task
- prioritize daily tasks before ordinary farming
- run one game-mode task at a time
- respect reserves/stop conditions
- verify battle/result progress
- continue to next playable task instead of stalling globally
- pause/stop safely
- keep run/task statistics

Do NOT reverse engineer or copy proprietary Exort implementation.

The project priority is now a working autonomous vertical slice, not deeper static-data decoding.

QUEST-LIVE-003 remains parked.

## MVP target

Implement the smallest real closed loop using the existing Windows Invokers client:

1. Observe current game/UI state.
2. Determine one executable task.
3. Navigate to Arena.
4. Choose one safely recognized visible opponent.
5. Start one offense battle.
6. Observe until terminal result using state-driven liveness.
7. Verify spend/result through structured Arena state where available.
8. Return to Arena/home.
9. Mark task success/failure/inconclusive.
10. Be ready to select the next task.

This proves the same core loop that a larger Exort-style planner can later reuse.

## Minimal architecture

Create/finish these boundaries only where needed:

### Observer
Produces current visual + structured state.

### Agenda
A small ordered list of executable jobs.
For MVP it may contain only:
- ArenaBattleOnce

Later jobs can include Campaign, Boss, rewards, quests, farming.

### TaskRunner
Owns exactly one active job and its attempt state.

### Skill
Executes one bounded UI transition:
- open Arena
- select opponent
- start battle
- return after result

### Verifier
Checks postconditions from screenshots + structured state.

### Recovery
Bounded, state-aware recovery only.

Do not introduce a new universal planning framework beyond this.

## State/action loop

Every transition must follow:

observe
→ classify
→ choose one action
→ input once
→ observe again
→ verify
→ continue/recover

No fixed macro sequences.
No blind retries.
No fixed battle-duration sleep.

## Arena MVP simplifications

Not required:
- perfect opponent ranking
- exact own Team Power
- full scroll traversal
- Quest Prototype decoding
- team optimization
- universal planner

Allowed selection:
- first/highest-confidence visible eligible opponent card

Keep existing smarter Arena systems intact for later.

## Safety

- Arena offense only
- require fresh verified token balance >= 1
- verified cost = exactly 1 Arena Token
- NEVER spend Gems
- manual opponent refresh disabled
- unknown/premium confirmation => no input + abort
- F12 global stop
- no replay after inconclusive result
- no blind Start retry
- one active attempt only

## Visual states needed

Minimum:
- HOME / known starting state
- ARENA_LIST
- FORMATION / pre-battle
- BATTLE_RUNNING or equivalent evidence
- RESULT_WIN
- RESULT_LOSS
- ARENA_RETURNED
- LOADING
- UNKNOWN
- UNSAFE/PREMIUM_CONFIRMATION if encountered

Use stable multi-frame recognition where appropriate.

## Diagnostics

Each decision trace should include:
- current state
- confidence/evidence
- chosen task
- chosen action
- click target
- attempt/opponent identity if available
- relevant structured versions
- terminal reason

On UNKNOWN or abort save diagnostic screenshot with ROIs.

## Tests

Add deterministic tests for:
- Agenda chooses ArenaBattleOnce when eligible
- no task when token balance unavailable/insufficient
- no action on UNKNOWN
- no action on premium/Gem UI
- exactly one input per observation/transition
- deterministic visible-opponent selection
- start is not blindly retried
- WIN path
- LOSS path
- INCONCLUSIVE path
- return-to-Arena path
- F12 cancellation
- existing Arena/Quest/static tests stay green

Full Windows CI required.

## Live acceptance

The package is not considered complete merely because tests pass.

Completion report must include the exact supervised command that can be run on the real PC to test:

known game state
→ Arena
→ one opponent
→ one battle
→ result
→ return

If a visual calibration value is still missing, report exactly which screenshot/ROI is required. Do not hide that behind generic "live test needed" wording.

## Non-goals

- no QUEST-LIVE-003 work
- no additional static-data reverse engineering
- no Exort binary/code extraction
- no universal scheduler rewrite
- no OCR unless a tiny unavoidable ROI is justified
- no Gem spending
- no Arena production semantics changes unrelated to wiring the loop

## Completion report

Report:
- implemented state graph
- Agenda/TaskRunner behavior
- visual evidence for each state
- files changed
- remaining live calibration dependency
- exact supervised live command
- commit SHA
- pytest count
- Windows Actions run/result
