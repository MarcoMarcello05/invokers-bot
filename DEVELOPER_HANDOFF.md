# DEVELOPER HANDOFF

## QUEST-LIVE-003 — real static QuestData decoder + current PrototypeId join

Status: BEREIT ZUR ENTWICKLUNG

Accepted baseline:
- QUEST-LIVE-002 commit: `04dd53fbad1cfb86114dbdd9126fa5915e106034`
- Windows Actions: `44315267859`
- result: `460 passed, 1 warning in 1.68s`
- conclusion: SUCCESS

Read first:
- `QUEST_STATIC_DEFINITIONS_0.62.md`
- `MASTER_STATUS.md`
- `TEST_RESULTS.md`
- existing `static_pack.py`, `quest_catalog.py`, `quest_static_discovery.py`

## Important correction

Do not conflate the two HZCP header version strings.

Observed current files expose:
- first string: 0.62.1657 / 0.62.1659 / 0.62.1661 respectively
- second string: 0.62.700 in all three

Treat them as distinct opaque version identifiers until the code/IL2CPP loader proves their exact semantics.
Do not label either one "Static revision" merely from filename/header position.

## Fresh real artifacts supplied from current PC

These are NOT to be committed raw:

- `static-data.0.62.1657.dat`
  - size 5,808,901
  - SHA256 `6f1c536c90c51465ea632c371719bde14ab90a314e8c2855fcfa79bd8703fd2f`

- `static-data.0.62.1659.dat`
  - size 5,838,336
  - SHA256 `d45634471a348ebbd8f3949feec085e27206c65922aba2f36edbbf443e4f6701`

- `static-data.0.62.1661.dat`
  - size 5,809,126
  - SHA256 `390f752c88d6247674fae7901653bf2b636af6735b1a0f1c157879060cd6b46d`

- current `PlayerQuestsModel.dat`
  - size 52,486
  - SHA256 `44b094afb8ada6818303ac4854cfc805a0dc5d93e9bc6db48288f5e675abdcad`

The old archived 0.62.1655 artifact remains useful for regression comparison, but current decoding should prioritize 1661 and use 1657/1659 for differential validation.

If these fresh artifacts are not available in your workspace, do NOT fabricate their contents. Implement the decoder against the archived 1655 evidence plus proven serializer/schema information, and report exactly what still requires the user-supplied current files for final cross-check.

## Verified type target

IL2CPP discovery already establishes:
- `StaticQuestData`
- `IQuestPrototype`
- prototype union tags:
  - 1 Periodic
  - 2 Achievement
  - 3 Book
- common prototype semantics include:
  - Id
  - Action
  - RequiredAmount
  - Conditions
  - Reward
  - Disabled
  - AutoComplete
  - OpenCondition
- IQuestCondition union tags 1..15 are typed in the schema
- QuestAction enum values are schema evidence, not PrototypeId mappings

The task is to prove the serialized layout and decode actual rows.

## A. Recover exact serialization

Preferred evidence order:
1. generated MemoryPack formatter/serializer code for StaticData / StaticQuestData / QuestPrototype / conditions / Reward;
2. matching generated metadata/formatter artifacts;
3. independent bounded structural proof from the real Main chunk, with exact list/object boundaries and full consumption.

Memory field offsets alone are insufficient.

No scan-by-ID heuristic is allowed as the production decoder.
No broad byte-range guessing.

## B. Decode StaticData -> QuestData

Prove:
- StaticData root member containing QuestData
- QuestData object member order
- prototype collection start/end/count
- whether PrototypeById is serialized directly or derived after load
- complete object/list consumption with no unexplained trailing bytes

Keep all unsupported members opaque/UNKNOWN rather than inventing semantics.

## C. Decode real prototype records

Decode union tags 1/2/3 with at least:
- prototype_id
- kind
- action
- required_amount
- disabled
- auto_complete
- subtype group/page fields when verified

Decode Conditions only for serializers that are proven.
Decode Reward only for child structures whose wire layout is proven.

It is acceptable for Reward/Condition subfields to remain UNKNOWN while Id/Action/RequiredAmount are verified.
Do not block the whole prototype if a bounded optional child can be preserved opaque safely.

## D. Real PrototypeId join

Use the current PlayerQuestsModel parser and perform a read-only join:

`PlayerQuestsModel.active_by_id[*].prototype_id`
→ decoded `StaticQuestData` prototype ID.

Report:
- number of unique active PrototypeIds
- number resolved
- number unresolved
- duplicates if any
- kind/action/required amount coverage
- any current PrototypeId absent from the static table

Do not commit bulk user quest rows.
Tests should use minimal synthetic fixtures and a tiny sanitized set of non-sensitive numeric regression facts only when necessary.

## E. Differential validation across static files

Compare 1657, 1659, 1661 structurally:
- HZCP/header compatibility
- chunk count/key set changes
- QuestData table count
- prototype IDs added/removed/changed
- whether Action/RequiredAmount/Reward fields changed

This is especially useful to prove that the decoder is reading semantic records rather than accidentally matching byte patterns.

Do not assume 1657/1659/1661 are schema-compatible merely because the format header is 4.

## F. Catalog integration

Once a definition row is structurally verified:
- create exact CatalogBinding using both HZCP version identifiers + artifact SHA256
- attach DefinitionOrigin / evidence level
- fail closed on a different binding
- unknown prototype remains UNKNOWN
- unsupported objective/condition/reward remains explicit

DomainHint remains non-executable.

No scheduler rewrite.

## G. Tests

Add synthetic regression tests for:
- exact QuestData table boundary
- each prototype union tag 1/2/3
- action + required amount
- unknown/unsupported union
- malformed/truncated object
- duplicate prototype ID
- trailing bytes
- version/binding mismatch
- current catalog fail-closed behavior
- optional opaque unsupported condition/reward handling
- deterministic real-ID join adapter using sanitized fixture IDs
- existing 460 tests remain green

If fresh real artifacts are accessible in CI only through a private/archive mechanism, run them as a separate read-only discovery validation. Never add raw static files or PlayerQuestsModel.dat to public main.

## H. Documentation

Update:
- `QUEST_STATIC_DEFINITIONS_0.62.md`
- MASTER_STATUS.md
- MASTER_CHECKLIST.md
- TEST_RESULTS.md

Explicitly separate:
- VERIFIED BY SERIALIZER/IL2CPP
- VERIFIED BY REAL STATIC DATA
- VERIFIED BY CROSS-VERSION DIFFERENTIAL
- VERIFIED BY PLAYER QUEST JOIN
- UNKNOWN

## Constraints

- read-only
- no raw/bulk data commit
- no SendInput
- no OCR
- no quest navigation
- no claim
- no spending
- no Arena production changes
- no guessed PrototypeId mapping
- Windows CI required

## Completion report

Report:
- exact StaticData -> QuestData serialization proof
- exact prototype member layout
- condition/reward coverage
- current active PrototypeId resolution coverage
- 1657/1659/1661 differential findings if files were available
- version/binding semantics
- files changed
- commit SHA
- final pytest count
- Windows Actions run/result
- precise remaining blocker for QUEST-LIVE-004
