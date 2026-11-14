# ANALYSER 2.0 – Restart Preparation

Date: 2026-11-14

## Status

- GitHub access: VERIFIED (repository readable; connected account has push/admin permissions).
- Active default branch: `main`.
- Current main tree SHA: `d363ef72e3cde80e05cc3829ac09f0137acedc5f`.
- Current repository inventory: 123 files, 21 directories.
- Top level: `.github/`, `.gitignore`, `InvokersBot_CODEX_HANDOFF/`, `README.md`.
- Recovery branch created before any destructive work:
  `archive/pre-analyser-2.0-restart-2026-11-14`.
- No files have been deleted from `main`.
- Destructive reset is BLOCKED pending explicit user approval.

## Reset scope prepared

After explicit approval, the active development branch should be rebuilt as a clean baseline. The old code, documentation, tests, calibration, generated caches, binary dumps, screenshots, configs and prior sprint material should not remain in the active tree merely because they existed before.

The archive branch above preserves the complete current Git state. The existing Git history should not be rewritten or destroyed.

Proposed clean baseline files after reset:

- README.md
- MASTER_STATUS.md
- MASTER_PLAN.md
- RESEARCH.md
- GAME_KNOWLEDGE.md
- ARCHITECTURE.md
- DECISIONS.md
- DEVELOPER_HANDOFF.md
- TEST_RESULTS.md
- .gitignore

No bot implementation should be added during the analysis phase.

## Invokers research – confirmed

Official / primary sources:

1. Invokers official Arena guide
   https://invokers.com/guides/arena/
   - Arena is asynchronous PvP.
   - Opponent Invokers, Titans, levels and Team Power are visible before battle.
   - Up to four Invokers/Titans can be used for offense.
   - Battles start in Auto Mode.
   - Arena Tokens regenerate and opponent refreshes have explicit rules.
   - Team Power is only an approximate strength indicator.

2. Invokers official Arena Strategy guide
   https://invokers.com/guides/arena-strategy/
   - Matchups depend on team composition, elements, stats, positioning and Titan order.
   - Static one-number heuristics are insufficient for optimal decisions.

3. Google Play / PC listing
   https://play.google.com/store/apps/details?id=hitzone.anima.spirit.guardians
   - Package: hitzone.anima.spirit.guardians.
   - Android and Windows availability confirmed.
   - Listing was updated 2026-10-27 when checked.

4. HitZone Terms of Use
   https://hit.zone/en/terms/terms-of-use.html
   - Automated systems and automated/unfair play can create account-sanction risk.
   - Therefore live unattended automation cannot be treated as rule-compliant by default.

5. Existing Invokers automation product (Exort)
   https://exort.eu/en/faq/
   - Confirms that Windows UI automation for Invokers is technically feasible.
   - Product claims to read game state and operate the UI without changing game values.
   - The vendor explicitly warns automation can violate game Terms and may lead to bans.
   - Treat as competitive/architectural evidence, not as permission.

## Comparable automation projects inspected

### GameScreenAgent
https://github.com/zZrkny/GameScreenAgent

Observed implementation:
- OpenCV template matching.
- Explicit game-state enum.
- State priority.
- ROI support.
- Multi-scale matching.
- UNKNOWN -> WAIT fallback.
- Decision layer separated from vision and action layer.

Transfer to Invokers:
- Strong fit for UI-state detection and recovery.
- Should not be copied directly; architecture pattern is useful.
- Current implementation is simple and lacks structured local game-state fusion.

### gbf-tani
https://github.com/Falllll/gbf-tani

Observed implementation:
- Screen-state driven loop.
- Configuration and reference images separated from runtime logic.
- Runtime limit/failsafe philosophy.
- Modular page/finder/battle abstractions.

Transfer to Invokers:
- Useful for declarative state/action definitions and safe execution boundaries.
- Resolution/DPI sensitivity remains a weakness.

### Osprey
https://github.com/wazgf1f/osprey

Observed implementation:
- Windows-specific screen capture and SendInput.
- Per-monitor DPI awareness.
- Region capture.
- Multi-scale / coarse-to-fine template matching.
- NMS.
- Dry-run default, panic key, stop file, runtime cap.
- Small state-machine/task interface.

