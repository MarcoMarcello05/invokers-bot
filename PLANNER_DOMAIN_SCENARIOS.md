# DOMAIN PRIORITY EXAMPLES — deterministic planner scenarios

Date: 2026-11-14

These scenarios are acceptance examples for the future scheduler.

## Scenario A — Claim beats normal progression

Facts:
- daily quest completed, reset in 20 minutes
- Arena tokens 2/10
- campaign next stage available

Expected:
1. ClaimCompletedQuestReward
2. replan
3. likely ProgressCampaign

Reason:
expiring completed reward belongs to higher priority band than ordinary progression.

## Scenario B — Near-cap Arena token beats campaign

Facts:
- Arena tokens 9/10
- token regen soon
- acceptable opponent exists
- campaign progression available

Expected:
FightBestAcceptableOpponent before campaign.

Reason:
avoid-waste pressure.

## Scenario C — No acceptable Arena opponent

Facts:
- token near cap
- all opponents fail matchup threshold
- refresh available for free/policy-approved

Expected:
RefreshOpponents.

If refresh unavailable/expensive:
choose another goal; do not blindly fight.

## Scenario D — Quest synergy

Facts:
- daily quest needs 3 Arena wins
- Arena token available
- normal Arena opportunity exists

Expected:
one Arena goal gets QuestSynergy bonus.
Do not create competing "do daily quest" and "spend Arena token" action loops.

## Scenario E — Event save policy

Facts:
- enough Stars to summon
- event starts soon and policy says save Stars
- summon upgrade would otherwise score well

Expected:
hero/titan summon goal blocked by DENY_EVENT_SAVE.

Reward score cannot override the reserve gate.

## Scenario F — Current MultiBattle session

Facts:
- MultiBattle session currently active/completed-awaiting-collection
- unrelated claim available but non-expiring

Expected:
finish/collect current session before switching, unless claim becomes urgent.

## Scenario G — Stale opponent state

Facts:
- cached Arena opponents are old
- visual Arena screen current
- token available

Expected:
RefreshStructuredState / reconcile.
Never spend token using stale candidate data.

## Scenario H — Hero upgrade is affordable but risky

Facts:
- hero upgrade available
- scarce ascension material required
- no explicit development target/policy

Expected:
blocked despite progression value.

## Scenario I — Failure circuit

Facts:
- open_arena failed repeatedly
- Arena navigation circuit open
- campaign navigation healthy

Expected:
Arena goals BLOCKED/CIRCUIT_OPEN.
Scheduler chooses another eligible domain instead of retry-looping Arena.

## Scenario J — Unknown screen

Facts:
- current goal CampaignProgress
- visual screen becomes UNKNOWN

Expected:
Campaign task pauses.
RecoverKnownScreen becomes Tier 0.
No blind click continues from the previous task.

## Scenario K — Reward + resource synergy

Facts:
- campaign first-clear reward is claimable
- Energy near cap
- next campaign stage also available

Expected:
claim first-clear reward first if immediate and cheap.
Then replan, likely campaign progression due overflow pressure.

## Scenario L — Anti-starvation

Facts:
- low-priority inbox claim available for a long time
- normal progression repeatedly scores slightly higher
- no deadlines

Expected:
bounded age boost eventually brings inbox task above ordinary progression.
It still cannot bypass risk or source-health gates.
