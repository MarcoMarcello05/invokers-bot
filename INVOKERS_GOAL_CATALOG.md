# INVOKERS GOAL CATALOG — Initial autonomous domain goals

Date: 2026-11-14

Purpose: turn the generic planner policy into concrete Invokers goals with explicit triggers, required facts, costs, risk, cancellation and success criteria.

Research basis:
- utility selection + planning separation
- priority tiers / commitment
- staleness-aware scheduling
- bounded retries / circuit breakers

References:
- https://github.com/erkan612/gmsmartagent
- https://github.com/tayyabtahir143/pulse/blob/main/docs/monitoring/ADAPTIVE_POLLING.md
- https://github.com/OpenKore/openkore
- https://github.com/BehaviorTree/BehaviorTree.CPP

## Global goal families

### G-SAFE-001 RecoverKnownScreen
Purpose:
Return from UNKNOWN/unexpected UI to a known safe state.

Generate when:
- visual screen unknown beyond grace period
- unexpected modal blocks current task
- navigation transition verification fails

Required facts:
- visual.screen
- visual.modal
- capture health
- navigation capability graph

Risk:
R1 REVERSIBLE

Priority:
Very high when current task cannot proceed.

Success:
- known screen recognized with sufficient confidence

Cancel:
- F12 stop
- capture unhealthy
- repeated recovery failure -> circuit open

### G-SAFE-002 ReconcileConflictedState
Purpose:
Resolve disagreement between structured state and visible UI.

Generate when:
- a required fact is marked STALE_OR_CONFLICTED

Actions:
- reread relevant snapshot
- refresh visual recognition
- optionally navigate to authoritative screen

Success:
- conflict resolved or task safely blocked

Risk:
R0/R1

### G-CLAIM-001 ClaimCompletedQuestReward
Generate when:
- quest state == Completed
- reward claim path capability exists

Inputs:
- quests.active
- quest type/group
- reset/deadline
- visual/navigation capability

Base priority:
High

Boosts:
- near daily/weekly/monthly reset
- reward needed by another active progression goal

Risk:
R1 unless claim causes known irreversible choice

Success:
- quest state/reward state changes or quest leaves claimable set

### G-CLAIM-002 ClaimCampaignReward
Generate when:
- PlayerBattleModel indicates eligible first-clear/chapter reward
- reward not present in ClaimedCampaign* set

Inputs:
- battle.level_stats
- battle.claimed_campaign_rewards
- visual campaign navigation

Risk:
R1

Success:
- structured claimed-reward state updates

### G-CLAIM-003 ClaimClanReward
Generate when:
- pending activity/boss chest exists
- claim not already recorded

Inputs:
- clan pending chest facts
- clan membership
- reset windows

Risk:
R1

### G-CLAIM-004 ClaimEventTournamentReward
Generate when:
- structured event/tournament state exposes claimable reward

Inputs:
- events participation/reward state
- event end time if known

Priority:
High near expiry.

### G-CLAIM-005 ClaimInboxReward
Generate when:
- inbox contains claimable reward item

Current blocker:
nested InboxItem parser not yet byte-verified in current snapshot.

Status:
Future goal generator.

## Resource-preservation / anti-waste goals

### G-RES-001 SpendArenaTokensBeforeCap
Generate when:
- Arena token balance is near configured cap
- at least one acceptable opponent exists
- no save policy blocks spend

Inputs:
- resources.Arena_Token
- arena opponents
- arena points/stats
- arena refresh time
- selected team capability

Risk:
R2 CONSUMABLE_LOW

Positive scoring:
- overflow pressure
- Arena progression value
- quest/event synergy

Negative scoring:
- poor opponent quality
- high expected loss
- expensive navigation/time

Success:
- Arena token decreases
- battle result recorded

Cancel:
- token count changed unexpectedly
- opponent state stale/conflicted
- no acceptable matchup

### G-RES-002 SpendEnergyBeforeCap
Generate when:
- Energy near cap / regeneration would be wasted
- useful farming/progression target available

