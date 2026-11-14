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
