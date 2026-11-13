"""Legacy capabilities retained for compatibility; new Actor owns all execution.
All legacy live capabilities are disabled.
"""
from dataclasses import dataclass

# EINZIGE Laufzeit-Wahrheit darüber, was der Bot tatsächlich ausführen kann.
# kind -> (Agent, Beschreibung, executable)
# executable=False bedeutet: Knowledge kennt die Aufgabe, aber es gibt keinen verifizierten Aktor.
# Solche Quests werden vom Planner nie gewählt und nie per LOS gestartet.
CAPABILITIES={
 'campaign':     ('CampaignAgent','exact chapter/stage farming + replay',False),
 'summon':       ('SummonAgent','green Wild Star only; smallest safe spend',False),
 'invoker':      ('DevelopmentAgent','invoker level routing (Automatische Auswahl -> LEVELN)',False),
 'arena':        ('ArenaAgent','arena quest/event routing',False),
 'awaken':       ('DevelopmentAgent','awakening routing',False),
 'relic_sell':   ('RelicAgent','relic sell task',False),
 'relic_upgrade':('RelicAgent','relic upgrade task',False),
 'farm':         ('BossAgent','boss/crest farming from Knowledge',False),
}
EXECUTABLE_KINDS=tuple(k for k,v in CAPABILITIES.items() if v[2])
OBSERVE_ONLY_KINDS=tuple(k for k,v in CAPABILITIES.items() if not v[2])

@dataclass
class Assignment:
    agent: str
    reason: str
    executable: bool

class AgentManager:
    """Agents own policy; the screen actor still enforces safe, verified clicks."""
    def can_execute(self, kind):
        return bool(CAPABILITIES.get(kind,(None,None,False))[2])
    def assign(self, plan):
        kind=(plan or {}).get('kind','unknown')
        a,r,ex=CAPABILITIES.get(kind,('QuestAgent','quest remains fail-safe/manual',False))
        return Assignment(a,r,ex)
    def campaign_result_action(self, plan, rows, norm):
        if not plan or plan.get('kind')!='campaign': return None
        # Same-stage farming: official result screen has Replay. German clients may localize it.
        for r in rows:
            t=norm(r.get('text',''))
            if t in ('REPLAY','WIEDERHOLEN','ERNEUT','NOCHMAL') and 1200 <= r.get('x',0) <= 1910 and 650 <= r.get('y',0) <= 1040:
                return r
        return None
    def summon_count(self, plan, have10, have1, left):
        """How many green stars to spend in this click. left = still allowed for this quest."""
        if not plan or plan.get('kind')!='summon' or left<=0: return 0
        if left>=10 and have10: return 10
        if have1: return 1
        return 0