Inputs:
- resources.Energy
- EnergySyncTime
- campaign/boss/spire availability
- farming targets
- quest/event objectives

Risk:
R2

Decision:
ResourcePlanner chooses sink based on progression and event policies.

### G-RES-003 UseExpiringAttempt
Generate when:
- daily/weekly key/attempt will reset soon
- useful eligible activity exists

Examples:
- boss keys
- spire attempts
- clan boss attempts where applicable

Priority:
Rises strongly near reset.

## Progression goals

### G-PROG-001 ProgressCampaign
Generate when:
- next campaign stage is known/uncompleted
- Energy/battle requirements available
- team can be formed

Inputs:
- LevelStats
- campaign reward state
- resources.Energy
- roster
- presets/team builder capability

Risk:
R2

Success:
- victory/stars/level progress updates

Failure:
- repeated battle loss can lower utility or block stage pending team improvement

### G-PROG-002 ProgressQuestObjective
Generate when:
- active quest is not complete
- objective maps to a supported domain capability

Inputs:
- quest state/progress
- static quest definition
- domain capability registry
- resource availability

Scoring:
- reset urgency
- reward value
- can combine with another useful goal

Important:
Quest goal should usually select an underlying domain goal rather than directly encode clicks.

Example:
"Win 3 Arena battles" adds synergy to G-RES-001/G-ARENA-001.

### G-PROG-003 ProgressSpire
Generate when:
- spire attempt/key available
- next useful floor known
- capability implemented

Inputs:
- battle tower/spire state
- resources/keys
- roster/team builder

Risk:
R2

### G-PROG-004 ProgressBoss
Generate when:
- boss attempt/key exists
- boss domain capability available
- target reward useful

Inputs:
- battle/boss state
- resources
- roster/team
- desired resource targets

### G-PROG-005 ImproveSelectedHero
Generate when:
- configured hero-development target exists
- improvement is affordable and policy-approved

Possible subgoals:
- level with XP
- ascend
- awaken
- upgrade skill
- equip better relic

Risk:
R3 ACCOUNT_CHANGE

Hard gates:
- target hero confirmed
- resource budget approved
- no protected material consumed
- expected change fully known

### G-PROG-006 ImproveSelectedTitan
Same philosophy as hero improvement.

Risk:
R3.

## Farming goals

### G-FARM-001 FarmConfiguredResource
Generate when:
- user/planner has active resource need
- target farming source is known
- farming is more useful than progression alternatives

Inputs:
- desired resource deficit
- available farming locations
- expected yield
- Energy/tokens
- MultiBattle capability

Priority:
Depends on downstream blocked goals.

### G-FARM-002 StartMultiBattleSession
Generate when:
- repeated farming/progression target selected
- MultiBattle tokens/resources available
- session settings are policy-valid

Inputs:
- battle.MultiBattleSession
- resources.Token_MultiBattle
- selected stage
- stop-loss settings
- background-battle policy

Risk:
R2

Success:
- MultiBattleSession enters active state

### G-FARM-003 ContinueOrCollectMultiBattle
Generate when:
- session active or completed
- collection/continuation action required

Structured source:
PlayerBattleModel.MultiBattleSession.

## Arena-specific goals

### G-ARENA-001 FightBestAcceptableOpponent
Generate when:
- Arena token available
- fresh opponent list exists
- at least one candidate passes matchup policy

Candidate score may use:
- opponent points
- level
- team composition
- previous result
- own roster/team estimate
- quest/event synergy

Risk:
R2

Success:
- battle result recorded and token consumed

### G-ARENA-002 RefreshOpponents
Generate when:
- no acceptable opponent
- refresh cooldown allows
- refresh cost/policy acceptable

Inputs:
- LastOpponentsRefreshTime
- opponent quality distribution
- refresh policy

Risk:
R1/R2 depending on cost.

## Clan goals

