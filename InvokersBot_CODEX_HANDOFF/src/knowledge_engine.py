import json,re
from config import MAX_DEFEATS_SAME_TARGET
from pathlib import Path
K=Path(__file__).resolve().parent/'knowledge'/'game_knowledge.json'

class Knowledge:
    def __init__(self):
        self.data=json.loads(K.read_text(encoding='utf-8'))

    def farm_for(self, need):
        n=need.lower(); a=self.data.get('awakening',{})
        maps={
            ('unterstützungs-wappen','unterstuetzungs-wappen'): 'Galvos',
            ('nahkampf-wappen',): 'Yskara', ('fernkampf-wappen',): 'Koltmos', ('tank-wappen',): 'Hyxxis'
        }
        for keys,target in maps.items():
            if any(k in n for k in keys): return target
        if 'crest' in n or 'wappen' in n: return 'Class-Crest-Boss passend zur Klasse'
        if 'spark' in n or 'funke' in n: return 'Titan Spark: '+str(a.get('titan_spark','Boss/Event'))
        if 'astral' in n: return 'Astral Essence: '+str(a.get('astral_essence','Boss/Event'))
        for name,v in self.data.get('relic_sets',{}).items():
            if name.lower() in n: return f'{name}: Campaign Kapitel {v.get("campaign_chapter","?")} / {v.get("boss","Boss")}'
        return None

    def parse_quest(self,text):
        t=' '.join(text.split()); l=t.lower()
        # Block premium/shop/profile actions, but do not substring-match "kauf" inside "verkaufe".
        premium_or_profile = any(x in l for x in ('edelstein','shop','vip','push-benachr','avatar'))
        purchase = bool(re.search(r'\b(?:kauf|kaufe|kaufen|gekauft)\b', l))
        if premium_or_profile or purchase:
            return {'kind':'blocked','text':t,'reason':'Premium/Shop/Profil nicht automatisch','score':-100}
        if any(x in l for x in ('unterschiedlichen tagen','spiele das spiel an','täglicher quests','taeglicher quests')) and ('mal' in l or 'tagen' in l):
            return {'kind':'manual','text':t,'reason':'Zeit-/mehrtägige Aufgabe','score':-50}
        ch=re.search(r'kapitel\s*(\d+)',l); lv=re.search(r'(?:level|stufe)\s*(\d+)',l)
        qty=re.search(r'(?:gewinne|schließe|schliesse|beschwöre|beschwoere|verkaufe|upgrade|erwecke)\s*(\d+)',l)
        if any(x in l for x in ('kampagne','handschuh','stiefel','reliqu')) and not ('verkaufe' in l or 'upgrade' in l):
            target='Kampagne'
            if ch: target+=f' Kapitel {ch.group(1)}'
            if lv: target+=f' Level {lv.group(1)}'
            return {'kind':'campaign','text':t,'target':target,'chapter':int(ch.group(1)) if ch else None,'level':int(lv.group(1)) if lv else None,'quantity':int(qty.group(1)) if qty else 1,'score':60}
        if 'arena' in l: return {'kind':'arena','text':t,'target':'Arena','quantity':int(qty.group(1)) if qty else 1,'score':50}
        if any(x in l for x in ('beschwör','beschwoer')):
            # User rule: only green/Wild Invoker stars. Rarity-specific rare/epic/legendary goals are not force-spent.
            if any(x in l for x in ('seltene invoker','epische invoker','legendär','legendaer','titan')):
                return {'kind':'resource_guarded','text':t,'reason':'Nicht gezielt wertvolle Beschwörungsressourcen ausgeben','score':-20}
            return {'kind':'summon','text':t,'target':'Beschwörung nur Stern der Wildnis','quantity':int(qty.group(1)) if qty else 1,'score':45}
        if 'erwecke' in l: return {'kind':'awaken','text':t,'target':'Invoker erwecken','quantity':int(qty.group(1)) if qty else 1,'score':35}
        if any(x in l for x in ('aufsteigen','level')) and 'reliqu' not in l:
            return {'kind':'invoker','text':t,'target':'Invoker entwickeln','score':35}
        if any(x in l for x in ('upgrade','verkaufe')) and any(x in l for x in ('reliqu','accessoire')):
            kind='relic_sell' if 'verkaufe' in l else 'relic_upgrade'
            return {'kind':kind,'text':t,'target':'Relikte verkaufen' if kind=='relic_sell' else 'Relikte upgraden','quantity':int(qty.group(1)) if qty else 1,'score':30}
        f=self.farm_for(l)
        if f: return {'kind':'farm','text':t,'target':f,'score':55}
        return {'kind':'unknown','text':t,'reason':'Text nicht sicher verstanden','score':-10}

    def quest_signature(self,text):
        """Stable semantic signature used to re-bind a stored plan to the correct GO row."""
        l=' '.join(text.lower().split())
        # OCR/Umlaut-Varianten vereinheitlichen (ö == oe usw.), damit Beschwöre == Beschwoere
        for a,b in (('ä','ae'),('ö','oe'),('ü','ue'),('ß','ss')): l=l.replace(a,b)
        words=set(re.findall(r'[a-z]+|\d+',l))
        stop={'der','die','das','den','dem','des','in','im','auf','von','und','oder','ein','eine','einer','einem','einen','normal'}
        words={w for w in words if w not in stop and len(w)>1}
        ch=re.search(r'kapitel\s*(\d+)',l); lv=re.search(r'(?:level|stufe)\s*(\d+)',l)
        nums=tuple(re.findall(r'\d+',l))
        items=set()
        for k in ('handschuh','stiefel','reliqu','arena','kampagne','wappen','beschwoer','upgrade','verkaufe','erwecke'):
            if k in l: items.add(k)
        return {'words':words,'chapter':ch.group(1) if ch else None,'level':lv.group(1) if lv else None,'nums':nums,'items':items}

    def quest_similarity(self,a,b):
        A=self.quest_signature(a); B=self.quest_signature(b)
        # Hard conflicts: explicit chapter/level or requested item differs.
        if A['chapter'] and B['chapter'] and A['chapter']!=B['chapter']: return 0.0
        if A['level'] and B['level'] and A['level']!=B['level']: return 0.0
        if A['items'] and B['items'] and A['items'].isdisjoint(B['items']): return 0.0
        union=A['words']|B['words']; inter=A['words']&B['words']
        score=len(inter)/max(1,len(union))
        if A['chapter'] and A['chapter']==B['chapter']: score+=.12
        if A['level'] and A['level']==B['level']: score+=.18
        if A['nums'] and A['nums']==B['nums']: score+=.08
        return min(1.0,score)

    def event_action(self,name):
        return self.data.get('events',{}).get('types',{}).get(name)

    def event_bonus_for(self, plan, active_events=()):
        """Connect event knowledge to planning. Unknown/inactive events add nothing."""
        kind=plan.get('kind'); bonus=0; reasons=[]
        for name in active_events:
            action=self.event_action(name)
            if not action: continue
            a=action.lower()
            hit=(kind=='arena' and 'arena' in a) or (kind=='campaign' and 'campaign' in a) or (kind=='summon' and 'invoker summon' in a) or (kind in ('invoker','awaken') and 'invoker' in a and ('level' in a or 'develop' in a)) or (kind.startswith('relic') and ('relic' in a or 'gear' in a)) or (kind=='farm' and ('crest' in a or 'boss' in a))
            if hit: bonus+=25; reasons.append(name)
        return bonus,reasons

    def choose_best(self,candidates,failures=None,active_events=(),can_execute=None):
        """can_execute(kind)->bool kommt vom AgentManager (zentrale Capability-Quelle).
        Ohne can_execute wird bewusst NICHTS gewählt (fail-safe)."""
        failures=failures or {}; scored=[]
        if can_execute is None: return None
        actionable=[c for c in candidates if can_execute(c['plan'].get('kind'))]
        for c in actionable:
            p=c['plan']; score=float(p.get('score',0)); reasons=[]
            # Overlap: same activity advances several quests.
            same=[x for x in actionable if x['plan'].get('kind')==p.get('kind')]
            if p.get('kind')=='campaign':
                ch=p.get('chapter'); lv=p.get('level')
                for x in actionable:
                    q=x['plan']
                    if q.get('kind')!='campaign' or x is c: continue
                    if ch and q.get('chapter')==ch: score+=12; reasons.append('gleiches Kapitel')
                    if ch and lv and q.get('chapter')==ch and q.get('level')==lv: score+=30; reasons.append('gleiches Level')
            else:
                score += max(0,len(same)-1)*10
                if len(same)>1: reasons.append(f'{len(same)} passende Quests')
            eb,ev=self.event_bonus_for(p,active_events); score+=eb
            if ev: reasons.append('Event: '+', '.join(ev))
            target=p.get('target') or p.get('kind'); fails=int(failures.get(target,0))
            if fails>=MAX_DEFEATS_SAME_TARGET: continue  # Niederlagenlimit: dieses Ziel nicht mehr wählen
            if fails: score-=fails*35; reasons.append(f'{fails} Niederlage(n)')
            scored.append((score,c,reasons))
        if not scored:return None
        scored.sort(key=lambda z:z[0],reverse=True)
        score,c,reasons=scored[0]; out=dict(c); out['planner_score']=score; out['planner_reasons']=reasons
        return out
