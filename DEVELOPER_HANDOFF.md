# DEVELOPER HANDOFF

## QUEST-LIVE-002 — static quest-definition discovery and catalog foundation

Status: BEREIT ZUR ENTWICKLUNG

Accepted baseline:
- QUEST-LIVE-001 implementation: `d8f1ffeb7a660dbdd79a37366751342afa318e2f`
- CI-fix: `0347c6d59d091c6f155ba791fc59ca57006ec631`
- Windows CI: `44312996129`
- `423 passed, 1 warning in 1.51s`

## Why this package

QUEST-LIVE-001 can tell us:
- which quest instances exist,
- type/group,
- state,
- progress,
- reset/window data,
- which active quests are Completed.

It does NOT yet know what a PrototypeId means.

QUEST-LIVE-002 must discover and formalize the static definition layer:
`PrototypeId -> objective semantics / target / required count / reward / routing hints`

Do not guess these fields.

## Research inputs

Search, in this order:

1. Current repository docs and archived branches/readers for any static-data parser or quest prototype mapping.
2. Existing IL2CPP dump/type inventory for quest/config/prototype/static-data types, serializers, enums and field names.
3. Any available local/static data artifacts already present in the developer environment.
4. The known game static-data artifact family, including the previously observed filename pattern `static-data.0.62.1655.dat`, if actually available.
5. Current official Invokers quest/update documentation only as semantic cross-check, never as runtime parser source.
6. Public GitHub/web references for robust versioned static-data catalog patterns if useful.

Current public research notes:
- official patch notes show quest objectives/rewards can change between builds, so catalog must be build/static-revision bound;
- 0.62 moved Clan Quests out of the main Quest screen, so navigation target cannot be inferred solely from quest kind;
- Exort publicly states it derives stats/text from game data and automates daily quests/farm goals, confirming that a data-driven quest-definition layer is practical, but do not copy undocumented assumptions from it.

## A. Discovery first

Before production parser code, identify the exact static quest-definition type(s).

Search IL2CPP/generated metadata for names related to:
- QuestPrototype
- QuestDefinition
- QuestConfig
- QuestObjective
- QuestReward
- QuestRequirement
- QuestTask
- QuestType
- QuestPeriodic
- QuestAchievement
- QuestBook / Progress Quest
- GO/navigation target
- static-data/config database containers

Record:
- namespace/type name
- field/property names
- enum values
- collection/container path
- serializer/wire format if discoverable
- linkage key to PlayerQuestsModel.PrototypeId
- build/static revision provenance

Do not infer field order from names alone.

## B. Static artifact inventory

If a static-data artifact is available:
- read-only only
- fingerprint it (size + SHA256)
- identify envelope/header/version/revision
- locate candidate quest tables without mutating the file
- compare candidate prototype IDs against QUEST-LIVE-001 synthetic/current-known ID expectations only where safe
- never commit the raw static-data file if it contains proprietary/bulk game content; commit only schema notes, tiny synthetic fixtures, and minimal non-copyrightable metadata needed for tests

If no static-data artifact is actually accessible:
- do NOT fabricate a parser
- complete the IL2CPP/schema discovery
- define the exact missing artifact/input needed for the next implementation step
- still implement only safe catalog interfaces/types that are fully justified by verified schema

## C. Catalog contract

Evolve the existing `QuestDefinitionCatalog` boundary only after discovery supports it.

Target semantic model may include, if verified:
- prototype_id
- quest family/kind
- objective type enum/id
- target/config id
- required amount/count
- reward descriptors
- navigation/domain hint
- page/group metadata
- game build
- static revision

All fields must distinguish:
- verified value
- absent/not-applicable
- unsupported/unknown

Never use guessed defaults.

## D. Routing layer

Only if objective semantics are verified, add a pure mapping from quest objective to existing bot domain capability, for example:
- Arena objective -> Arena domain hint
- Campaign objective -> Campaign hint
- Spire objective -> Spire hint
- Relic upgrade objective -> Relic hint

This is a **hint/synergy layer**, not an executor.

No clicks.
No scheduler rewrite.
No duplicate quest-specific implementations of Arena/Campaign/etc.

Unknown objective -> UNKNOWN/UNSUPPORTED, never guessed.

## E. Version safety

Catalog lookup must fail closed when:
- game build mismatch
- static revision mismatch
- unknown prototype
- unsupported objective type
- malformed static data

No silent fallback to stale definitions.

## F. Cross-checks

Use official current game information only to validate plausibility of decoded semantics.

Examples known from current official notes:
- quest rewards can change between updates;
- Clan Quest visibility/navigation changed in 0.62;
- new Sedula quest/achievement content was added in 0.62.

These facts prove version sensitivity; they are NOT sufficient to manufacture prototype mappings.

## G. Tests

If parser/schema is verified enough to implement:
- synthetic fixtures only
- exact prototype lookup
- unknown prototype
- build mismatch
- static revision mismatch
- unsupported objective type
- malformed/truncated table
- duplicate prototype IDs
- deterministic reward/objective decoding
- pure domain routing hint
- no action/input imports
- QUEST-LIVE-001 tests unchanged
- full suite green on Windows

If implementation is blocked by missing static artifact:
- add schema/discovery tests only where justified
- do not create fake parser behavior merely to increase test count

## H. Documentation

Create/update:
- `QUEST_STATIC_DEFINITIONS_0.62.md` or similarly precise schema note
- MASTER_STATUS.md
- MASTER_CHECKLIST.md
- TEST_RESULTS.md
- DEVELOPER_HANDOFF.md for the next package

Clearly separate:
- VERIFIED BY IL2CPP
- VERIFIED BY STATIC DATA
- CROSS-CHECKED AGAINST OFFICIAL DOCS
- UNKNOWN / BLOCKED

## Constraints

- read-only
- no SendInput
- no OCR
- no quest navigation
- no reward claim
- no purchase action
- no guessed PrototypeId mappings
- no bulk/raw static-data commit
- no Arena production changes
- Windows CI required for any code change

## Completion report

Report:
- exact static quest type/container discoveries
- whether actual static-data artifact was available
- artifact fingerprint if available
- PrototypeId linkage proof
- implemented files/interfaces
- which semantic fields are verified vs still unknown
- test count
- Windows Actions run/result
- blocker/input required for QUEST-LIVE-003
