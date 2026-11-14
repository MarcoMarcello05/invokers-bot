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
