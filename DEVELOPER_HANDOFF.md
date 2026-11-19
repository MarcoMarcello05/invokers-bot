# DEVELOPER HANDOFF

## AUTOPILOT-MVP-001 — first real closed-loop Arena run

Status: BEREIT ZUR ENTWICKLUNG

## Strategic pivot

Pause QUEST-LIVE-003 static-definition decoding.

Reason:
The project has accumulated strong data/schema infrastructure, but the highest-risk unknown is no longer data decoding. It is whether the existing capture + vision + SendInput + verification stack can complete a full useful task autonomously in the real client.

Priority is now:
**working end-to-end loop first, intelligence second.**

Do not delete Quest work. Keep it parked and reusable.

## Goal

Build the smallest safe real Arena autopilot slice that can execute:

HOME / known state
→ enter Arena
→ identify a valid visible opponent card
→ select one opponent
→ reach formation / pre-battle state
→ start exactly one offense battle
→ observe battle/result state without fixed-duration sleeps
→ classify WIN / LOSS / INCONCLUSIVE
→ return to Arena
→ verify the attempt through existing structured Arena evidence where available

This package is successful only if the path is wired end-to-end and ready for a supervised live client test.

## Deliberate simplifications

For MVP-001:
- do NOT require optimal opponent ranking
- do NOT block on exact own Team Power
- do NOT require full opponent-list traversal
- do NOT require Quest semantics
- do NOT require universal scheduler
- do NOT require static-data decoding

Use one clearly visible, confidently detected opponent card.
Selection policy may be deterministic and intentionally simple (for example first safely recognized eligible visible card).

The objective is proving the closed loop, not winning every battle.

## Safety

Hard gates:
- Arena offense only
- require structured Arena token balance >= 1 and fresh enough for existing policy
- cost is exactly 1 verified Arena token
- NEVER spend Gems
- if any Gem/premium confirmation is detected or action path is ambiguous: abort
- UNKNOWN visual state = no input
- F12 remains global stop
- no blind retry of Start
- one attempt ownership at a time
- no replay on inconclusive outcome
- no manual Arena refresh
- no destructive inventory/account actions

## Architecture

Use the existing deterministic loop:

capture
→ classify current visual state
→ choose exactly one allowed transition
→ SendInput
→ immediately re-observe
→ verify transition
→ continue or recover

No macro-style fixed click sequence.

Prefer existing DXcam/OpenCV/ROI/template infrastructure.
OCR remains optional and should not be needed for this MVP unless a tiny numeric/text ROI is the only robust evidence.

## Required visual states

Wire only the minimum state graph needed:
- HOME or known launch state
- ARENA_LIST
- OPPONENT_SELECTED / FORMATION
- BATTLE_RUNNING or battle-start evidence
- RESULT_WIN
- RESULT_LOSS
- ARENA_RETURNED
- LOADING / transition
- UNKNOWN
- PREMIUM_CONFIRMATION / unsafe modal if distinguishable

State recognition should be stable over multiple frames where appropriate.

## Arena opponent choice

For this MVP, opponent choice must be simple and observable.

Allowed:
- first/highest-confidence visible opponent card
- existing opponent card template/ROI if already available
- deterministic card index tied to current viewport

Not required:
- own-power ratio
- global opponent ranking
- scrolling all opponents

Keep the existing smart ranking code intact for later use.

## Start and battle monitoring

Reuse current Arena attempt coordinator:
- immutable attempt/opponent identity
- soft start evidence
- progress/liveness updates
- inactivity watchdog
- absolute hard cap
- late result acceptance where safe
- no fixed fight duration
- exact spend/result reconciliation when snapshots arrive

Do not reintroduce fixed 60-second battle waits.

## Recovery

Bounded recovery only:
- if expected visual transition does not appear, re-observe
- one safe back/close recovery only where state is known
- if identity/state becomes ambiguous: terminal INCONCLUSIVE + screenshot/trace
- never blindly re-click Start

## Diagnostics

For every live decision record:
- visual state
- confidence/evidence
- selected action
- target coordinates/ROI
- pre/post AccountState versions relevant to Arena
- attempt ID/opponent ID if known
- terminal reason

On UNKNOWN/abort save a diagnostic screenshot with relevant ROIs overlaid.

## Tests

Add deterministic offline tests using synthetic/replay frames where possible:
- state transition graph
- no action on UNKNOWN
- no action on premium/Gem confirmation
- one-action-per-observation
- start not retried blindly
- first visible card deterministic selection
- result WIN/LOSS paths
- result INCONCLUSIVE path
- return-to-arena verification
- F12/cancel propagation
- existing Arena coordinator tests remain green
- existing Quest/static tests remain green

Full Windows CI required.

## Important non-goals

Do NOT continue QUEST-LIVE-003 in this package.
Do NOT decode more static data.
Do NOT create a universal planner.
Do NOT optimize opponent ranking.
Do NOT modify Arena token semantics.
Do NOT add auto-refresh.

## Completion report

Report:
- exact end-to-end state graph implemented
- visual evidence used for each transition
- files changed
- what remains dependent on live calibration
- whether the path can be launched in supervised live mode
- commit SHA
- full pytest count
- Windows Actions run/result
- exact command for the first supervised real-client test

