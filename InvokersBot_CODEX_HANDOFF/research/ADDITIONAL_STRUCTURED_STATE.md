# Additional structured-state research — 2026-11-13

Sources: shipped `raw/dumps/InvokersDump(2).zip` C#/IL2CPP schema outputs,
original `tests/fixtures/*.dat`, and all three snapshots in
an optional private comparison archive (not versioned).

Implementation: `src/additional_readers.py`. Validation:

```sh
python -m unittest discover -s tests -p test_additional_readers.py -v
```

Twelve tests pass on real fixtures and bounded corruption cases. These are pure
readers: no game clicks, spending, claims, or snapshot modifications.

## Heroes: thirty records, not twenty-nine

`PlayerHeroesModel` wire fields 0/1/2 are LastId, HeroesById and LobbyHeroIds.
The dictionary contains **30** entries in both original and Windows snapshots.
The previous primitive-signature scanner returned 29 because hero inventory
ID **176** has ConfigId **35**, outside its assumed normal config-ID range.
The structural reader retains that record without inventing a static definition
or treating it as an eligible training/sacrifice target.

Validated PlayerHero wire fields:

| Field | Meaning |
| --- | --- |
| 0..5 | InventoryId, ConfigId, Rank, Level, Experience, TotalExperience |
| 6,7,8 | Locked, InStorage, CharacterMarker |
| 9 | nullable RecentBattleTime (aligned 16-byte nullable DateTime) |
| 11,12 | RelicIdBySlot and AccessoryIdBySlot |
| 21 | SkillLevels; sequential UpgradeableSkill pairs (SkillKind:Int32, Level:Int32) |

Dictionary key and InventoryId must match. Ascending/unique keys, object bounds,
nullable flag/width and skill entries are checked. Reserved/late fields are
retained by index/raw hex rather than guessed as awakening or skin fields.
The legacy fields needed by planner/static-name integration are preserved.

### Serialized order cannot establish the Main Six

HeroesById is a **SortedDictionary**, so serialized IDs begin
`[1,2,3,5,9,17,...]`. This does not prove the first six heroes in the current UI.
LobbyHeroIds is empty in both real datasets and is not a UI sorting declaration.

The client dump independently confirms mutable UI sorting:
`Client/UI/HeroesGrid/Filters/HeroFilterDialogView.cs` exposes
HeroLevelSortingButton, HeroPowerSortingButton, HeroRankSortingButton and
HeroRaritySortingButton. `HeroFilterDialogController` receives IDeviceStorage
and a savingStateKeyPrefix; client sorting/filter preferences can affect UI order.
The dump contains signatures, not the runtime preference values.

`read_hero_roster()` therefore returns `serialized_order_ids`, but
`ui_order_ids=None` with an explicit unknown reason. A validated UI order or
explicit persistent UserConfig main-team inventory IDs must resolve Main Six;
never silently relabel dictionary order as UI order.

## Relics: equipped state and exact bonus payloads

`PlayerRelicsModel.RelicsById` is wire field 1. All 313 original records and all
180 Windows records decode structurally, with dictionary key/InventoryId checks.

PlayerRelic fields 0..8 are InventoryId, Slot, Rank, Rarity, Set,
Nullable<EquippedHeroId>, Level, IsSeen and Bonuses. PlayerRelicBonus fields
0..4 are Id, CharacterStatBonus, F64.Value, Level and F64.RollsSum.
Enums come from the dumped RelicSlot, RelicRarity, RelicSet and CharacterStatBonus.
Raw signed Int64 F64 fields are preserved exactly. Decimal scaling is not declared
fixture-validated, and this reader does **not** turn bonus presence into a value
ranking or an upgrade/sell cost model.

Original relic ID1 is Helmet/Health/Rare, equipped to hero1, level5. Its first
bonus is HealthFlat with Value.Raw=1975684956160. The original snapshot contains
56 equipped relics. Every hero RelicIdBySlot cross-link agrees with the relic's
slot and EquippedHeroId in the fixtures. This supports explicit equipped-item
protection and account-improvement fingerprints without permitting item sales.

Unknown rarity/stat IDs remain explicit unknown names rather than being coerced
to low value. Equipped, unknown or unevaluated items must stay protected by Safety.

## Clan and boss preparation

The Windows ZIP additionally supplies PlayerClanModel, union tag12.
Validated top-level field18 is PlayerClanBoss2State; its fields are DayUtc,
ReplaysUsed, StartedDifficulties, Chests and BestDamageByDifficulty.

All three copies contain:

- clan membership role20 (Member), abbreviation retained locally, omitted from public evidence;
- Boss2 day ticks corresponding to 2026-11-13, replays used0;
- no started difficulties, no saved chest records, no saved per-difficulty damage;
- null DailyActivity, PendingActivityChest, DailyBossActivity and PendingBossChest.

Membership fields0..4 are ClanId, Role, JoinedAtUtc, nullable CanParticipateAtUtc,
ClanAbbreviation. DateTime raw ticks/kind are retained; unspecified kind is not
silently relabeled UTC. No account/user filesystem paths are included in the API.

Non-null daily activity/chest variants are bounded and retained as undecoded
fields until a real fixture validates them. Current boss health is **not a field**
of PlayerClanBoss2State and remains explicitly unknown. Zero replays/empty lists
are genuine decoded values, but they do not establish a boss attack's energy/key
cost, navigation, or reward eligibility. Boss actions need separate cost and
verification evidence.

## Events and remaining limits

No new DailyBestScore union4 or runtime Tournament catalog is present in the
additional ZIP. Existing Common/Novice/GetLegendary fields remain usable, but
exact event definitions/name/schedule mapping still needs the runtime catalog.
No source in this research establishes current own Arena power: user-configured
Arena power must carry user-config provenance, not an OCR/structured claim.

