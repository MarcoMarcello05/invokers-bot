# RELICS MEMORYPACK MAP — 0.62.1621

Date: 2026-11-14

Sources:
- current IL2CPP v39 dump
- fresh PlayerRelicsModel.dat
- PlayerHeroesModel.dat cross-reference

Raw user/account files are not committed.

## PlayerRelicsModel

Current model is VersionTolerant with 3 slots:

| Slot | Field | Current bytes |
|---:|---|---:|
| 0 | LastId | 4 |
| 1 | RelicsById | 23926 |
| 2 | Randoms | 724 |

Snapshot facts:
- LastId = 361
- RelicsById contains 180 PlayerRelic entries

## PlayerRelic

Current PlayerRelic is VersionTolerant with exactly 9 slots and no observed reserved gaps.

| Slot | Field | Type |
|---:|---|---|
| 0 | InventoryId | int32 |
| 1 | Slot | RelicSlot / int32 |
| 2 | Rank | RelicRank / int32 |
| 3 | Rarity | RelicRarity / int32 |
| 4 | Set | RelicSet / int32 |
| 5 | EquippedHeroId | Nullable<int> |
| 6 | Level | int32 |
| 7 | IsSeen | bool |
| 8 | Bonuses | List<PlayerRelicBonus> |

The first observed relic confirms member lengths:
4, 4, 4, 4, 4, 8, 4, 1, variable Bonuses payload.

## Cross-model integrity

Hero RelicIdBySlot references were checked against the RelicsById inventory.

For the observed Hero InventoryId 1, all eight equipped relic references resolve to real PlayerRelic inventory IDs.

This proves the bot can join:
PlayerHero -> RelicSlot -> PlayerRelic

without OCR.

## Architectural value

Structured relic state can drive:
- equipped/un-equipped detection
- slot-aware loadouts
- rank/rarity/set/level evaluation
- storage inventory
- safe replacement planning
- protection from accidental sell/crush
- account-wide gear ownership relationships

Full PlayerRelicBonus decoding is intentionally deferred until its own schema is mapped.

## Development sequencing

Relic parsing should follow PlayerHero parsing, because cross-model linking and protection logic benefit from both datasets being available together.

No implementation handoff is issued yet while DATA-003 Phase 2 is in progress.
