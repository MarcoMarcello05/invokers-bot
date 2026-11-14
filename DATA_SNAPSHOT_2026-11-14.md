# FRESH DATA SNAPSHOT — 2026-11-14

Source: user-provided Windows Invokers data snapshot.
Game data itself is **not committed** because the repository is public and raw player/account data may contain private identifiers.

## Archive condition

The uploaded ZIP is truncated at the end and lacks its central-directory index.
However, local ZIP headers allowed recovery of the important early entries.

Recovered successfully: 84 entries plus directory records.
The final log entry is truncated.

Therefore this is a useful analysis snapshot, but **not yet treated as a guaranteed complete directory inventory**.

## Current build evidence

A printable build string inside `aggregate_snapshots/PlayerModel.dat` is:

`0.62.1661`

Official Invokers news confirms Update 0.62 as the current public update family in October/November 2026:
- https://invokers.com/news/66/
- https://invokers.com/news/67/

## High-value recovered files

### Aggregate snapshots

| File | Size |
|---|---:|
| PlayerAccessoriesModel.dat | 761 B |
| PlayerAnimasModel.dat | 547 B |
| PlayerArenaModel.dat | 204,317 B |
| PlayerBattleModel.dat | 58,604 B |
| PlayerClanModel.dat | 260 B |
| PlayerGlobalEventsModel.dat | 1,896 B |
| PlayerHeroesModel.dat | 5,982 B |
| PlayerInboxModel.dat | 36 B |
| PlayerModel.dat | 4,469 B |
| PlayerQuestsModel.dat | 52,486 B |
| PlayerRelicsModel.dat | 24,685 B |
| PlayerShopModel.dat | 16,052 B |

### Offline action/event state

| File | Size |
|---|---:|
| actions/pending_deterministic_actions.dat | 39 B |
| aggregate_events/uncommitted_aggregate_events.dat | 51 B |
| bi_events/pending_bi_events.dat | 2,275 B |

At snapshot time the deterministic pending/action files are effectively near-empty compared with prior offline-action captures.

### Other useful state

| Path | Size |
|---|---:|
| clan/own_clan_snapshot.dat | 26,923 B |
| BattleTapeService/.../metadata/... | 178 B |
| BattleTapeService/.../tape/... | 87,584 B |
| config/meta_server_app_settings/-371610290.dat | 386 B |
| GlobalEvents/challenge_seen/1006.dat | 17 B |
| GlobalEvents/red_badges_instances/* | small state markers |
| GlobalEvents/red_badges_types/* | small state markers |
| LastSeen/daily_counters/LOBBY_SHOWN.dat | 28 B |
| LastSeen/seen/* | small state markers |
| i18n/de_DE.bin | 10,455,575 B |
| i18n/dl_de_DE.bin | 10,628,773 B |

## First observations

1. `PlayerArenaModel.dat` is by far the largest player aggregate snapshot in this capture and contains readable opponent/player-name strings. It remains a strong candidate for structured Arena perception.

2. `PlayerQuestsModel.dat` is large enough to plausibly contain rich quest/account-task state and is a top priority for schema-led decoding.

3. `PlayerRelicsModel.dat` is large and likely suitable for structured gear inventory analysis if its schema is recovered.

4. `PlayerHeroesModel.dat` remains the main roster/development candidate.

5. The dedicated `clan/own_clan_snapshot.dat` is much larger than `PlayerClanModel.dat`; both must be analyzed separately rather than assuming PlayerClanModel contains all clan state.

6. Global-event red-badge and LastSeen marker files may provide very cheap state signals for notifications/claims without OCR.

7. A BattleTapeService recording exists. This may be valuable for battle-state/result research and should be mapped before attempting visual-only battle intelligence.

## Serialization research consequence

Current MemoryPack documentation/source confirms that MemoryPack is a schema-dependent binary format rather than a self-describing format. A reliable parser should therefore be driven by the matching C#/IL2CPP model definitions where possible instead of blind byte guessing.

Research:
- https://github.com/Cysharp/MemoryPack
- https://github.com/SunSi12138/SharpPack

This does **not yet prove** every Invokers .dat file is MemoryPack. Exact serialization must be verified per file/model using game type definitions and controlled before/after comparisons.

## Missing / unresolved

- The ZIP truncation means files after the final recovered local header may be missing.
- No current `static_data` directory was recovered from this uploaded archive.
- Exact schemas/field offsets are not yet established for this clean rebuild.
- Raw player data must stay outside the public repository.

## Analysis priority

1. PlayerModel.dat
2. PlayerQuestsModel.dat
3. PlayerHeroesModel.dat
4. PlayerRelicsModel.dat
5. PlayerArenaModel.dat
6. clan/own_clan_snapshot.dat + PlayerClanModel.dat
7. PlayerGlobalEventsModel.dat + GlobalEvents marker files
8. PlayerBattleModel.dat + BattleTapeService
9. PlayerShopModel.dat
10. Accessories/Animas/Inbox

## Next decision gate

Before giving the DEVELOPER a parser implementation task, ANALYSER should first obtain/inspect the matching current IL2CPP/C# type definitions for the highest-priority models and map each desired AccountState field to its source and confidence.

No developer coding task is issued yet.
