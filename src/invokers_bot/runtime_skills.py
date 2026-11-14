"""Skill registration boundary; engine dispatches generic configured skill ids."""
from .arena_skill import run_arena_traversal, discard_stale_inventory

SKILLS = {"arena_traversal": run_arena_traversal}


def invoke(engine, action, cancelled):
    from .action_verification import ActionResult
    skill = SKILLS.get(action.get("skill"))
    if skill is None:
        return ActionResult(False, "UNKNOWN_SKILL")
    return skill(engine, action, cancelled)


def account_updated(facts, account):
    return discard_stale_inventory(facts, account)
