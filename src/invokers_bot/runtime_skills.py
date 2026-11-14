"""Skill registration boundary; engine dispatches generic configured skill ids."""
from .arena_skill import run_arena_traversal, discard_stale_inventory

from .arena_refresh import update_arena
from .arena_ranking import update_ranking

SKILLS = {"arena_traversal": run_arena_traversal}


def invoke(engine, action, cancelled):
    from .action_verification import ActionResult
    skill = SKILLS.get(action.get("skill"))
    if skill is None:
        return ActionResult(False, "UNKNOWN_SKILL")
    return skill(engine, action, cancelled)


def account_updated(facts, account, raw=None):
    changed = update_arena(facts, account)
    stale = discard_stale_inventory(facts, account)
    if raw is not None:
        update_ranking(facts,account,raw)
    return stale or changed
