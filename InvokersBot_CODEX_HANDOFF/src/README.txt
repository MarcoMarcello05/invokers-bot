INVOKERS ARENA AUTOPILOT — INTEGRATION SPRINT 01

Start from the handoff folder. Full Windows setup/test guide:
  docs/ARENA_SPRINT_01.md

No game / invented data:
  python src/arena_runner.py --simulate --cycles 2

Real screen, no inputs by default:
  python src/arena_runner.py --dry-run --config <local.json> --calibration <local.json>

Explicit nonspending navigation audit:
  add --navigate (opens Arena/formation and scrolls; never starts a battle/refresh)

Live requires --live --activate-arena-live --preflight <fresh-success-report>.
Default maximum is one battle. UserConfig own Arena power is authoritative.
Field12 opponents are reread before/after actions. AUTO is never enabled.
Unknown screens/dialogs/costs/stale data stop; no blind confirmation.
F8 / mouse-corner PyAutoGUI Fail-Safe / Ctrl+C / STOP file.

Simulation and offline screenshot checks do not establish Windows live success.
Do not commit local configs, private game snapshots, logs or error screenshots.
