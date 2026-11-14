# MASTER STATUS

Date: 2026-11-14

## Product target

**Universal fully autonomous Invokers autopilot.**

The canonical project target list is now:
`MASTER_CHECKLIST.md`

All future planning, implementation and status updates must reference that checklist by stable feature ID. New systems discovered through research must be appended there instead of living only in chat or scattered documentation.

## State

- ABGESCHLOSSEN: Recovery branch `archive/pre-analyser-2.0-restart-2026-11-14`.
- ABGESCHLOSSEN: Clean active-tree reset.
- ABGESCHLOSSEN: Windows live-input engine.
- ABGESCHLOSSEN: Client-area + DPI handling.
- ABGESCHLOSSEN: DXcam + MSS fallback.
- ABGESCHLOSSEN: OpenCV state and target matching.
- ABGESCHLOSSEN: Stable-state gate, UNKNOWN=no-input, F12 abort.
- IN ENTWICKLUNG: Universal Goal -> Task -> State -> Action architecture.
- IN ENTWICKLUNG: Central scheduler and reusable skill registry.
- ABGESCHLOSSEN: Permanent full-project checklist established in `MASTER_CHECKLIST.md`.
- OFFEN: Fresh global UI/state inventory.
- OFFEN: Full account/game automation implementation across checklist domains.
- TEST AUSSTEHEND: Real Windows dry/live validation.

## Working rule

Never mark a major capability as complete only because code exists. A checklist item reaches `ABGESCHLOSSEN` only when its acceptance behavior has been verified.

## Immediate next objective

Work directly from `MASTER_CHECKLIST.md`, starting with the universal core/data/navigation foundations required by many later systems.


## Current data-analysis package

- IN ANALYSE: DATA-002 fresh local data inventory.
- IN ANALYSE: DATA-003 structured snapshot-reader research.
- Fresh snapshot findings are documented in `DATA_SNAPSHOT_2026-11-14.md`.
- Project role split and research-first rule are documented in `PROJECT_WORKFLOW.md`.
- No new production coding task is issued until the model/schema analysis is ready for a precise DEVELOPER prompt.


## IL2CPP schema milestone

- ABGESCHLOSSEN: current Windows IL2CPP metadata identified as version 39.
- ABGESCHLOSSEN: primary player/account aggregate model field inventory extracted.
- ABGESCHLOSSEN: ResourceTypeId structured resource model confirmed.
- IN ANALYSE: snapshot serialization/formatter contract needed before parser handoff.
- Schema findings: `IL2CPP_SCHEMA_0.62.1621.md`.


## Snapshot serialization milestone

- ABGESCHLOSSEN: IAggregateSnapshotDTO MemoryPack union tags mapped for all 12 aggregate files.
- ABGESCHLOSSEN: generic 3-member VersionTolerant envelope verified byte-for-byte across all supplied snapshots.
- BEREIT ZUR ENTWICKLUNG: read-only aggregate-envelope parser (DATA-003 phase 1).
- IN ANALYSE: exact inner-model MemoryPackOrder/reserved-slot maps for AccountState decoding.
- Details: `SNAPSHOT_SERIALIZATION_0.62.1621.md`.

## DATA-003 Phase 1 implementation

- ABGESCHLOSSEN: DATA-003 Phase 1 strict read-only outer envelope parser; GitHub Actions run 43602310052 passed on Windows for commit ed11fb1f06373c72f394b6d06e35be7f039a70c1.
- Windows CI uses existing pytest discovery. No live input or snapshot writes.
- Full DATA-003 remains open pending inner-model research and implementation.


## PlayerModel / Resources milestone

- ABGESCHLOSSEN: PlayerModel current 53-slot VersionTolerant layout mapped.
- ABGESCHLOSSEN: four reserved/removed slots identified at 7, 12, 13, 14.
- ABGESCHLOSSEN: Resources / ResourcesGained / ResourcesSpent binary structure decoded and cross-validated arithmetically.
- BEREIT ZUR ENTWICKLUNG: DATA-003 Phase 2 can decode selected PlayerModel scalars and ResourceTypeId values while safely skipping nested slots.
- Details: `PLAYERMODEL_RESOURCES_MAP_0.62.1621.md`.


