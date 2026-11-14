# SHOP MEMORYPACK MAP — 0.62.1621

Date: 2026-11-14

Sources:
- current IL2CPP v39 dump
- fresh PlayerShopModel.dat

Raw account files are not committed.

## PlayerShopModel

Current payload:
- VersionTolerant member count: 19
- current IL2CPP fields: 9
- historical/reserved slots: 2-9, 11-12

Verified current mapping:

| Slot | Field | Current bytes |
|---:|---|---:|
| 0 | LastPurchaseId | 8 |
| 1 | LastPurchaseTime | 16 |
| 2-9 | RESERVED | 0 |
| 10 | ShopHash | 4 |
| 11-12 | RESERVED | 0 |
| 13 | Purchases | 5029 |
| 14 | Offers | 10612 |
| 15 | FirstPurchaseTime | 16 |
| 16 | TotalUsd | 4 |
| 17 | AppliedTriggers | 310 |
| 18 | RewardStateByPurchase | 4 |

Current structural observations:
- Purchases dictionary count = 9
- Offers dictionary count = 104
- RewardStateByPurchase is empty in the supplied snapshot

## Bot value

This is useful for:
- shop offer availability
- purchase history
- purchase-trigger state
- retention/reward program state

However spending decisions are high-risk and must remain behind explicit policy/SafetyGate controls.

The planner may read shop state, but should never infer permission to purchase from availability alone.
