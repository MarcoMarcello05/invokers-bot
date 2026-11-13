# D1 decoding evidence — 2026-11-13

## Reproduction

From `InvokersBot_CODEX_HANDOFF`, with Python 3.12 and Brotli 1.2.0:

```sh
python -m unittest discover -s tests -v
python src/game_state.py --root tests/fixtures --static 'raw/static/static-data.0.62.1655(1).dat' --output /tmp/invokers-game-state.json
```

On the prepared Cloud machine use `/workspace/invokers-env/venv/bin/python`.
No GUI packages, running game, display, external service, or `/mnt/data` aliases
are required. Both original regressions now run through standard unittest discovery.
No release ZIP was produced. Windows game/actor behavior is not validated by these tests.

## Wire format and evidence

Schemas come from `raw/dumps/InvokersDump(2).zip`, under
`InvokersDump/DiffableCs/Shared.Choreograph.Models/Shared/Choreograph/Models/`.
The simplified `schema_catalog.json` lists backing fields, **not** wire indices.
Retired/omitted members retain zero-length entries in VersionTolerant headers.

The bounded parser uses a byte member count, signed VarInt byte lengths, then
field payloads. `0xff` is a null object. Snapshot files start with a model union
tag and a three-field envelope (two Int64s and the actual model). All object and
collection boundaries must be consumed exactly; truncated, negative-length,
wrong-tag, duplicate-key and inconsistent tournament-ID inputs fail closed.
Unknown appended participation fields retain their index and raw hex.

MemoryPack's VarInt and unmanaged Nullable layouts were checked against the
upstream implementation at commit `239ffa0df2f7ccad63d276457557b49e88acae4b`:
`src/MemoryPack.Core/MemoryPackReaderWriter.VarInt.cs` and
`src/MemoryPack.Core/Formatters/NullableFormatter.cs` in Cysharp/MemoryPack.
Nullable<int> is 8 bytes, Nullable<long> 16, Nullable<bool> 2. Only the first
has-value byte and aligned value are meaningful; padding can contain garbage.
The fixture contains nonzero nullable padding, so testing only all-zero null
payloads would miss a real decoding hazard.

| Object | Validated wire positions |
| --- | --- |
| PlayerModel | Resources=9, ResourcesGained=10, ResourcesSpent=11 |
| Resources | RawValues=0; count followed by Int32 key/value pairs |
| PlayerBattleModel | LevelStats=1, LastMetaBattleSetup=2, AsyncPvpPreset=23 |
| LevelStats | Victories=1, Defeats=2, LastBattleTime=3, BestTimeInSeconds=4 |
| TeamPresetData | Formation=0, Slots=1, LeadPosition=4; 2 and 3 omitted |
| TeamPresetSlot | Position=0, HeroInventoryId=1, HeroConfigId=2, AnimaInventoryId=3, AnimaConfigId=4, AnimaPriority=5 |
| PlayerGlobalEventsModel | TournamentsById=0, FinishedNoviceTournament=1, CompletedNoviceTournamentGroupIds=2 |
| TournamentParticipationState | TournamentId=0, JoinedAtUtc=2, ScoringCompleted=3, GroupId=4; derived fields start at 50 |
| ArenaOpponent | Name=0, Level=1, ArenaPoints=3, TeamSetup=4 |
| BattlePlayerTeamSetup | CombatPower=0, PlayerId=1 (validated in opponent teams) |

This is an explicit captured-format profile, not support for every game version.
DateTime outputs preserve the raw .NET ticks and kind; an unspecified kind is
not silently relabeled UTC. Rank value 0 is preserved without inventing semantics.

## Arena preset and power

The attack preset has FormationTypeId=2, LeadPosition=21 (Mid1):

| Position | Hero inventory ID | Hero internal name | Anima inventory ID |
| --- | --- | --- | --- |
| Front1 (11) | 166 | CAM007 | 2 |
| Mid1 (21) | 5 | BST008 | null |
| Back1 (31) | 167 | LTS033 | null |
| Back2 (32) | 2 | IRN026 | 1 |

All four inventory IDs **and** ConfigIds match PlayerHeroesModel. These are the
stored Arena preset, not the first six main-team heroes and not a proven live UI state.

`LastMetaBattleSetup` at absolute offset 46805 is exactly `ff` (null).
ArenaDefenseSetup's dumped schema contains formation/lead/slots, no CombatPower.
The new structural reader decodes CombatPower and player identity for all 31
opponent records; none has the account PlayerId. Thus the supplied battle/arena
captures do not establish current own Arena power. GameState reports null,
status=unknown, with a reason. Historical setup presence also never establishes
current Arena power. We do not infer 9368, sum hero levels, or reuse opponent power.
A non-null own battle-team capture is still needed to validate that decode path.