### G-CLAN-001 ProcessClanActivity
Generate when:
- member of clan
- daily activity has useful action/claim state

Inputs:
- PlayerClanModel
- quest synergy

### G-CLAN-002 FightClanBoss2
Generate when:
- Boss2 attempt/replay available
- difficulty eligible
- expected reward useful
- team capability available

Inputs:
- Boss2 state
- best damage by difficulty
- replay count
- roster/team

Risk:
R2

### G-CLAN-003 ClaimClanBoss2Reward
Claim-only version, higher priority than new fight near reset.

## Event goals

### G-EVENT-001 ProgressActiveEvent
Generate when:
- event is active
- objective maps to supported activities
- expected marginal reward justifies cost

Planner behavior:
Event should usually add synergy/weight to underlying domain goals rather than create duplicate execution paths.

### G-EVENT-002 SaveResourceForEvent
Generate as a policy constraint rather than an executable click task.

Effect:
ResourcePlanner marks selected resources DENY_EVENT_SAVE for unrelated goals.

## Maintenance goals

### G-MAINT-001 RefreshStructuredState
Generate when:
- required snapshot fact stale
- source health otherwise good

Risk:
R0

### G-MAINT-002 InventoryPressureRelief
Generate when:
- inventory pressure detected
- safe non-destructive action exists

Until irreversible policies exist:
- may sort/filter/inspect
- MUST NOT sell/crush/dismiss automatically

### G-MAINT-003 DiagnosticsBundle
Generate on repeated failure/circuit open.

Output:
- screenshot
- recognized screen
- relevant structured facts + ages
- current goal/task/skill
- failure reason
- last actions

Risk:
R0

## Goal synergy rules

Goals should not duplicate work when one activity advances several objectives.

Examples:

Arena battle may satisfy:
- spend near-cap token
- daily quest
- achievement
- event objective
- Arena progression

Represent as ONE Arena execution goal with synergy bonuses from the other objectives.

Campaign stage may satisfy:
- campaign progression
- spend near-cap Energy
- quest objective
- material farming target

Avoid multiple competing Goals for the exact same action.

## Priority tiers

Tier 0 SAFETY
- F12/abort
- inconsistent state
- destructive-action guard
- reconnect/recovery

Tier 1 EXPIRING / CLAIM
- expiring claimable reward
- near-reset attempt/token waste
- daily/weekly tasks near deadline

Tier 2 ACTIVE SESSION
- complete current battle/MultiBattle/claim chain
- valid current goal continuation

Tier 3 PROGRESSION
- campaign/spire/boss/arena progression
- quests

Tier 4 DEVELOPMENT
- hero/titan/gear improvement

Tier 5 MAINTENANCE
- housekeeping
- optional diagnostics

Tier is not the final score. It defines broad preemption bands.

## Preemption policy

Immediate preemption:
- safety event
- invalid/stale prerequisite for current goal
- reconnect/error
- urgent expiring opportunity crossing configured threshold

Deferred preemption:
- slightly better normal progression goal
- maintenance
- non-urgent reward

Never interrupt:
- an atomic UI confirmation sequence mid-action unless safety requires it
- battle start after irreversible token/energy spend unless recovery requires it

## Required developer-facing abstractions later

GoalCandidate:
- id
- domain
- tier
- eligibility result/reasons
- utility components
- required facts
- risk class
- requested resources
- capability id
- completion predicate
- cancellation predicate

GoalEvaluation:
- eligible bool
- blocked reasons
- component scores
- total score
- evidence versions/ages

SchedulerDecision:
- selected goal
- previous goal
- switch/stay reason
- preemption reason
- timestamp

## Current implementation order

Do not code all domain goal generators at once.

Recommended:
1. core GoalCandidate/GoalEvaluation
2. Reward claim goal
3. Arena token anti-waste goal
4. Campaign progression goal
5. generic quest synergy layer
6. MultiBattle
7. clan/event goals
8. development/resource spending goals only after SafetyGate/ResourcePlanner are mature
