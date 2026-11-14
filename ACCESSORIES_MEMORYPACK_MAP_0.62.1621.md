# ACCESSORIES MEMORYPACK MAP — 0.62.1621

Date: 2026-11-14

Sources:
- current IL2CPP v39 dump
- fresh PlayerAccessoriesModel.dat

Raw account files are not committed.

## PlayerAccessoriesModel

Current payload is VersionTolerant with 3 slots:

| Slot | Field | Current bytes |
|---:|---|---:|
| 0 | LastId | 4 |
| 1 | AccessoriesById | 4 |
| 2 | Randoms | 724 |

Current snapshot:
- AccessoriesById is an empty dictionary
- therefore no real PlayerAccessory instance is available in this snapshot for byte-level cross-validation

## PlayerAccessory schema from current IL2CPP

Current fields:
- InventoryId
- Slot
- Rank
- Rarity
- Faction
- EquippedHeroId
- Level
- IsSeen
- Bonuses

The model is MemoryPack VersionTolerant.

Because the supplied snapshot contains no accessories, exact historical slot order for PlayerAccessory should NOT be treated as byte-verified yet.

Evidence level:
- PlayerAccessoriesModel top-level: HIGH
- PlayerAccessory field inventory/types: HIGH from IL2CPP
- PlayerAccessory exact serialized slot order: NOT YET VERIFIED from live bytes

## Development rule

Do not issue a PlayerAccessory binary parser based only on declaration order.

Wait until either:
- a snapshot contains at least one accessory, or
- formatter/member-order metadata is independently recovered.

This is intentionally conservative.

## Architectural value

Once verified, accessories can provide:
- equipped hero relationship
- slot/rank/rarity/faction
- level
- seen status
- bonus stats

This belongs in the same equipment graph as:
PlayerHero -> AccessoryIdBySlot -> PlayerAccessory.