## Structured-data analysis milestones

- ABGESCHLOSSEN: PlayerHeroesModel / PlayerHero current MemoryPack layout mapped and cross-validated against PlayerRelicsModel.
- ABGESCHLOSSEN: PlayerRelicsModel / PlayerRelic current MemoryPack layout mapped.
- ABGESCHLOSSEN: PlayerQuestsModel and IQuestState union layout mapped, including periodic/achievement/book quest state structure.
- ABGESCHLOSSEN: PlayerAnimasModel / PlayerAnima current MemoryPack layout mapped.
- IN ANALYSE: remaining structured models and cross-model AccountState source matrix.
- New schema documents:
  - `HEROES_MEMORYPACK_MAP_0.62.1621.md`
  - `RELICS_MEMORYPACK_MAP_0.62.1621.md`
  - `QUESTS_MEMORYPACK_MAP_0.62.1621.md`
  - `ANIMAS_MEMORYPACK_MAP_0.62.1621.md`

## DATA-003 Phase 2 implementation

- ABGESCHLOSSEN: DATA-003 Phase 2 PlayerModel scalars and Resources dictionaries implemented and Windows-CI verified on commit `2a9f1d5b508a321dc7553ea2a899eeff43cc3612`.
- ABGESCHLOSSEN: full 181-name ResourceTypeId mapping ported from the verified archive; integer keys remain canonical.
- CI: GitHub Actions run `43640238110` completed SUCCESS with `89 passed, 1 warning`.


## Architecture benchmark / structured-domain milestone

- ABGESCHLOSSEN: external architecture benchmark covering OpenKore, RuneLite, BehaviorTree.CPP and Robot Framework patterns.
- ENTSCHEIDUNG: retain Invokers' own deterministic architecture; adopt event bus, freshness-aware WorldState facts, explicit task statuses, bounded recovery, plugin-like Skills and structured action traces.
- ABGESCHLOSSEN: PlayerArenaModel current top-level MemoryPack layout mapped.
- ABGESCHLOSSEN: PlayerBattleModel and MultiBattleSession current MemoryPack layouts mapped.
- IN ANALYSE: PlayerAccessory exact inner slot order remains unverified because current snapshot contains zero accessories.
- ABGESCHLOSSEN: initial AccountState source matrix created.
- Details:
  - `BOT_ARCHITECTURE_BENCHMARK.md`
  - `ARENA_MEMORYPACK_MAP_0.62.1621.md`
  - `BATTLE_MULTIBATTLE_MAP_0.62.1621.md`
  - `ACCESSORIES_MEMORYPACK_MAP_0.62.1621.md`
  - `ACCOUNTSTATE_SOURCE_MATRIX.md`


## Additional structured-domain milestone

- ABGESCHLOSSEN: PlayerClanModel top-level layout and PlayerClanBoss2State mapped.
- ABGESCHLOSSEN: PlayerGlobalEventsModel top-level layout mapped; nested tournament union remains future analysis.
- ABGESCHLOSSEN: PlayerShopModel current 19-slot layout mapped, including historical gaps and current Purchases/Offers dictionaries.
- IN ANALYSE: InboxItem exact inner layout awaits a non-empty inbox snapshot; top-level PlayerInboxModel is mapped.
- New schema documents:
  - `CLAN_MEMORYPACK_MAP_0.62.1621.md`
  - `GLOBAL_EVENTS_MEMORYPACK_MAP_0.62.1621.md`
  - `INBOX_MEMORYPACK_MAP_0.62.1621.md`
  - `SHOP_MEMORYPACK_MAP_0.62.1621.md`

## DATA-003 Phase 3 implementation

- TEST AUSSTEHEND: read-only PlayerHeroesModel and PlayerHero parser; bounded nested objects reuse the shared slot reader. Windows CI pending.
- Root slots 6 onward remain opaque. ReceivedHeroesCount uses inferred Int64 key + Int32 count (900 bytes consistent with 4 + 74*12); real snapshot verification pending.


