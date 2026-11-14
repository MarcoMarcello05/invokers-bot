# DEVELOPER HANDOFF

## ARENA-LIVE-006B — real-client formation glyph calibration

Status: BEREIT FÜR LIVE-KALIBRIERUNG

006A accepted:
- implementation `d0432a49479578afa0ac7d1847cb0544044c90bf`
- CI fix `f3e0e6d702e155c27d8fad5a6e6b57161ae74efe`
- Windows CI `43650628167`
- `359 passed, 1 warning in 1.31s`

## Goal

Replace synthetic-only formation glyph assumptions with a calibration workflow using real client captures.

The current real reference capture is 1536x864 and showed pre-start formation power 9368.

## Required live evidence

Collect several formation screenshots at unchanged client geometry/DPI while deliberately changing the selected team so the visible own-power number changes.

For every capture record:
- exact visible own-power text
- full client screenshot
- client size
- Windows DPI
- same confirmed formation state

Target:
- collectively cover digits 0..9 and the thousands separator '.'
- preferably each digit appears at least twice across captures
- do not use result-screen power values
- do not use opponent power glyphs unless font/scale parity is explicitly proven

## Calibration implementation

Build a local calibration helper that:
- crops only the configured formation power ROI
- extracts connected glyph components from confirmed real captures
- associates components with the operator-provided exact numeric label
- creates per-glyph canonical templates for 0..9 and dot
- rejects inconsistent samples for the same glyph
- stores only sanitized glyph templates/calibration metadata, never full user screenshots
- records calibration_id, client_size, DPI, ROI, sample count and template digest

Runtime reader remains disabled until:
- all 11 glyphs present
- geometry/DPI exact match
- calibration consistency tests pass
- at least one held-out real formation capture is recognized exactly

## Validation

Use at least one real screenshot NOT used to build templates as hold-out.
Recognition must exactly equal the operator-observed power.

No confidence=1 / validated=true before hold-out parity succeeds.

## Constraints
- no broad OCR
- no result-screen power substitution
- no raw screenshots committed
- no SendInput
- no battle-start enablement
- no replay/Gem refresh
- existing 359+ suite remains green

## Completion report
Report:
- captured power labels
- digit coverage
- real client size/DPI
- calibration ID
- template consistency method
- held-out recognition result
- pytest count
- Windows CI
- remaining live blockers