Transfer to Invokers:
- High-value reference for Windows capture, DPI handling, diagnostics, dry-run safety and efficient matching.
- New/alpha project, so use ideas selectively rather than taking a hard dependency.

### RSLBot
https://github.com/Harkame/RSLBot

Observed implementation:
- Image-treatment based Raid automation.
- Tesseract dependency.
- Fixed supported resolutions.

Transfer to Invokers:
- Demonstrates conventional CV/OCR approach.
- Fixed-resolution assumptions are a design smell for our use case.
- OCR should remain targeted, not central.

### pywinauto
https://github.com/pywinauto/pywinauto

Observed implementation:
- Win32/UIA control discovery and input support.

Transfer to Invokers:
- Worth probing for launcher/window management.
- Likely limited inside a custom-rendered Unity game canvas.
- Use for window discovery/activation where possible, not as the main game-state sensor.

## Initial architecture recommendation

Use a hybrid observation pipeline, in this priority order:

1. Local structured game files, read-only.
2. File-change/event observation.
3. Window geometry + DPI + client-area normalization.
4. ROI-based computer vision.
5. Template matching with per-state thresholds and optional multi-scale search.
6. OCR only for fields not obtainable structurally or by simpler visual cues.
7. Raw fixed coordinates only behind a normalized coordinate transform and only when verified immediately before action.

Core loop:

Capture/Read -> Fuse observations -> Classify state -> Decide -> Safety gate -> Act -> Verify -> Recover/Wait.

The state classifier must be allowed to return UNKNOWN. UNKNOWN must never cause speculative clicking.

## Key new design decision

Do not build the first MVP as a generic all-mode bot.

First prove one complete read-only-to-action workflow with:
- deterministic state recognition,
- explicit preconditions,
- explicit post-action verification,
- timeout/recovery behavior,
- logging and screenshots on failure.

Because current Terms create a live-automation compliance risk, the first implementation target should be a read-only/dry-run diagnostic and decision system. Live action should be a separately gated capability only after the user explicitly accepts the rule/account risk or obtains permission.

## Data requested from user, priority order

P0:
- Fresh Windows game directory snapshot from:
  `%USERPROFILE%\AppData\LocalLow\Hit_Zone\Invokers`
- File listing with sizes and modification times.
- Fresh copies of high-value `aggregate_snapshots` files.
- Current `static_data` file(s).
- 1920x1080 or native-resolution screenshots of:
  - home/main screen
  - Arena opponent list
  - Arena formation screen
  - battle start
  - battle running
  - victory
  - defeat
  - common popups/errors
- Windows display resolution and scaling percentage.

P1:
- BEFORE/AFTER file snapshots for one controlled action at a time.
- Short screen recording of one complete Arena cycle.
- Game/launcher executable/window title information.
- Current game version/build number.

P2:
- Additional modes only after the first end-to-end path is proven.

Do not upload account credentials, tokens, personal identifiers or unnecessary private player data.

## Prioritized analysis plan

1. CLEAN BASELINE – await reset approval, then rebuild documentation-only repository.
2. DATA INVENTORY – catalog fresh user-provided local files and screenshots.
3. STRUCTURED STATE – determine which bot decisions can come from snapshots/events.
4. WINDOW/CAPTURE – benchmark Windows capture, window detection and DPI normalization.
5. VISION – define minimal state templates/ROIs and confidence thresholds.
6. STATE FUSION – combine files + CV into one typed observation model.
7. DRY-RUN MVP – recognize one complete Arena flow without sending input.
8. VERIFY/RECOVERY – failure screenshots, timeouts, UNKNOWN handling, diagnostics.
9. LIVE-GATE REVIEW – check rules/permission before enabling unattended actions.
10. HANDOFF – create one cohesive developer package with tests and completion criteria.

## Current blockers

- Destructive repository reset: requires explicit user confirmation.
- Fresh data set: not yet supplied under the new clean-room process.
- Live unattended automation: Terms/rule compliance risk must be acknowledged or clarified.

## Completion criteria for analysis phase

Analysis phase is complete when:
- clean baseline exists,
- research is documented with sources,
- fresh game-data inventory is complete,
- chosen capture/state architecture is justified,
- one read-only end-to-end Arena state path is specified,
- developer handoff has objective tests and acceptance criteria,
- unresolved blockers are explicitly documented.