## Planner policy milestone

- ABGESCHLOSSEN: research-backed planner policy defined for Goal eligibility, utility scoring, freshness, risk, hysteresis, recovery and circuit breakers.
- ABGESCHLOSSEN: AccountState-to-Planner contract defined, including model joins, provenance/versioning and derived-fact dependencies.
- ENTSCHEIDUNG: use a hybrid planner now: hard gates -> utility Goal selection -> deterministic Task/Skill execution -> reactive replan.
- ENTSCHEIDUNG: defer full GOAP search until cross-domain quest routing proves it is actually needed.
- Details:
  - `PLANNER_POLICY.md`
  - `ACCOUNTSTATE_PLANNER_CONTRACT.md`


## DATA-003 Phase 3 verification

- ABGESCHLOSSEN: PlayerHeroesModel / PlayerHero read-only parser.
- CI verified on commit `09a3c33638abbede74ad1063e26baf3b02a87b54`.
- GitHub Actions run `43641550108`: SUCCESS.
- Test result: `129 passed, 1 warning in 0.30s`.
- Remaining schema assumption: ReceivedHeroesCount interpreted as Int64->Int32 mapping; non-blocking for core Hero parsing.
- NEXT: DATA-003 Phase 4 PlayerRelicsModel + PlayerRelic.

## DATA-003 Phase 4 implementation

- TEST AUSSTEHEND: read-only PlayerRelicsModel and PlayerRelic parser using the existing envelope and nested VersionTolerant slot readers.
- PlayerRelicBonus and Randoms remain opaque; no assumed bonus layout or gear actions. Windows CI pending.


## Goal catalog milestone

- ABGESCHLOSSEN: concrete Invokers Goal catalog defined across safety, claims, anti-waste, progression, farming, Arena, Clan, Events and maintenance.
- ABGESCHLOSSEN: deterministic planner acceptance scenarios defined for priority, synergy, stale data, event-save policy, circuit breakers and anti-starvation.
- ENTSCHEIDUNG: overlapping objectives should contribute synergy to one executable domain Goal instead of spawning duplicate competing action loops.
- Details:
  - `INVOKERS_GOAL_CATALOG.md`
  - `PLANNER_DOMAIN_SCENARIOS.md`

## Phase 4 CI and live AccountState foundation

- ABGESCHLOSSEN: Phase 4 parser CI run 43642110801, 174 passed, 1 warning; commit ca2dc5bdc3251b3a8b05724ef893a90d7093e08a.
- TEST AUSSTEHEND: optional live AccountObserver and WorldState bridge; polling plus post-input refresh. Planner integration and real client verification remain open.


## Live AccountState review

- ABGESCHLOSSEN: Phase 4 PlayerRelicsModel/PlayerRelic implementation and CI verification.
- ABGESCHLOSSEN: first live AccountState observation channel integrated into BotEngine.
- CI for live integration commit `371ab08015cb0bd9ec3e2a3ca4723a187133e80f`: SUCCESS, run `43642665870`, `179 passed, 1 warning`.
- REVIEW FINDING: current live input path invalidates all account aggregate observations after every real input. This is too coarse and can make unchanged Heroes/Relics unavailable after unrelated UI actions.
- REQUIRED NEXT: action-scoped invalidation + action-specific verification predicates before AccountState-driven goal selection.


## Live action verification milestone

- ABGESCHLOSSEN: action -> affected source -> verification matrix defined.
- ABGESCHLOSSEN: live Skill verification contract defined.
- ENTSCHEIDUNG: `invalidates_sources` and `expects_changed_sources` are separate concepts.
- ENTSCHEIDUNG: navigation-only actions must not invalidate structured account sources.
- ENTSCHEIDUNG: pre-action source digest/version baselines should be captured for state-changing actions.
- ENTSCHEIDUNG: verification results need explicit SUCCESS / FAILURE / TIMEOUT / CANCELLED / INCONCLUSIVE states.
- Details:
  - `ACTION_SOURCE_VERIFICATION_MATRIX.md`
  - `LIVE_SKILL_VERIFICATION_CONTRACT.md`

