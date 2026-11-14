# ACTION -> SOURCE -> VERIFICATION MATRIX

Date: 2026-11-14

Purpose: define which structured sources a live action may invalidate and which evidence proves success.

This document bridges:
- BotEngine live input
- AccountObserver
- AccountState
- future Skills / Scheduler

External research reinforced two design rules:
- retry cadence and give-up windows should be separate
- preconditions, blackboard state, retry and timeout behavior should be explicit rather than hidden in one loop

References:
- OpenKore timeout policy
- BehaviorTree.CPP retry/timeout/precondition/blackboard patterns

## Verification modes

### VISUAL_ONLY
Use when action changes only UI/navigation state.

Success:
- expected visual successor state recognized

Structured source invalidation:
- none

Examples:
- open menu
- switch tab
- close popup
- navigate home

### STRUCTURED_ONLY
Use when UI may remain visually ambiguous but a known aggregate change is authoritative.

Success:
- all required structured source changes observed

Examples later:
- account-state operations with no reliable visual confirmation

Use sparingly.

### VISUAL_AND_STRUCTURED
Use for important account-changing actions.

Success requires:
- expected visual transition
AND
- expected structured source change

Examples:
- equip relic
- claim reward
- spend resource on upgrade

### VISUAL_OR_STRUCTURED
Use for actions where either authoritative signal proves completion and game save timing may lag.

Use only when both evidence paths independently imply the same semantic success.

## Core rule

`invalidates_sources` and `expects_changed_sources` are NOT the same thing.

- invalidates_sources:
  sources that may have become stale because of the action.

- expects_changed_sources:
  sources whose changed content is required as success evidence.

Example:
Starting a battle may invalidate PlayerModel because Energy/token count may change, but save latency can mean visual transition appears first. Whether PlayerModel change is mandatory depends on action semantics.

## Current tracked source names

Currently implemented:
- player
- heroes
- relics

Planned:
- animas
- quests
- arena
- battle
- clan
- events
- inbox
- shop
- accessories

## Action matrix

| Action/Skill family | Invalidates | Expected structured change | Visual verification | Recommended mode |
|---|---|---|---|---|
| navigate/open screen | none | none | target screen | VISUAL_ONLY |
| switch tab/filter | none | none | target tab/filter | VISUAL_ONLY |
| close popup | none | none | popup gone / prior screen | VISUAL_ONLY |
| scroll list | none | none | list movement/target visible | VISUAL_ONLY |
| select hero/team temporarily | none unless saved immediately | none | selected state visible | VISUAL_ONLY |
| start Arena battle | player + arena | arena and/or token resource depending confirmed persistence | battle/loading screen | VISUAL_AND_STRUCTURED preferred once arena source exists |
| finish Arena battle | arena + player | arena result/points and possibly resources | result/Arena screen | VISUAL_AND_STRUCTURED |
| refresh Arena opponents | arena | arena | opponent list changed | VISUAL_AND_STRUCTURED |
| start Campaign battle | player + battle | player resource spend and/or battle session/history depending persistence | battle/loading screen | VISUAL_AND_STRUCTURED |
| finish Campaign battle | battle + player | level stats / rewards / resource state as applicable | result/campaign screen | VISUAL_AND_STRUCTURED |
| start MultiBattle | battle + player | battle.MultiBattleSession | session started UI | VISUAL_AND_STRUCTURED |
| collect MultiBattle | battle + player | battle session/reward + resources | collection/result UI | VISUAL_AND_STRUCTURED |
| claim quest reward | quests + player | quest state + resources if reward includes resources | quest claim disappears | VISUAL_AND_STRUCTURED |
| claim campaign reward | battle + player | claimed campaign set + resources | reward UI resolved | VISUAL_AND_STRUCTURED |
| claim clan reward | clan + player | clan pending chest + resources | claim resolved | VISUAL_AND_STRUCTURED |
| claim event reward | events + player | event reward state + resources | claim resolved | VISUAL_AND_STRUCTURED |
| claim inbox reward | inbox + player | inbox item/reward state + resources | item disappears/claimed | VISUAL_AND_STRUCTURED |
| level hero | heroes + player | hero level/xp + spent resources | updated hero details | VISUAL_AND_STRUCTURED |
| ascend hero | heroes + player | hero rank + spent materials | rank change | VISUAL_AND_STRUCTURED |
| awaken hero | heroes + player | awake state + spent materials | awakening UI change | VISUAL_AND_STRUCTURED |
| upgrade hero skill | heroes + player | skill level + spent resources | skill UI change | VISUAL_AND_STRUCTURED |
| lock/unlock hero | heroes | heroes | lock icon | VISUAL_AND_STRUCTURED |
| equip relic | heroes + relics | hero RelicIdBySlot and relic EquippedHeroId | equipped UI | VISUAL_AND_STRUCTURED |
| unequip/swap relic | heroes + relics | hero/relic equipment relation | equipped UI | VISUAL_AND_STRUCTURED |
| upgrade relic | relics + player | relic level + resource spend | relic level UI | VISUAL_AND_STRUCTURED |
| sell/crush relic | relics + player | relic removed + resources | item disappears | VISUAL_AND_STRUCTURED, R4 safety |
| level Titan/Anima | animas + player | Anima level/xp + resources | details UI | VISUAL_AND_STRUCTURED |
| summon hero | heroes + player | hero roster/received counts + resource spend | summon result UI | VISUAL_AND_STRUCTURED |
| summon Titan/Anima | animas + player | anima roster/received counts + resources | summon result UI | VISUAL_AND_STRUCTURED |
| purchase | shop + player | purchase/reward state + resources | purchase confirmation | BLOCKED by default |

