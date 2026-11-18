# QUEST STATIC DEFINITIONS — 0.62 (QUEST-LIVE-002)

## Evidence and scope

- Repository archive: d363ef72e3cde80e05cc3829ac09f0137acedc5f.
- Inputs already present in that archive: InvokersDump(2).zip (15,490,896 B), InvokersIL(1).zip (5,787,363 B), static-data.0.62.1655(1).dat (5,806,407 B), catalog.bin (2,036,713 B), de_DE.bin.br (1,162,978 B).
- Read-only Windows discovery runs 44314113822 (job 134835593581) and 44314362726 (job 134836471793), SUCCESS. Source declarations extracted from InvokersDump/DiffableCs, not raw data exported. Second ZIP contains no matching named C# files; no claim made about its contents beyond this inspection.
- Local direct binary fetch unavailable; GitHub Actions reads existing archive blobs with git show into memory. No new raw/bulk data on main, no uploads of binary artifacts.
- Client IL2CPP schema profile is 0.62.1621; pack revision is 0.62.1655. They are not assumed interchangeable. The second header string is 0.62.700; its precise semantic label is not independently established.

## VERIFIED BY STATIC DATA — HZCP container

| Fact | Observed value |
|---|---|
| Artifact bytes | 5806407 |
| SHA256 | 85c4b47a4b07e73454e6f923416a9f5da516599d455dc721c172b9ebf7805e4c |
| Magic / format word | HZCP / 4 |
| First / second version string | 0.62.1655 / 0.62.700 |
| Compressed / decompressed header bytes | 8836 / 17853 |
| Header MemoryPack member count | 3 |
| Entries in Keys / Chunks / ChunkHashes | 446 / 446 / 446 |
| Entry widths | 16 / 16 / 8 bytes |
| Unique Main key | Category=0, Id=0 |
| Main compressed / uncompressed bytes | 1467207 / 8652824 |
| Main SHA256 | be4fd758a5a107b8f39ee9001e3f472e5c5175aaa2821fcecd3ce197eeff482f |
| Main root object member count | 27 |

Confirmed envelope profile: HZCP bytes, LE UInt32 format 4, two 1-byte-length-prefixed ASCII version strings, LE UInt32 header packed/raw lengths, Brotli header, concatenated chunk data. Header fields: MemoryPack Object count 3, Int32 array count and 16-byte PackChunkKey records, Int32 array count and 16-byte PackChunk records, Int32 array count and 8-byte UInt64 hashes. Header length = 13 + 40*N. Offsets relative to end of packed header. Bounds, unique keys, count equality, bool, decompression length and artifact SHA verified by strict reader; chunk hash algorithm UNKNOWN, do not claim per-chunk declared hash validation.

Shared.Logic.Configs:
- ChunkPackHeader: Keys PackChunkKey[], Chunks PackChunk[], ChunkHashes UInt64[].
- PackChunkKey: Id Int64, Category byte, seven padding bytes.
- PackChunk: Offset, Size, UncompressedSize Int32; IsCompressed bool (16-byte record).
- ChunkCategory: Main=0, Level=1, Navmesh=2, Character=3, DerivedLevelInfo=4, BackgroundDownloadInfo=5. No quest-specific chunk category verified.
- StaticData: MemoryPackable GenerateType.Object, includes QuestData: StaticQuestData, ConfigVersion, SharedVersion. Main root count 27 matches observed object header. No verified offset/serialized member order for QuestData.

## VERIFIED BY IL2CPP — logical quest definition model

Definition namespace Shared.Logic.Configs; active state/action/reward enums in Shared.Choreograph.Models.

StaticQuestData contains Prototypes: List<IQuestPrototype>, AchievementGroups: DeterministicDictionary<QuestAchievementGroup, QuestAchievementGroupSettings>, PrototypeById: Dictionary<Int32,IQuestPrototype>, PeriodicPrototypes: List<QuestPrototypePeriodic>, AchievementPrototypes: Dictionary<QuestAchievementKey,QuestPrototypeAchievement>, BookPrototypes: List<QuestPrototypeBook>. These are declared properties; serialized membership/order of caches is not established.

