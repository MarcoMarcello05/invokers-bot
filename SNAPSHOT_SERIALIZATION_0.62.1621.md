# SNAPSHOT SERIALIZATION — 0.62.1621

Date: 2026-11-14

This document records the verified binary envelope of the current Windows aggregate snapshot files.

Sources:
- user-provided current `global-metadata.dat` + `GameAssembly.dll`
- current v39 Il2CppDumper output
- user-provided fresh aggregate snapshot files
- MemoryPack source/generator behavior

Raw player files are not committed.

## Result

The aggregate snapshot files are serialized directly with MemoryPack.

The client storage path uses:
`SimpleFileStore<IAggregateSnapshotDTO>`

Its `DecodePayload(ReadOnlySpan<byte>)` calls:
`MemoryPackSerializer.Deserialize<IAggregateSnapshotDTO>(...)`

No additional compression/encryption layer was identified in the payload path.

## Root union

`IAggregateSnapshotDTO` is a MemoryPack union with these tags:

| Tag | Snapshot type | File |
|---:|---|---|
| 1 | AggregateSnapshotDTO<PlayerModel> | PlayerModel.dat |
| 2 | AggregateSnapshotDTO<PlayerHeroesModel> | PlayerHeroesModel.dat |
| 3 | AggregateSnapshotDTO<PlayerAnimasModel> | PlayerAnimasModel.dat |
| 4 | AggregateSnapshotDTO<PlayerRelicsModel> | PlayerRelicsModel.dat |
| 5 | AggregateSnapshotDTO<PlayerAccessoriesModel> | PlayerAccessoriesModel.dat |
| 6 | AggregateSnapshotDTO<PlayerShopModel> | PlayerShopModel.dat |
| 7 | AggregateSnapshotDTO<PlayerBattleModel> | PlayerBattleModel.dat |
| 8 | AggregateSnapshotDTO<PlayerQuestsModel> | PlayerQuestsModel.dat |
| 9 | AggregateSnapshotDTO<PlayerArenaModel> | PlayerArenaModel.dat |
| 10 | AggregateSnapshotDTO<PlayerGlobalEventsModel> | PlayerGlobalEventsModel.dat |
| 11 | AggregateSnapshotDTO<PlayerInboxModel> | PlayerInboxModel.dat |
| 12 | AggregateSnapshotDTO<PlayerClanModel> | PlayerClanModel.dat |

The first byte of every supplied snapshot matches its file's union tag.

## AggregateSnapshotDTO envelope

The generic DTO is:

`AggregateSnapshotDTO<TModel>`

and is marked `[MemoryPackable(GenerateType.VersionTolerant)]`.

Its three serialized members are:

1. `long Version`
2. `DateTime UpdatedAtUtc`
3. `TModel Data`

MemoryPack VersionTolerant encoding writes:
- object member count,
- one VarInt serialized-length delta per member,
- then member payloads in order.

Every supplied aggregate file validates as:

`[union tag] [object count=3] [delta=8] [delta=8] [delta=DataLength] [Version:int64] [UpdatedAtUtc:DateTime] [Data]`

The third delta exactly equals the remaining byte count in all 12 files.

## Verified snapshot metadata