## Important current implementation rule

Until a source parser exists, do not pretend its structured verification exists.

Example:
Arena parser is documented but not implemented in live AccountState yet.

Therefore a current Arena action may only:
- invalidate `player` if token/resources are expected to change,
- use visual verification for Arena-specific state,
- and must NOT fabricate an `arena` source.

When PlayerArenaModel becomes live, the same Skill can upgrade to stronger structured verification without changing planner semantics.

## Legacy config compatibility

Old flow actions may have no verification metadata.

Recommended compatibility behavior:

Navigation-looking legacy action:
- no structured invalidation
- retain current visual transition logic

Unknown legacy action:
- do NOT globally invalidate all sources
- mark verification confidence as LEGACY_UNDECLARED
- force normal metadata poll
- rely on visual transition only
- diagnostics should flag the action for migration to an explicit contract

This is safer than poisoning all account sources.

## Verification timing

Each ActionExpectation should distinguish:

- retry_interval
- verification_timeout
- give_up_timeout if a Skill performs several retries

Do not use one magic timeout for all semantics.

Suggested starting ranges:

Navigation:
- retry observation: capture-speed / decision loop
- verification timeout: 1-2 s

Snapshot-backed account change:
- visual timeout: 1-3 s
- structured save grace: configurable 0.5-5 s initially
- actual values must be measured on the real client

Battle transition:
- visual transition should occur quickly
- structured persistence may lag and should be measured separately

These are engineering starting points, not confirmed game timings.

## Source-change semantics

A source change means:
- file digest changed
AND
- new file parses successfully

A timestamp/stat change alone is not semantic evidence.

A corrupt/new partial write is FAILURE/WAITING, not success.

An unchanged digest after an action does not prove failure until the configured save grace/verification deadline expires.

## Pre-action evidence capture

Before a state-changing action record:

- action id
- current screen
- relevant source digests
- relevant aggregate versions
- relevant semantic values
- timestamp

After action compare against this baseline.

Success predicates should prefer semantic deltas where possible.

Examples:

Equip relic:
- BEFORE hero[H].relic_id_by_slot[S] != R
- AFTER hero[H].relic_id_by_slot[S] == R
AND
- relic[R].equipped_hero_id == H

Claim reward:
- BEFORE claimable == true
- AFTER claimable == false
or reward state includes claimed marker

Resource spend:
- do not merely require "PlayerModel changed"
- verify the specific balance delta when cost is known.

## Verification result model

Recommended result:

ActionVerificationResult
- status: SUCCESS | FAILURE | TIMEOUT | CANCELLED | INCONCLUSIVE
- visual_satisfied
- changed_sources
- semantic_predicates_satisfied
- errors
- elapsed
- evidence summary

INCONCLUSIVE is important.

Example:
Visual transition succeeded but expected snapshot has not persisted before timeout.

For R0/R1 navigation this may still be acceptable if structured evidence was never required.

For R3/R4 account changes it should not be silently promoted to success.

## Failure policy

On verification failure:

1. do not repeat blindly
2. refresh relevant observations
3. classify:
   - visual failure
   - structured timeout
   - corrupt/partial source
   - conflicting evidence
4. apply Skill retry policy
5. after bounded retries open circuit / replan

This mirrors the proven retry-vs-give-up separation used by robust automation systems.

## Current priority for implementation

1. scoped invalidation
2. explicit ActionExpectation
3. source digest/version baseline capture
4. verification result object
5. visual-only legacy compatibility
6. semantic predicates later as domain Skills mature

Do not block the first implementation on every future domain source.
