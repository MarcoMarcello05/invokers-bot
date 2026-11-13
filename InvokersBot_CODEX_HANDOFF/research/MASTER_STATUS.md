# Invokers Bot — Master Status
Updated: 2026-11-13

## Active scope: Arena Integration Sprint 01

The current user instruction supersedes the earlier broad architecture/GUI
expansion. Reuse existing Handoff and Arena V4 components. No additional GUI,
publication workflow or unrelated reverse engineering is part of this sprint.
GitHub is the authoritative code base; completed source/tests/status must be
committed, pushed and verified. Do not commit new private captures, account
manifests, local configs, logs, screenshots or credentials.

## Non-negotiable rules

- Current Arena candidates come only from PlayerArenaModel field 12, reread
  before consequential actions and after refresh/battle; never the pooled cache.
- Own Arena power is the positive manual UserConfig.arena_combat_power. UI may
  corroborate/reject it, never raise it or choose opponents by OCR strength.
- Choose the weakest eligible structured candidate. Search that identity with
  bounded scrolls; never substitute a randomly visible stronger opponent.
- Gems/premium purchases and unknown-dialog confirmations are forbidden.
- AUTO stays OFF. The old AUTO-enable branch is removed from the reused helper.
- PyAutoGUI Fail-Safe stays enabled; F8/STOP/Ctrl+C support safe cancellation.
- Dry-run, nonspending navigation audit, simulation and explicitly activated live
  are distinct. No claim that simulation/offline screenshots prove Windows live.

## Implemented integration

- [x] Compared arena_actor, arena_snapshot, arena_runner, screen_actor_v8,
  autonomy_bridge and policy against the supplied V4 code; retained Handoff
  per-candidate priority instead of V4's visible-first bug.
- [x] Existing bounded top/down search reused for the selected identity only;
  strict full normalized name matching and ambiguous-row/button rejection.
- [x] Arena-only bridge planner, small coherent Arena/resource reader, age/future/
  corruption/duplicate identity checks. Existing state_reader/resource enum reused.
- [x] OBSERVE → PLAN → ACT → VERIFY → RECOVER → REPLAN with explicit deadlines,
  cycle limits, stable-target rechecks, bounded recovery and per-target memory.
- [x] Windows adapter uses the existing screen_actor OCR/template helpers; checks
  foreground window, geometry, known state, fresh/stable controls, formation
  identity, configured power and fixed recognized one-token start cost.
- [x] Victory/defeat needs UI plus exactly one structured offense-counter delta
  and exact token delta. Unexpected resource decrease, including Gems, stops.
- [x] Return to Arena and fresh read before next plan; wins/defeats excluded for
  the current run. Persistent identity cooldown cannot be bypassed by CP changes.
- [x] Optional free refresh only with explicit free label, zero spend, changed
  current list and max budget3; default0, no refresh in dry-run.
- [x] Default dry-run sends no inputs. `--navigate` can open/scroll/inspect formation
  but never start battle. Live requires two explicit gates: activation plus a
  successful matching navigation report no older than five minutes.
- [x] Error codes, JSONL phase journal, reports and best-effort real failure PNG;
  no fake simulation screenshot or false live-success label.
- [x] Python launchers and portable tests; reproducible source-build script reads
  committed HEAD only and excludes private game/runtime data.

## Validation

**Executed: 104 automated tests passed, zero skipped, including 22 Arena sprint
tests.** Two consecutive simulated cycles completed successfully. Real OCR/template
smoke on the existing list/formation images passed, including own power, token
symbol/cost, control-label umlaut variants, and rejection of an unknown blank image.
See [the sprint guide](../docs/ARENA_SPRINT_01.md) for exact commands. Automated coverage includes priority, bounded scroll/missing/ambiguous
identities, stale/missing/corrupt snapshots, UI errors/dialogs/focus loss,
formation/cost/power mismatches, AUTO state, timeouts, premium delta rejection,
free refresh/reread, bounded recovery, stop handling and consecutive simulated
wins/defeats. Full existing regression suite is also required.

Actual offline OCR/template checks use the already versioned Arena-list and
formation screenshots, with no physical input. German control-label OCR variants
are tolerated separately from strict opponent identity. Blank/unknown images
must remain unactionable.

## Real Windows gate — next test

1. Install pinned arena requirements and configure actual game root/manual power.
2. Check 1920x1080 geometry, foreground title and calibration ROIs.
3. Run no-input dry-run, then explicitly requested navigation-only dry-run.
4. Expected: correct lowest suitable field-12 target, correct formation identity,
   own power and one-token cost; no battle/refresh/Gem/token expenditure.
5. Inspect the local report/failure image. Only after this succeeds should an
   explicitly activated **single** live cycle be considered.

Not executed here: physical Windows input/F8 hook, current client navigation,
real AUTO-off/battle/result/return transitions and real reward/resource timings.
Missing recognition or delayed snapshots stop safely, not retries/confirmation.
An actual successful live test is still outstanding.

## Existing foundation retained, not expanded in this sprint

The prior work supplies modular GameState/Planner/Safety/Verification/Memory and
persistent UserConfig, with structural heroes/quests/relics and clan metadata.
Old heuristics missed hero and quest records; current structural readers preserve
unknowns and explicit provenance. Main Six UI ordering is not inferred from ID
sorting. Relic valuation/cost scale and runtime event definitions remain unknown.
The general actor's production registry stays empty; only the narrowly gated
Arena integration runner is eligible for a later explicit Windows live test.

## Evidence and privacy

Source comparison rationale, command guide, test evidence and Open-Source
references: docs/ARENA_SPRINT_01.md. Private uploaded archives stay outside the
checkout/commit. Public tests can run without them using generated fixtures.
A small non-personal token icon template and resource enum suffice for the
source build; complete dumps and account screenshots are not bundled.

## Git/build acceptance

All completed source, tests and this status are committed together. The source build
is generated from that committed HEAD and validated after extraction; it contains
no new private game data. The final chat report records the actual repository,
remote branch, commit SHA and verified push outcome; this file does not assert a
push before the remote check has succeeded.


## Sprint 02 — Windows client-area geometry gate (2026-11-13)

Implemented in `src/arena_windows.py`:
- Win32 GetClientRect + ClientToScreen obtain physical client bounds; focus, visible/non-minimized window, desktop coordinate compatibility and exact calibrated client dimensions are required.
- Baseline HWND/client rectangle is pinned on adapter initialization; changes stop subsequent observations and inputs.
- OCR/template screenshots are cropped to the verified client, keeping existing ROIs client-relative.
- Navigation coordinates are translated from validated client-local points, constrained to expected control ROIs where known; scroll location derives from calibrated list region instead of a hardcoded desktop point.
- F8, STOP file, PyAutoGUI failsafe, premium restrictions, battle gates and arena target selection remain unchanged.
- `tests/test_arena_geometry.py` adds isolated geometry and point-boundary regression tests.

**Validation status:** Source committed to GitHub. Automated tests were **not executed** in this session because the runtime could not clone the GitHub repository (DNS unavailable); Windows physical validation also pending. Do not label this sprint fully validated until tests run. Exact 1920x1080 *client* size is required; maximized window with a smaller client must safely stop, not auto-scale. Test on the user's actual maximized window before allowing navigation.