| File | Tag | Version | UpdatedAtUtc | Data bytes |
|---|---:|---:|---|---:|
| PlayerAccessoriesModel.dat | 5 | 1 | 2026-11-10 08:16:45.079504Z | 738 |
| PlayerAnimasModel.dat | 3 | 2249 | 2026-11-11 12:06:06.213024Z | 524 |
| PlayerArenaModel.dat | 9 | 3587 | 2026-11-13 14:13:31.798272Z | 204292 |
| PlayerBattleModel.dat | 7 | 3554 | 2026-11-13 08:59:25.625272Z | 58579 |
| PlayerClanModel.dat | 12 | 3551 | 2026-11-13 08:59:25.598448Z | 237 |
| PlayerGlobalEventsModel.dat | 10 | 3585 | 2026-11-13 14:05:05.669144Z | 1873 |
| PlayerHeroesModel.dat | 2 | 3526 | 2026-11-12 15:49:12.075104Z | 5959 |
| PlayerInboxModel.dat | 11 | 1770 | 2026-11-11 11:19:52.904256Z | 15 |
| PlayerModel.dat | 1 | 3600 | 2026-11-13 15:08:53.079840Z | 4446 |
| PlayerQuestsModel.dat | 8 | 3558 | 2026-11-13 08:59:25.625712Z | 52461 |
| PlayerRelicsModel.dat | 4 | 3529 | 2026-11-12 15:49:36.578528Z | 24662 |
| PlayerShopModel.dat | 6 | 3581 | 2026-11-13 13:58:23.182824Z | 16029 |

These independent versions/timestamps also confirm that aggregate models are persisted independently rather than as one monolithic player save.

## Inner model format

The inner player models are also MemoryPack objects.

Observed first object-header counts:
- PlayerModel: 53
- PlayerHeroesModel: 10
- PlayerAnimasModel: 5
- PlayerRelicsModel: 3
- PlayerAccessoriesModel: 3
- PlayerShopModel: 19
- PlayerBattleModel: 28
- PlayerQuestsModel: 6
- PlayerArenaModel: 18
- PlayerGlobalEventsModel: 3
- PlayerInboxModel: 2
- PlayerClanModel: 19

Some counts exceed the currently visible backing-field count in `dump.cs`. This is expected for VersionTolerant MemoryPack layouts when explicit member orders contain reserved/removed slots. The generator pads missing order numbers with blank members so old/new schema versions remain compatible.

Therefore: **do not assume declaration order alone for models where header count > visible members.**

## Why the v39 dump matters

Current metadata confirms:
- IL2CPP metadata version 39
- Unity 6000.3.0b1+
- variable-width metadata indices
- 35,395 type definitions
- 240,401 methods

The current v39-compatible dumper successfully generated:
- dump.cs
- script.json
- stringliteral.json
- il2cpp.h
- 200 DummyDll assemblies

This gives enough evidence to recover exact model/member contracts without guessing byte offsets.

## Parser design decision

The parser must be **read-only** and schema-driven.

Phase 1:
1. Parse MemoryPack VarInt.
2. Parse IAggregateSnapshotDTO union tag.
3. Parse the 3-member VersionTolerant envelope.
4. Expose:
   - aggregate type,
   - Version,
   - UpdatedAtUtc,
   - raw Data span.
5. Validate declared Data length against actual remaining bytes.
6. Reject malformed/truncated input safely.

Phase 2:
1. Extract exact MemoryPack member orders/reserved slots for the target models from DummyDll metadata / IL2CPP evidence.
2. Parse selected inner fields.
3. Normalize to AccountState.
4. Expand model-by-model, starting with PlayerModel and Resources.

No writing back to game files is part of this parser.

## Research references

MemoryPack:
- https://github.com/Cysharp/MemoryPack
- https://github.com/Cysharp/MemoryPack/blob/main/src/MemoryPack.Generator/MemoryPackGenerator.Emitter.cs
- https://github.com/Cysharp/MemoryPack/blob/main/src/MemoryPack.Core/MemoryPackReaderWriter.VarInt.cs

The generator confirms VersionTolerant objects write a member count, per-member serialized-length deltas, then payloads. It also pads missing explicit order numbers with blank members.

## Development readiness

The outer aggregate parser is now sufficiently specified for implementation.

Recommended next DEVELOPER package:
- implement only the generic read-only aggregate envelope parser + tests against sanitized fixtures,
- do not yet implement full PlayerModel/Quest/Hero parsing,
- return exact evidence and test results,
- commit and push to main.

Inner model decoding remains ANALYSER work until exact member-order maps are finished.
