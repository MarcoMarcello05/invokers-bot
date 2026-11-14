# LIVE SKILL VERIFICATION CONTRACT

Date: 2026-11-14

Purpose: define the contract every future live Skill should expose.

## Skill metadata

Each Skill should declare:

- id
- domain
- risk_class
- required_screen or navigation capability
- required_account_sources
- freshness limits
- input actions
- retry policy
- cancellation points

## Each state-changing action declares an ActionExpectation

Fields:

- invalidates_sources
- expects_changed_sources
- expected_visual_states
- verification_mode
- verification_timeout
- optional semantic predicate id

## Why action-level, not only skill-level

A Skill may contain:

1. open menu
2. select item
3. confirm action

Only step 3 may change account state.

If invalidation is attached only to the Skill, the bot can unnecessarily invalidate data during navigation.

Therefore:
- Skill defines the overall objective/risk/retry policy.
- Action defines the immediate expected effect.

## Example: EquipRelic skill

Step 1: open hero screen
- VISUAL_ONLY
- invalidates none

Step 2: open relic slot
- VISUAL_ONLY
- invalidates none

Step 3: select relic
- maybe VISUAL_ONLY if selection is not persisted yet

Step 4: confirm equip
- invalidates heroes, relics
- expects changed heroes, relics
- VISUAL_AND_STRUCTURED
- semantic predicate:
  hero[H].RelicIdBySlot[S] == R
  relic[R].EquippedHeroId == H

## Example: StartCampaignBattle

Navigation steps:
- visual only

Final Start action:
- invalidates player and battle
- visual expected: loading/battle
- structured predicate depends on measured game persistence

Do not require a guessed exact snapshot delta until real client testing confirms what is persisted at battle start.

## Example: ClaimQuestReward

Confirm claim:
- invalidates quests + player
- expected visual: claim indicator disappears
- structured:
  quest leaves claimable state
  and/or resources update if reward includes resources

## Risk interaction

R0/R1:
visual-only verification may be enough.

R2:
require structured verification where resource spend is known to persist promptly; otherwise visual success + later reconciliation may be acceptable only if policy explicitly permits it.

R3:
prefer VISUAL_AND_STRUCTURED.

R4:
must require explicit semantic structured verification and dedicated safety policy. Never retry an irreversible confirmation automatically without re-reading all relevant state.

## Retry rule

Retries happen at Skill level, not by mechanically re-clicking the same ActionExpectation.

After a failed action:
- re-observe
- re-evaluate preconditions
- decide whether retry is safe

This prevents double-spend/double-confirm behavior.

## Diagnostics

Every failed verification should log:

- Skill id
- action id
- screen before/after
- relevant source digest/version before/after
- visual result
- structured result
- elapsed time
- retry count
- final reason

This will be essential for real-client tuning.
