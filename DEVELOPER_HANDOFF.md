# DEVELOPER HANDOFF

## NEXT PHASE — LIVE CLIENT PIVOT

Status: BLOCKIERT BIS USER WIEDER AM WINDOWS-CLIENT IST

ARENA-LIVE-006C accepted:
- commit `d3a1bf33e2074d534e132dd3dcb4da30f06df3dc`
- Windows CI `43652958684`
- `376 passed, 1 warning in 1.35s`

## Strategy change

Do NOT add another large offline architecture layer.

The next objective is a real-client Arena path:
1. calibrate current UI states/templates/ROIs,
2. validate Home -> Arena -> list -> formation navigation,
3. solve OwnPower pragmatically for MVP,
4. run shadow/dry observation against the live client,
5. enable one supervised low-risk action,
6. then supervised Arena start using the existing StartIntent/verification contract.

## While user is mobile

No new major implementation package is authorized.

Allowed only:
- inspect/review existing code for obvious defects,
- keep CI green,
- documentation corrections,
- prepare tiny test scaffolding that directly supports the next live session.

Do not:
- expand planner/GOAP/utility architecture,
- add more domain abstractions,
- implement Campaign yet,
- enable battle start,
- enable replay or Gem refresh,
- invent UI coordinates/templates without real captures.

## Next live-session checklist

Capture/validate:
- client size and Windows DPI
- Home state template/ROI
- Arena entry target
- Arena list state/template
- opponent card/list ROI
- formation state/template
- own-power solution (temporary provenance-bound fixed value or calibrated tiny ROI)
- battle/loading state
- victory/result state
- back/next-opponent path
- popup/loading/error cases encountered

Then run:
- dry observation only,
- one supervised navigation click,
- one supervised Arena attempt,
- result verification,
- no blind retry.

The project is now integration-bound, not architecture-bound.