QuestStateBase.PrototypeId (Int32) and QuestPrototypeBase.Id (Int32), with PrototypeById keyed by Int32, establish the intended logical linkage. This is schema-level evidence, not a verified byte-level join of real records. The archive heuristic signature 01 0A (periodic union/object prefix) has 31 matching distinct IDs among 524 archived active distinct PrototypeIds, no duplicates under that filter. This is a candidate count only, not table boundaries or proof of any mapping. Different account capture from current QUEST-LIVE-001 fixture. No actual prototype IDs/objective values committed.

IQuestPrototype MemoryPack union tags and derived fields:
| Tag | Type | Additional declared fields |
|---:|---|---|
| 1 | QuestPrototypePeriodic | Group: QuestPeriodicGroup; SortOrder: Int32 |
| 2 | QuestPrototypeAchievement | Group: QuestAchievementGroup; Level: Int32 |
| 3 | QuestPrototypeBook | Page: Int32; SortOrder: Int32 |

QuestPrototypeBase (MemoryPack GenerateType.Object):
| Field | Declared type |
|---|---|
| Id | Int32 |
| Action | QuestAction |
| RequiredAmount | Int32 |
| Conditions | List<IQuestCondition> |
| Reward | Reward |
| Disabled | Nullable<Boolean> |
| AutoComplete | Nullable<Boolean> |
| OpenCondition | QuestConditionPlayer |

Declarations do not prove wire order. QuestPrototypeSerializationType: Unknown=0, Periodic=1, Achievement=2, Book=3. StaticQuestData named parent constants (10000 Daily, 11000 Weekly, 15000 Monthly, 17000 Advance, 18000 Clan) are declared in dump; never use them to infer ID ranges or group of an individual record.

QuestAchievementGroupSettings: AchievementTab Nullable<QuestAchievementTab>, SortOrder Nullable<Int32>. QuestPeriodicGroupShard: Group, List<QuestPrototypePeriodic>; QuestBookPageShard: Page, List<QuestPrototypeBook>; QuestAchievementGroupShard: Group, Settings, List<QuestPrototypeAchievement>. Shard types are declared but no independently addressable quest shard wire format or chunk category verified.

### IQuestCondition union

GenerateType.Object. Union attributes and QuestConditionSerializationType agree.
| Tag | Type | Declared fields (names, NOT wire order) |
|---:|---|---|
| 1 | QuestConditionHero | MinRarity, Rarity, Rank, MinLevel, Classes, NotElements, Elements, SoulSigns, HeroXpSource, MinAwakeLevel, IsFullAwakened |
| 2 | QuestConditionAnima | Rarity, EmpowermentLevel, MinLevel |
| 3 | QuestConditionRelic | Slot, MinRank, MinRarity, Rarity, Set, Equipped, MinLevel, Ranks, SubStatGrade, Slots, MainBonuses |
| 4 | QuestConditionQuest | PrototypeIds (List<Int32>), BookPage, FinishPeriodicGroup |
| 5 | QuestConditionBattle | AreaId, RegionId, Difficulty, Number, RegionIds, AutoBattle, AnimasCount, MinNumber, Numbers, AllowDefeat, CollectStars, ClanBoss2DamageDifficultyId |
| 6 | QuestConditionResources | ResourceId, AnyResourceId, Count |
| 7 | QuestConditionShop | No backing fields captured; do not assert an empty wire object |
| 8 | QuestConditionPlayer | MinPlayerLevel, MaxPlayerLevel, ArenaLeagueId, AnyFormationBelowLevel |
| 9 | QuestConditionHeroesCollection | HeroesCount, HeroesMinLevel, HeroesClasses, RelicsCount, RelicsMinLevel, EquippedSets, MainBonuses, EquippedSlot, SetsCount, RelicMinRank, MinAwakeLevel, HeroesElements, SkillsLevel, HashTags, Stats |
| 10 | QuestConditionAnimasCollection | AnimasCount, AnimasMinLevel |
| 11 | QuestConditionHeroOrAnima | No backing fields captured; do not assert an empty wire object |
| 12 | QuestConditionArenaHallCollection | Element, Level, OneElementStatsHasSpecifiedLevel |
| 13 | QuestConditionClientAction | ActionType (Nullable<ClientQuestActionType>) |
| 14 | QuestConditionAccessory | Slot, MinRank, MinRarity, Rarity, Equipped, MinLevel, Ranks, SubStatGrade, Slots, MainBonuses |
| 15 | QuestConditionGear | MinRank, MinRarity, Rarity, Equipped, MinLevel, Ranks, SubStatGrade, MainBonuses |