PlayerArenaModel's original fixture has 10 ArenaOpponent records in wire field 12
and 21 in field 15. The subsequent Windows capture has 10 and 23. User-observed
`_SILVA00` / 6151 correlates field 12 with the current UI list. The role method
is explicitly `user_ui_correlated`, not automated screenshot validation.
`arena_snapshot.read_opponents()` now uses only field 12 structurally. Field 15
is `other_stored`, excluded from actor ranking; exact history/cache semantics
remain unknown. Unicode names are preserved. The old 27-hit ASCII scan pooled
both lists and must no longer be used as evidence of current membership.

The completed A/B/C capture has no persisted model changes on formation
navigation. Own power 9368 is user-observed UI evidence only; LastMetaBattleSetup
is still null. Arena bridge commands remain blocked for lack of verified current
own power. See the private Windows follow-up (intentionally not versioned).

## Events

All six captured records consume their entire dictionary payload (1318 bytes):

| ID | Union type | Points / source scores | Scoring completed |
| --- | --- | --- | --- |
| 935 | Common (1) | 50700 | false |
| 939 | Novice (3) | 86550 | false |
| 991 | GetLegendary (2) | {6:5034, 12:101400, 14:3660, 5:2200, 9:480, 4:520, 7:210, 13:10000, 8:16} | false |
| 1000 | Common (1) | 352 | false |
| 1006 | Common (1) | 240 | true |
| 1007 | Common (1) | 8 | false |

Base fields, nullable bracket IDs, personal/milestone claimed and unlocked reward
sets, reward flags, final/seen/current ranks, Novice time windows and Legendary
per-source scores/shop purchase counts are decoded. Novice completion is false
and completed novice group IDs are empty in the capture.

DailyBestScore (union 4), including 64-bit scores and nested reward dictionaries,
is implemented against the dumped schema and an **assumed** derived-field profile
starting at 50. It is tested with synthetic data only, marked `schema_only`, and
must not drive event actions until a real capture validates its field positions.
Common, Novice and GetLegendary are marked `captured_fixture` for this profile.

Runtime tournament IDs are not static definition IDs. The dumped `Tournament`
contains TypeId, DateDetails, VisualSettings and scoring/reward definitions;
`GetTournamentsResponse` supplies Tournament[] plus CatalogHash. That catalog is
not among the supplied fixtures. PlayerLiveOps holds content IDs/statuses, not
those definitions. Do not guess ID-to-name mappings from participation points,
nearby strings, or the old static pack. Definition remains null with a reason.
Known specialized type IDs (Legendary=51, Novice=52, DailyBestScore=53) are enum
identities, not translated event names; Common type remains unknown.

## GameState and integration boundary

`game_state.py` collects resources, campaign, Arena, events, heroes, enriched
quests, relics, hero names and quest prototypes. Each observation has value,
status, method, source references and an unknown/error reason. Sources carry
original paths, byte sizes and SHA-256 hashes; nested values inherit observation
provenance, with Arena field overrides and structural offsets where available. Current-list role assignment has explicit user-UI provenance.
Legacy hero/quest/relic/static decoders remain labeled heuristic.

Private input copies prevent later reads from silently switching file versions.
A hash recheck rejects files changed during capture; this does **not** prove
that separately persisted game files share one game tick.

The core reads through GameState and optionally exports it with `--state-output`.
The planner bridge consumes/exports the same state while retaining the existing
planner's scoring; missing/corrupt inventories/quests block executable commands.
Actor, premium spending and inventory destruction remain disabled in validation.
D2 (planner policies consuming resources/campaign/events with budgets) remains
separate; this integration does not claim those future policies are implemented.

## Remaining evidence after the completed Windows comparison

The requested A/B/C navigation capture is complete and byte-identical across
all 12 files; do not repeat it expecting a persisted own-power update. See
the local private Windows comparison report (not versioned) for exact results.
A pre-existing raw capture with non-null own team setup or another relevant raw
source would be needed to validate structural own power. No new fight is requested.
Current own power must remain unknown or come from a separately validated,
fresh UI observation; the manually reported 9368 is not a live constant.

A matching cached/runtime tournament catalog is still needed for exact event
names, schedules and definitions. A real union-4 participation snapshot is still
needed before DailyBestScore can be treated as fixture-validated.

## Superseded policy note

The latest user instruction accepts persistent UserConfig.arena_combat_power as
authoritative own power. The raw snapshot field can remain unknown without
blocking planning. Current executable Arena scope and live guards are documented
in [Arena Sprint 01](../docs/ARENA_SPRINT_01.md); no private comparison archive or
account report is part of the commit.
