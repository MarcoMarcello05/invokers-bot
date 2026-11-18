# DEVELOPER HANDOFF

## QUEST-LIVE-003 — verified static quest table decoder

Status: BLOCKED on exact serialized QuestData/prototype/condition/reward boundaries and final QUEST-LIVE-002 CI acceptance, not on artifact availability.

Read QUEST_STATIC_DEFINITIONS_0.62.md, MASTER_STATUS.md, TEST_RESULTS.md first.

Discovery runs 44314113822 and 44314362726 verified HZCP format 4, Main and header vector layout, IL2CPP static types and unions. Artifact is already in archive d363ef72e3cde80e05cc3829ac09f0137acedc5f, path InvokersBot_CODEX_HANDOFF/raw/static/static-data.0.62.1655(1).dat. SHA256 85c4b47a4b07e73454e6f923416a9f5da516599d455dc721c172b9ebf7805e4c. Do not copy raw files to main. Existing read-only discovery workflow can use archive git show. No production table rows loaded.

1. Verify 002 implementation Windows tests and strict archive reader log; fix any issues without weakening validity. Record exact commit/run/count.
2. Recover matching generated MemoryPack serializer or independently prove sequential StaticData.QuestData start/end, list counts, object bounds/order and trailing fields. Investigate existing InvokersIL(1).zip (named C# probe found none), other generated formatter/metadata files or matching client extraction in a read-only isolated environment. No scan-by-ID/range fallback. Memory field offsets alone do not prove serializer order.
3. Establish exact static/client compatibility: client schema 0.62.1621 vs artifact revision 0.62.1655 and second header string 0.62.700. Do not conflate them.
4. Decode bounded IQuestPrototype 1/2/3 records and relevant IQuestCondition 1..15, including nullable/list/complex nested schemas. Decode Reward VersionTolerant slots / ImmutableResources and other child serializers only when proven. Distinguish unknown vs absent. Verify duplicate/truncated/malformed rejection and full table consumption.
5. Cross-check actual unique prototype IDs against read-only captured PlayerQuestsModel and declared PrototypeById linkage. Report aggregate coverage and minimal synthetic fixture, not real bulk definitions. If anything remains unsupported, expose explicit unknowns/block production lookup. No fabricated reward/amount/target mapping.
6. Feed independently verified definitions with exact CatalogBinding and DefinitionOrigin into QuestStaticCatalog only once evidence is sufficient. Domain hints are non-executable. No quest UI navigation, claims, spending, OCR, SendInput, Arena production changes or scheduler expansion.
7. Run and inspect actual full Windows CI, push on main, document exact evidence and remaining blockers. No raw/static data committed.