Battle condition: AreaId, RegionId, Difficulty and Number are nullable enums/Int32; RegionIds List<RegionId>, Numbers List<Int32>; AutoBattle, AllowDefeat, CollectStars nullable bool; AnimasCount, MinNumber, ClanBoss2DamageDifficultyId nullable Int32. Do not treat absence as zero or unknown as absence.

QuestAction full enum (verified declarations, not actual prototype action assignments): implemented as QuestActionId in quest_catalog.py. Important values: HeroSummon=2, HeroLevelUp=3, RelicUpgrade=43, RelicActivateOrUpgrade=47, AccessoryUpgrade=53, BattleFinish=61, QuestComplete=81, QuestUpgradeProgress=82, ResourcesSpent=101, ShopPurchase=121, PlayerLogIn=141, ArenaHallUpgrade=191, ArenaPointsChange=192, ClientAction=201.
AreaId: Unknown=0, Campaign=1, Dungeon=2, Tower=3, AsyncPvp=4, FactionWars=5, ClanBoss=6, Events=7, InfinityDungeon=8, Experiment=40, VFX=54, GameDesign=56, Coders=57, Tools=58, Misc=99.

### Reward and navigation

Shared.Choreograph.Models.Reward is MemoryPack VersionTolerant. Declared fields: Experience Int32, Resources ImmutableResources, Heroes ImmutableList<HeroReward>, Animas ImmutableList<AnimaReward>, Relics ImmutableList<RelicReward>, Accessories ImmutableList<AccessoryReward>, VipPoints Int32, AvatarFrames ImmutableList<AvatarFrameReward>. Child formats/slots and actual reward values remain unverified. No default zero amounts.

Client.UI.Quests.QuestNavigation.ImprovedNavigation.QuestConditionFinder and related client-navigation type names exist. No verified navigation target serializer/route/GO behavior. No quest navigation API or runtime actor.

## CROSS-CHECKED AGAINST OFFICIAL DOCS

Official 0.62 patch notes, 23 Oct 2026 (https://invokers.com/news/66/): Daily and Clan rewards changed, Sedula quest and damage achievements introduced, Clan Quests moved out of main Quest screen into Clans. Version-sensitive design justified. No PrototypeId or serialization order inferred from the text.

## Implemented foundation

static_pack.py strictly indexes the verified HZCP profile and extracts a bounded chunk into memory. No StaticData/quest object decoder. quest_catalog.py models declared action/condition enum IDs, explicit VERIFIED/ABSENT/UNKNOWN/UNSUPPORTED values, immutable semantic definition/record provenance, exact build/revision and optional artifact fingerprint gates, duplicate ID rejection and safe in-memory lookup of already independently decoded records. Without a verified table the catalog is unavailable; no production instance or rows installed. Coarse domain hints only from successful lookup and verified action/conditions; BattleFinish requires explicit single Battle AreaId, never a prototype range or family. Hint is not UI navigation, spending or action authorization. Synthetic-only catalog tests exercise the consumer, not a static table decoder.

## UNKNOWN / BLOCKED — next decoder work

StaticData is sequential GenerateType.Object, not VersionTolerant. Recover serialized member ordering/skip logic from matching generated serializer/IL and prove QuestData table start/end (including list count/boundaries and trailing fields). Decode every relevant prototype and condition union structurally with bounded nested parsing; verify Reward slots and child layouts, then cross-check real IDs/counts and duplicates from the archived state without outputting bulk data. Confirm client's exact static revision compatibility independently before publishing a production catalog. Artifact exists and archive CI is available; user upload not necessary if matching serializer evidence can be recovered there. No guessed objective, count, reward or real routing mappings. No static bulk file committed.
