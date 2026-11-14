# TEST RESULTS
## 2026-11-14 clean rebuild
Included pure tests:
- config loading
- normalized ROI crop

Windows/client tests still required:
- window discovery
- DPI/client geometry
- DXcam/MSS capture
- real input
- current-template recognition
- complete Arena loop

Verdict: live engine implemented; practical autonomous Invokers run not yet verified because fresh current-game templates are not in the clean rebuild.

## DATA-003 Phase 1

Synthetic pytest cases cover all 12 tags, all VarInt marker widths, length boundaries, malformed/truncated headers and values, trailing bytes, UTC ticks and read-only path input. Command: `python -m pytest -q`.

Execution evidence: direct Git clone in this session failed due to DNS; Windows CI and full-suite results not yet verified. No real user snapshots available in the local runtime. No private fixtures committed.

VarInt reference: https://github.com/Cysharp/MemoryPack/blob/main/src/MemoryPack.Core/MemoryPackReaderWriter.VarInt.cs (ReadVarIntInt32). UTC field accepts UTC or unspecified kind; local kind rejected; exact 100 ns ticks retained separately from Python microsecond timestamp.


### CI verification update

GitHub Actions independently executed the exact DATA-003 Phase 1 implementation commit:

- commit: `ed11fb1f06373c72f394b6d06e35be7f039a70c1`
- workflow run: `43602310052`
- workflow: `tests`
- platform: Windows workflow defined by the repository
- job: `test`
- Test step: SUCCESS
- overall conclusion: SUCCESS

Therefore the earlier developer-session DNS block is no longer a project blocker. DATA-003 Phase 1 is verified by repository CI.

## DATA-003 Phase 2

Added synthetic pytest coverage for selected scalars, reserved and additive slots, all three dictionaries, unknown IDs, malformed headers, lengths, counts, duplicates, trailing bytes and file read-only behavior. Full suite command: `python -m pytest -q`. Local execution and Windows CI outcome not yet verified. No private snapshots committed.

Schema references: PLAYERMODEL_RESOURCES_MAP_0.62.1621.md and RESOURCE_TYPE_ID_0.62.1621.md; upstream MemoryPack collection formatter: https://github.com/Cysharp/MemoryPack/blob/main/src/MemoryPack.Core/Formatters/CollectionFormatters.cs . Timestamp conversion reuses Phase 1 UTC policy and preserves ticks. Revision fields interpreted as signed Int64; reserved historical bytes skipped, additive slots allowed, null dictionaries rejected rather than treated as empty.


### DATA-003 Phase 2 CI verification

GitHub Actions independently executed the exact implementation commit:

- commit: `2a9f1d5b508a321dc7553ea2a899eeff43cc3612`
- workflow run: `43640238110`
- job: `test`
- platform: Windows / Python 3.11.9
- command: `pytest -q`
- result: `89 passed, 1 warning in 0.38s`
- conclusion: SUCCESS

The warning is an existing pytest deprecation in `tests/test_snapshot_envelope.py::test_tags`: an `enumerate` object is passed directly to `parametrize`. It is non-blocking and can be cleaned up opportunistically.

## DATA-003 Phase 3

Synthetic tests added for roster, identity, equipment, skills, reserved/additive slots, nullable timestamps, malformed input and read-only access. Command: `pytest -q`. CI outcome pending; no real user snapshot execution claimed. Native nullable DateTime layout (16 bytes, flag at 0, value at 8) corroborated by archived additional_readers.py. Root collection widths: lobby Int32, seen config Int64, received counts Int64/Int32 inferred from schema and lengths; root slots 6 onward opaque. No private data committed.


### DATA-003 Phase 3 CI verification

- commit: `09a3c33638abbede74ad1063e26baf3b02a87b54`
- workflow run: `43641550108`
- command: `pytest -q`
- result: `129 passed, 1 warning in 0.30s`
- conclusion: SUCCESS

The remaining warning is the existing pytest parametrize deprecation in the envelope test and is non-blocking.

## DATA-003 Phase 4

Synthetic tests cover empty/multiple inventories, identity, unknown enums, nullable ownership, booleans, opaque bonuses, malformed counts/spans/scalars, additive slots, trailing bytes, read-only files and inventory-ID joins. Command: `pytest -q`. CI outcome pending. No real snapshot execution claimed; no private fixtures committed.

Sources: RELICS_MEMORYPACK_MAP_0.62.1621.md; archived memorypack.py Nullable<int> reader corroborates the native 8-byte layout (flag at byte 0, value at byte 4). Bonus and Randoms contents are not validated internally, only bounded by the outer slot lengths. Additional root/relic slots skipped by length.

### Phase 4 verification

Windows run 43642110801, commit ca2dc5bdc3251b3a8b05724ef893a90d7093e08a: pytest -q, 174 passed, 1 warning in 0.47s (verified job logs).

## Live AccountState foundation

Synthetic observer tests for refresh, invalidation, corrupt/missing files, freshness, immutability and throttling. CI pending. No real Windows client available; no game files written. Existing CV flows remain separate from future account-driven goal eligibility.


### Live AccountState CI verification

- commit: `371ab08015cb0bd9ec3e2a3ca4723a187133e80f`
- workflow run: `43642665870`
- result: `179 passed, 1 warning in 0.39s`
- conclusion: SUCCESS