## LIVE-001A implementation

- TEST AUSSTEHEND: action-scoped invalidation, explicit four-mode evidence contracts, baseline checks and failure results integrated into existing BotEngine. Navigation no longer invalidates unrelated aggregates. Arena start requires player change plus visual transition; real-client timing unverified. CI pending.


## LIVE-001A acceptance

- ABGESCHLOSSEN: action-scoped AccountState invalidation and explicit action verification contracts.
- commit: `43f665f37ec15b7d4b448f785184274e76b721ce`
- Windows CI run: `43643095273`
- result: `215 passed, 1 warning in 0.75s`
- VERIFIED: navigation-only actions preserve unrelated account sources.
- VERIFIED: all four verification modes, corrupt-source failure handling, scoped invalidation, baseline checks, cancellation and legacy compatibility.
- OPEN LIVE ASSUMPTION: Arena start currently requires a PlayerModel digest change within 5s. Real client persistence timing and the precise Arena-token semantic delta are not yet measured.


## ResourcePlanner / Arena policy milestone

- ABGESCHLOSSEN: ResourcePlanner reserve/spend policy defined.
- ABGESCHLOSSEN: initial live Arena Goal policy defined.
- ENTSCHEIDUNG: unknown resource caps/costs are never guessed.
- ENTSCHEIDUNG: Arena overflow pressure is disabled until a cap is verified/configured.
- ENTSCHEIDUNG: visual battle start followed by delayed snapshot persistence must reconcile before any retry.
- Details:
  - `RESOURCE_PLANNER_POLICY.md`
  - `ARENA_GOAL_POLICY.md`

## LIVE-001B

- TEST AUSSTEHEND: first AccountState-driven Arena eligibility and refresh goal; generic semantic resource predicates, decision trace and runtime goal gate implemented. CI pending. Real-client timing/cost/cap not verified.


## LIVE-001B acceptance and Arena completion direction

- ABGESCHLOSSEN: LIVE-001B AccountState-driven Goal eligibility + semantic resource verification.
- commit: `6c12332548ff3c0e6d0d536fda7250156732f0ad`
- Windows CI run: `43643490286`
- result: `242 passed, 1 warning in 0.95s`
- VERIFIED: blocked Goals do not send live input.
- VERIFIED: Arena token semantic predicates distinguish real token deltas from unrelated PlayerModel changes.
- VERIFIED: Goal domain logic remains outside BotEngine.
- NEXT: complete Arena end-to-end before Campaign. ARENA-LIVE-002 = PlayerArenaModel + bounded scrollable opponent-list traversal.


## Arena completion plan

User confirmed that the Arena opponent list is vertically scrollable. Opponent discovery must therefore traverse beyond the first viewport.

Arena will now be completed before Campaign:
1. live PlayerArenaModel
2. bounded scrollable opponent-list traversal
3. ArenaOpponent semantic mapping
4. opponent scoring
5. target/formation selection
6. battle start and token verification
7. result/win/loss handling
8. opponent refresh policy
9. recovery/circuit + real-client validation

Engineering rule: scrolling uses generic SendInput wheel support, visual ROI change verification, de-duplication, end-of-list detection and hard safety bounds.


## Arena own Team Power source analysis

- ABGESCHLOSSEN: opponent Team Power confirmed as structured Arena data target.
- ABGESCHLOSSEN: own-power source candidates ranked.
- PRIMARY CANDIDATE: PlayerBattleModel.LastMetaBattleSetup -> PlayerTeamSetup -> CombatPower.
- ALTERNATIVE: exact local calculation from AsyncPvpPreset + Heroes + Relics + Accessories + Arena/formation inputs, but formula parity is not yet proven.
- FALLBACK: tiny pre-battle Team Power OCR/number ROI.
- REQUIRED LIVE TEST BEFORE OPPONENT SCORING: snapshot diff before/after opening Arena formation without starting battle.
- Details: `ARENA_OWN_POWER_SOURCE_ANALYSIS.md`
