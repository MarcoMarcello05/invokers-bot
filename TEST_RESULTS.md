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