ANALYSER review note: CI is green, but current post-input invalidation is intentionally conservative to the point of being operationally harmful. It marks all tracked aggregates awaiting_change after any real input. The next live-runtime package must replace this with action-scoped invalidation and verification expectations.

## LIVE-001A

Added synthetic observer/evidence and mocked engine tests: scoped refresh, unrelated freshness, four verification modes, invalid contracts, corrupt sources, missing baseline, timeout, cancellation, no chained action after failure and read-only files. Command: `pytest -q`. CI pending; actual client not exercised. See LIVE_ACCOUNTSTATE.md for legacy behavior and assumptions.


### LIVE-001A CI verification

- commit: `43f665f37ec15b7d4b448f785184274e76b721ce`
- Actions run: `43643095273`
- command: `pytest -q`
- result: `215 passed, 1 warning in 0.75s`
- conclusion: SUCCESS

ANALYSER code review confirms scoped invalidation and explicit verification behavior match the architecture contract. Note: the developer report expected 214 tests; CI actually discovered and passed 215.

Live caveat: `config/arena.json` currently requires `player` to change for the start-battle action. This must be validated against real-client save timing before treating the five-second timeout as production truth.

## LIVE-001B

Synthetic tests for eligibility, freshness, reserve, missing navigation/data, deterministic sanitized trace, exact/decreased resource predicates and blocked runtime inputs. Full pytest CI pending. No real client test.


### LIVE-001B CI verification

- commit: `6c12332548ff3c0e6d0d536fda7250156732f0ad`
- Actions run: `43643490286`
- result: `242 passed, 1 warning in 0.95s`
- conclusion: SUCCESS

ANALYSER review:
- Goal gating is AccountState-driven.
- blocked Goal paths are covered by no-input regression tests.
- semantic resource verification rejects unchanged/wrong-direction token values.
- Arena-specific policy remains outside BotEngine.

## ARENA-LIVE-002

Synthetic arena root, malformed members, opaque entry hashes, observer, wheel contract and traversal termination tests added. CI pending. No client or private data exercised.


### ARENA-LIVE-002 CI verification

- commit: `84eadeb436e707c3e9157252fc6b3f66c5fa009c`
- Actions run: `43644672629`
- result: `269 passed, 1 warning in 0.66s`
- conclusion: SUCCESS

ANALYSER review confirms:
- bounded traversal safety conditions
- STALE cancellation on Arena source change
- F12/UNKNOWN/unexpected-screen exits
- visual overlap de-duplication
- no AccountState invalidation from wheel scrolling
- live calibration intentionally disabled by default

## ARENA-LIVE-003

Synthetic opponent field, malformed identity/power, fingerprint, cache invalidation and passive probe tests. Windows CI pending. No game input or raw snapshots used.

## ARENA-LIVE-003 fixture repair

Original run 43645108504 failed (275 passed, 3 failed, 1 warning). The fixture used raw unsigned single-byte member sizes instead of signed MemoryPack VarInt. Upstream reference: https://github.com/Cysharp/MemoryPack/blob/main/src/MemoryPack.Core/MemoryPackReaderWriter.VarInt.cs (WriteVarInt(int), ReadVarIntInt32). Reader unchanged. Independent literal wire tests and nested size boundary regressions added; real current client snapshot validation remains pending. New Windows CI pending.


### ARENA-LIVE-003 final acceptance

- commit: `bca993439fae721158939b22f2e92559c39e6ffc`
- Actions run: `43645342539`
- result: `289 passed, 1 warning in 0.99s`
- conclusion: SUCCESS
- fixture VarInt regression coverage added at 127/128/255/256/32767/32768 and nested large-object cases.

## ARENA-LIVE-004

Synthetic tests cover provenance gates, deterministic ratio and tie-break, policy bounds, stale source, cache invalidation and small ROI diagnostic contract. Full Windows CI pending. Live A/B/C and UI parity not executed.


### ARENA-LIVE-004 code/CI acceptance

- commit: `047c99ac78ddc377d09e9beddabe8e4cb23ed478`
- Actions run: `43645551854`
- result: `304 passed, 1 warning in 0.69s`
- conclusion: SUCCESS
- ranking remains diagnostic only until own Team Power is exact + validated on the real client.

## ARENA-LIVE-005A

Synthetic historical-profile stats and malformed wire, single-channel, outcome/conflict, defense/reset, exact spend, delayed/timeout and no-replay tests. Full Windows CI pending. No live fights performed.


### ARENA-LIVE-005A acceptance

- commit: `779d5b4106f031b24fa5361763ac716b206eabcf`
- Actions run: `43646254157`
- result: `323 passed, 1 warning in 1.06s`
- conclusion: SUCCESS
- no battle start or replay path introduced.

## ARENA-LIVE-005B

Synthetic identity/ambiguity, malformed entry, immutable baseline, stale pre-start, wrong-attempt rejection, duplicate terminal record and raw baseline exclusion tests. CI pending.


### ARENA-LIVE-005B acceptance

- commit: `4b4ced808b9fb00553c86e81c02dbc46a6467d63`
- Actions run: `43646510502`
- result: `329 passed, 1 warning in 0.71s`
- conclusion: SUCCESS
