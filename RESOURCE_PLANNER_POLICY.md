# RESOURCE PLANNER POLICY

Date: 2026-11-14

Purpose: define how the live bot approves, blocks and prioritizes resource-spending goals.

This is a policy layer above raw ResourceTypeId balances.
It must not read MemoryPack directly.

## Research basis

Relevant robust-agent patterns reviewed:
- OpenKore separates action cadence from give-up windows and records repeated failure before dropping a target.
- BehaviorTree.CPP exposes explicit Preconditions, Retry and Timeout decorators plus Blackboard state.

Applied Invokers rule:
- resource spending requires fresh preconditions
- retry timing is separate from give-up/circuit policy
- no resource-spending Goal is allowed to infer unknown caps/costs

## Planner decision outputs

ResourcePlanner should return one of:

- ALLOW
- ALLOW_WITH_LIMIT
- DENY_RESERVE
- DENY_EVENT_SAVE
- DENY_UNKNOWN_COST
- DENY_STALE_BALANCE
- DENY_UNKNOWN_CAP
- DENY_POLICY
- DENY_RISK
- DENY_NO_USEFUL_SINK

Each decision should carry:
- resource id/name
- current balance
- requested amount
- configured reserve
- effective cap if known
- source freshness
- reason
- policy version/config reference

## Resource classes

### Regenerating / capped operational resources
Examples:
- Energy
- Arena_Token
- Token_MultiBattle
- mode-specific keys/attempts where regeneration/reset is verified

Policy:
- may create anti-waste pressure
- may be spent before overflow
- reserve may be zero or low
- cap/regeneration must be known from config or verified data

### Common progression currencies
Examples:
- Gold
- Memorium

Policy:
- configurable reserve
- spend only when a downstream Goal has sufficient utility
- never spend simply because balance is high

### Scarce progression resources
Examples:
- Stars
- Orbs
- ascension/awakening materials
- Codexes
- Prisms

Policy:
- default conservative
- support explicit save-for-event policy
- target-specific budget preferred

### Premium/paid resources
Examples:
- Gems
- purchase-related state

Policy:
- spending blocked by default
- requires explicit user policy
- real-money purchase remains blocked

## Reserve model

Per resource support:

- hard_minimum
- soft_minimum
- target_reserve
- event_reserve
- emergency_reserve
- max_spend_per_action
- max_spend_per_session

Hard minimum:
Never cross.

Soft minimum:
May cross only for high-priority goals if policy explicitly permits.

Event reserve:
Blocks unrelated spending during configured event-save windows.

## Unknown cost rule

If the bot cannot determine the expected cost of an account-changing action:

- R0/R1: irrelevant
- R2+: DENY_UNKNOWN_COST unless the action's domain policy explicitly allows an observed fixed-cost confirmation flow

No guessed costs.

## Freshness rule

Resource decisions require fresh PlayerModel.Resources.

Recommended:
- use AccountState freshness contract
- if player source is stale/awaiting_change/error -> DENY_STALE_BALANCE
- do not fall back to OCR when structured PlayerModel is available but stale
- visual HUD can be diagnostics/cross-check, not hidden override

## Cap rule

Never hardcode an Arena/Energy cap unless confirmed.

Cap source priority:
1. verified static/config game data
2. verified structured runtime state
3. explicit local user config
4. otherwise unknown

If anti-waste scoring requires a cap and cap is unknown:
- DENY_UNKNOWN_CAP for cap-based behavior
- ordinary non-cap-based Arena Goal may still be eligible if another reason exists

## Overflow pressure

For known capped resource:

usable = max(0, balance - hard_minimum)
headroom = cap - balance

Pressure should rise as headroom approaches zero.

Recommended normalized concept:

pressure = clamp01((balance - pressure_start) / (cap - pressure_start))

where pressure_start is configurable, e.g. a fraction of cap.

Do not bind implementation to one formula; acceptance matters:
- lower balance -> little/no overflow pressure
- near-cap -> strong pressure
- at/over cap -> maximum pressure
- reserve constraints still apply

## Regeneration pressure

If regeneration interval/sync data is verified, increase urgency when:
- next regeneration tick is near
AND
- balance is close enough to cap that the tick would be partially/fully wasted

Do not infer exact regeneration interval from EnergySyncTime/ArenaTokenSyncTime alone.
The interval must be known independently.

## Spend authorization flow

Goal asks ResourcePlanner:

request:
- resource
- amount
- purpose
- risk class
- goal id
- current AccountState
- optional deadline/event context

Planner:
1. validate fresh balance
2. validate cost known
3. load reserve policy
4. check event-save constraints
5. check session/action spend limits
6. check cap/overflow context if relevant
7. return decision

The domain Goal never mutates balances.

## Semantic post-spend verification

When expected cost is known:

before_balance = B
expected_cost = C
after_balance should equal B - C

Use exact delta where game mechanics support it.

If reward/refund can occur in same transaction:
- exact delta may be inappropriate
- use domain semantic predicate instead

A generic "resource decreased" predicate is weaker and should only be used where exact cost is not yet known but decrease itself is authoritative.

## Arena Token policy

Resource ID:
- Arena_Token = 21

Current implementation may read the balance from PlayerModel.Resources.

Do NOT assume:
- token cap
- regeneration interval
- exact cost timing
unless verified.

Recommended config fields:

arena:
  token:
    cap: null
    pressure_start: null
    reserve: 0
    start_battle_cost: 1
    verification_timeout: configurable

The value `start_battle_cost: 1` must only become default after real/live or static-data verification. Until then it is an explicit configured assumption.

## MultiBattle Token policy

Resource ID:
- Token_MultiBattle = 11

Same rules:
- no guessed cap
- no guessed session cost
- budget based on selected session settings once verified

## Gold / Memorium policy

Use hard reserve + per-goal spend cap.

Examples of future policy:
- never spend below reserve on low-priority gear upgrades
- allow targeted hero progression only if selected development plan approves

Do not implement optimization values before game-economy analysis.

## Stars / Orbs policy

Default:
- save unless an explicit summon/development/event policy permits spend

Event windows may set:
- DENY_EVENT_SAVE

This is a policy constraint, not an executable Goal.

## Failure/retry interaction

A resource-spending action that is INCONCLUSIVE must not be immediately repeated.

Required sequence:
1. reread resource state
2. check semantic delta
3. re-evaluate whether spend occurred
4. only then decide retry

This prevents double spend.

## Diagnostics

Every ResourcePlanner decision should log:
- goal id
- resource id/name
- balance
- requested cost
- reserve
- cap if known
- overflow pressure
- decision
- reason
- source age/version

No raw snapshot bytes.