The generated C#/IL2CPP files contain method signatures with empty bodies; they
cannot establish arbitrary game formulas merely by naming a calculation method.
Do not derive relic valuation, hero combat power, upgrade costs, UI order or boss
eligibility from unproven arithmetic over these decoded fields.

## ArenaBattleStats counter profile for verification

`read_arena_stats()` decodes PlayerArenaModel field10 as a VersionTolerant
ArenaBattleStats object. Wire slots0..3 are retired/empty. The captured profile:

| Wire index | Counter | Original | Windows |
| --- | --- | --- | --- |
| 4,5 | DefenseBattlesThisWeek / wins | 8 / 0 | 10 / 0 |
| 6,7 | DefenseBattlesLastWeek / wins | 0 / 0 | 0 / 0 |
| 8,9 | TotalOffenseBattles / wins | 13 / 13 | 13 / 13 |
| 10,11 | TotalDefenseBattles / wins | 8 / 0 | 10 / 0 |
| 12 | MaxLeagueReached | 12 | 12 |
| 13 | TotalBattlesByLeague | {11:20,12:1} | {11:22,12:1} |
| 14,15 | AttackBattlesThisWeek / wins | 13 / 13 | 13 / 13 |
| 16,17 | AttackBattlesLastWeek / wins | 0 / 0 | 0 / 0 |

Names follow the dumped ArenaBattleStats schema and the retired-member profile.
League accounting independently agrees: 20+1=13+8, and 22+1=13+10. The original
monthly Arena BattleFinish quest also reports progress13. These facts corroborate
the counter assignment, but **no actual battle transition** is included in the
A/B/C archive (all three files are identical). The API records both this captured
profile validation and the missing transition validation. Negative counters and
wins greater than battle counts fail closed; league-accounting disagreement is
exposed as a boolean rather than fabricated away.

A real counter increase after an action can support verification, but a queue
entry, click or increment in unrelated defense counters cannot establish that
the planned offensive battle succeeded. Wins and total-offense deltas must be
interpreted separately.

### Refresh timestamps: important distinction

PlayerArenaModel **field7 is unchanged** at 2026-11-10T08:16:46 across old and new
fixtures, consistent with week processing rather than the latest list refresh.
Field5 changes from 2026-11-11T13:14:07 to 2026-11-13T08:59:54 alongside the
current-list replacement and close to its file-write time. That makes field5 a
refresh-time candidate, but there is no independently captured refresh action to
prove its semantic role. `last_refresh_time` therefore remains null/unknown;
raw DateTime interpretations are preserved in `timestamp_fields` for research.
Refresh verification should prefer an actual current-list signature change and
must not accept field7, metadata-only timestamp changes or a byte-identical
re-read as success.

## Full quest union decoding: the prior 35-record view was incomplete

`read_quest_states()` decodes PlayerQuestsModel union8. Top-level fields0..5 are
LastQuestId, ActiveQuestsById, CompletedPrototypeIds, PeriodicGroups,
AchievementGroups and TotalCompletedQuests. The active dictionary's value is a
MemoryPack IQuestState union: tag1 Periodic, tag2 Achievement, tag3 Book.
QuestStateBase wire fields0/1/2/3/5 are QuestId, PrototypeId, StateId,
TimeStarted and Progress; field4 is retired/empty. Derived state field50 is
Periodic.Group, Achievement.Group, or Book.Page according to the union tag.

| Capture | Active records | Periodic | Achievement | Book | State=Completed |
| --- | --- | --- | --- | --- | --- |
| Original fixture | 524 | 31 | 489 | 4 | 7 |
| Windows captures | 523 | 31 | 488 | 4 | 5 |

All dictionaries and object boundaries are consumed exactly. The previous
signature/range scanner returned only35 because it rejected prototype IDs at or
above1,000,000, removing almost every achievement. Example: quest23 is a genuine
Achievement with PrototypeId1002001, AchievementGroup2. Book quest533 is Page2;
its prototype range does not turn it into a Periodic or Progress quest.

### Progress / Advance is not inferred from a numeric ID

The dumped server QuestPeriodicGroup enum defines Daily1, Weekly2, Monthly3,
Advance4 and Clan5. **Neither fixture contains an active Advance4 record.**
Periodic counts are Daily8, Weekly4, Monthly7 and Clan12. The PeriodicGroups
metadata itself has keys1,2,3,5 and no4. The client QuestGroup enum uses a
*different* numbering (Advance4, Book5, Achievements6, Clan7), so those two enums
must not be conflated. Book page tasks and Achievements remain separately named.

The reader supports future Periodic group4 as `group='Advance'`; the planner can
apply Progress priority when an actual such record exists. It must not fabricate
one from Book IDs, static text proximity or low/high prototype ranges. Unknown
union subtypes retain bounded raw fields but have no inferred prototype, state,
progress or action semantics.

State IDs come from QuestStateId: Unknown0, New1, InProgress2, Completed3.
The seven/five Completed records are preserved rather than discarded as if their
rewards were already claimed. Nevertheless completion is not an ANNEHMEN button
or proof that a claim is currently safe. `reward_claimable` remains null with
this explicit reason; any claim path needs the corresponding UI precondition
and a verified post-action quest/reward transition.

CompletedPrototypeIds are read as a List (not silently deduplicated as a set).
Periodic group start/nullable finish times and all491 AchievementGroup current
level/progress pairs are exposed. These provide a coherent future verification
boundary for actual state/claim changes, without calling unknown-state records
active or converting a synthetic mutation into live-game validation.
