"""Refresh evidence and conservative invalidation of derived arena artifacts."""
from dataclasses import dataclass

CACHE_KEYS=("arena_traversal","arena_row_mapping","arena_viewport_mapping","arena_ranking","arena_selected_target")

@dataclass(frozen=True,slots=True)
class ArenaRevision:
    digest: str
    version: int
    fingerprint: str
    refresh_ticks: int

def update_arena(facts,account):
    item=account.sources.get("arena") if account else None
    old=facts.get("arena_revision")
    if not item or not item.fresh(2) or not item.digest:
        removed=False
        for key in CACHE_KEYS:
            if key in facts:
                del facts[key]
                removed=True
        return removed
    model=item.model
    if not hasattr(model,"opponent_set_fingerprint"):
        return False
    new=ArenaRevision(item.digest,model.version,model.opponent_set_fingerprint,model.last_opponents_refresh_ticks)
    facts["arena_revision"]=new
    if old is None or old==new:
        return False
    source_changed=(old.digest,old.version)!=(new.digest,new.version)
    semantic=source_changed and old.fingerprint!=new.fingerprint
    time_changed=old.refresh_ticks!=new.refresh_ticks
    facts["arena_refresh_event"]={"semantic_refresh":semantic,"source_changed":source_changed,
        "refresh_time_changed":time_changed,"before":old,"after":new}
    # Conservative invalidation even for same-set source changes; coordinates are not identity.
    if source_changed or time_changed:
        for key in CACHE_KEYS:
            facts.pop(key,None)
        return True
    return False
