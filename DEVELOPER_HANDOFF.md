# DEVELOPER HANDOFF

## Current package: DATA-003 Phase 1 — read-only aggregate envelope parser

Status: BEREIT ZUR ENTWICKLUNG

Read first:
- MASTER_CHECKLIST.md
- MASTER_STATUS.md
- PROJECT_WORKFLOW.md
- IL2CPP_SCHEMA_0.62.1621.md
- SNAPSHOT_SERIALIZATION_0.62.1621.md

### Goal

Implement a small, read-only parser for the common MemoryPack aggregate snapshot envelope. Do **not** implement full inner PlayerModel/Hero/Quest parsing yet.

### Required behavior

Input: bytes/path for one aggregate snapshot .dat.

Output model should expose at minimum:
- union_tag
- aggregate/model name
- version (int64)
- updated_at_utc
- data/raw payload span or bytes
- total file size
- payload size

Supported union tags:
1 PlayerModel
2 PlayerHeroesModel
3 PlayerAnimasModel
4 PlayerRelicsModel
5 PlayerAccessoriesModel
6 PlayerShopModel
7 PlayerBattleModel
8 PlayerQuestsModel
9 PlayerArenaModel
10 PlayerGlobalEventsModel
11 PlayerInboxModel
12 PlayerClanModel

### Format

Verified root:
[MemoryPack union tag]
[VersionTolerant object header: member count=3]
[varint delta 8]
[varint delta 8]
[varint delta DataLength]
[int64 Version]
[DateTime UpdatedAtUtc]
[Data bytes]

Implement MemoryPack VarInt decoding according to the upstream source linked in SNAPSHOT_SERIALIZATION_0.62.1621.md.

### Safety

- Read-only only.
- No game input.
- No modification of LocalLow files.
- Reject malformed, truncated or unsupported-tag inputs with clear errors.
- Never silently accept a mismatched declared payload size.

### Tests

Create synthetic/sanitized fixtures sufficient to cover:
- all 12 union tags
- small payload
- payload length encoded as Int16 VarInt
- malformed member count
- unknown union tag
- truncated Version
- truncated DateTime
- declared Data length > remaining bytes
- extra trailing bytes
- valid DateTime conversion

If existing raw user snapshots are available only locally, use them for local verification but do not commit player/account data.

### Acceptance criteria

1. Parser correctly identifies all 12 aggregate types.
2. Version and UpdatedAtUtc decode correctly.
3. Data-length validation is strict.
4. No mutation APIs exist.
5. Tests pass on Windows CI.
6. Update TEST_RESULTS.md and MASTER_STATUS.md.
7. Commit and push all completed work to the existing main branch.
8. Report exact commit SHA, push result, test command and test result.

### Out of scope

- Full PlayerModel field parsing
- Hero/Relic/Arena/Quest nested decoding
- writing snapshots
- manipulating game state

The ANALYSER will provide a second package after exact inner MemoryPack member-order maps are finished.
