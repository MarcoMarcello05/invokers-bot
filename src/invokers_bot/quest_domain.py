"""Fresh semantic quest facts only. Completed does not mean UI claimable."""
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Protocol
from .quests_model import QuestKind, QuestStateId, PlayerQuestsState, PeriodicWindow


@dataclass(frozen=True, slots=True)
class QuestProvenance:
    digest: str
    version: int
    observed_at: float


@dataclass(frozen=True, slots=True)
class ClaimableQuest:
    """Candidate only: no reward, click, route or claim authorization."""
    quest_id: int
    prototype_id: int
    kind: QuestKind
    state_id: int
    group_or_page: int
    time_started_utc: datetime
    periodic_finish_time_utc: datetime | None
    provenance: QuestProvenance


@dataclass(frozen=True, slots=True)
class QuestSummary:
    provenance: QuestProvenance
    total_active: int
    total_completed_state_active: int
    periodic_count: int
    achievement_count: int
    book_count: int
    completed_prototype_count: int
    total_completed_quests: int


@dataclass(frozen=True, slots=True)
class QuestGoalFacts:
    source_fresh: bool
    provenance: QuestProvenance | None
    has_completed_candidates: bool | None
    completed_candidate_count: int | None
    nearest_known_periodic_finish_time: datetime | None
    groups_with_completed_candidates: tuple[int,...] | None


@dataclass(frozen=True, slots=True)
class QuestView:
    state: PlayerQuestsState
    provenance: QuestProvenance

    def all_completed_candidates(self):
        result=[]
        for q in sorted(self.state.active_by_id.values(),key=lambda q:q.quest_id):
            if q.state_id!=QuestStateId.COMPLETED:
                continue
            window=self.state.periodic_groups.get(q.group_or_page) if q.kind==QuestKind.PERIODIC else None
            result.append(ClaimableQuest(q.quest_id,q.prototype_id,q.kind,q.state_id,q.group_or_page,
                q.time_started_utc,window.finish_time_utc if window else None,self.provenance))
        return tuple(result)

    def periodic_candidates(self,group):
        return tuple(q for q in self.all_completed_candidates()
                     if q.kind==QuestKind.PERIODIC and q.group_or_page==group)

    def active_periodic_windows(self) -> tuple[PeriodicWindow,...]:
        # Persisted windows only; no assumption about current wall-clock validity.
        return tuple(self.state.periodic_groups[k] for k in sorted(self.state.periodic_groups))

    def summary(self):
        quests=tuple(self.state.active_by_id.values())
        return QuestSummary(self.provenance,len(quests),len(self.all_completed_candidates()),
            sum(q.kind==QuestKind.PERIODIC for q in quests),
            sum(q.kind==QuestKind.ACHIEVEMENT for q in quests),
            sum(q.kind==QuestKind.BOOK for q in quests),
            len(self.state.completed_prototype_ids),self.state.total_completed_quests)

    def goal_facts(self):
        candidates=self.all_completed_candidates()
        finishes=[w.finish_time_utc for w in self.active_periodic_windows() if w.finish_time_utc is not None]
        return QuestGoalFacts(True,self.provenance,bool(candidates),len(candidates),min(finishes,default=None),
            tuple(sorted({q.group_or_page for q in candidates if q.kind==QuestKind.PERIODIC})))


def quest_view(account,*,now,max_age=2.0):
    """Caller supplies monotonic now; expired/error/pending sources are unusable."""
    if not isfinite(now) or not isfinite(max_age) or max_age<=0:
        raise ValueError("invalid quest freshness window")
    item=account.sources.get("quests") if account else None
    if not item or not item.digest or not item.fresh(max_age,now) or not isinstance(item.model,PlayerQuestsState):
        return None
    return QuestView(item.model,QuestProvenance(item.digest,item.model.version,item.checked_at))


def quest_goal_facts(account,*,now,max_age=2.0):
    view=quest_view(account,now=now,max_age=max_age)
    return view.goal_facts() if view else QuestGoalFacts(False,None,None,None,None,None)


class QuestDefinitionCatalog(Protocol):
    """Future verified static-data boundary. No implementation or ID guesses.

    A catalog must bind to both game build and static-data revision. A lookup
    with mismatched versions must return no definition. Objective/reward types
    remain intentionally unspecified until the static wire format is verified.
    """
    def lookup(self,prototype_id:int,*,game_build:str,static_revision:str) -> object | None: ...
