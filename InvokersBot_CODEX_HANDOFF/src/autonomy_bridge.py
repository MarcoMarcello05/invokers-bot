import json,time,sys
from pathlib import Path
import invokers_core as core
ROOT=Path(__file__).resolve().parent
GAME_ROOT=Path.home()/r'AppData/LocalLow/Hit_Zone/Invokers'
POLICY_FILE=ROOT/'autonomy_policy.json'; MEMORY_FILE=ROOT/'runtime'/'failure_memory.json'; PLAN_FILE=ROOT/'runtime'/'action_plan.json'

def load_json(p,default):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return default

def atomic_json(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+'.tmp'); t.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8'); t.replace(p)

def build_plan():
    policy=load_json(POLICY_FILE,{})
    mem=load_json(MEMORY_FILE,{})
    src=core.snapshot(GAME_ROOT)
    # snapshot() stores aggregate model filenames, not absolute paths. Resolve them against the live snapshot folder.
    snap_dir=GAME_ROOT/'aggregate_snapshots'
    def model_path(key):
        item=src.get(key)
        if not item: return None
        p=Path(item['file'])
        return p if p.is_absolute() else snap_dir/p
    hp=model_path('heroes'); qp=model_path('quests'); rp=model_path('relics')
    heroes=core.decode_heroes(hp) if hp and hp.exists() else []
    quests=core.decode_quests(qp) if qp and qp.exists() else []
    relics=core.decode_relics(rp) if rp and rp.exists() else []
    static=core.find_static_data(GAME_ROOT)
    names={}; protos={}
    if static:
        names=core.map_hero_internal_names(heroes,static)
        protos=core.decode_quest_prototypes(static,{q['prototype_id'] for q in quests})
        quests=core.enrich_quests(quests,protos)
    # adapt policy to core schema
    cp={'safety':{'min_heroes_after_send_away':policy.get('safety',{}).get('min_heroes_after_send_away',30)},'relics':{'protected_inventory_ids':[]}}
    strategy=core.build_account_strategy(heroes,quests,relics,cp,mem.get('failures',{}))
    # Concrete execution semantics. Meta/progress quests may influence scoring, but can never become actor commands.
    meta_actions={'QuestUpgradeProgress','QuestComplete','PlayerLogIn','ConnectAccount','EnablePushNotifications','ChangeAccountName','ChangeAccountAvatar','ClientAction'}
    def concrete_command(j):
        action=j.get('action'); target=(j.get('target') or '')
        if action in meta_actions: return None
        if action=='BattleFinish':
            if 'Arena' in target: return 'ARENA_BATTLE'
            if 'Kampagne' in target: return 'CAMPAIGN_BATTLE'
            if 'Clan-Boss' in target: return 'CLAN_BOSS_BATTLE'
            if 'Dungeon' in target or 'Boss' in target: return 'DUNGEON_BATTLE'
            return 'BATTLE_FROM_QUEST_LOS'
        if action in ('HeroSummon','HeroOrAnimaSummon'): return 'SUMMON_WILDSTAR'
        if action=='HeroLevelUp': return 'HERO_LEVEL'
        if action=='HeroAwake': return 'HERO_AWAKE'
        if action=='HeroAscend': return 'HERO_ASCEND'
        if action=='PushCampaignUntilFirstDefeat': return 'CAMPAIGN_PUSH'
        if action=='DevelopMainTeam': return 'MAIN_TEAM_LEVEL'
        return None
    for j in strategy.get('queue',[]):
        cmd=concrete_command(j)
        j['actor_command']=cmd
        j['actor_path']=('QUEST_LOS' if j.get('kind')=='quest_action' and cmd else ('CAMPAIGN_PUSH' if cmd=='CAMPAIGN_PUSH' else ('MAIN_TEAM_LEVEL' if cmd=='MAIN_TEAM_LEVEL' else None)))
        j['execution_ready']=bool(cmd) and not j.get('blocked',False)
        if j.get('action') in ('GearSell','GearDestroy','GearUpgrade','RelicCleanup','ShopPurchase','ResourcesSpent'):
            j['execution_ready']=False; j['blocked']=True; j['block_reason']=j.get('block_reason') or 'inventory/cost actor intentionally locked until value/cost confirmation is validated'
    # The executable queue is what the actor consumes. Abstract/meta jobs remain visible in queue for reasoning only.
    executable_queue=[j for j in strategy.get('queue',[]) if j.get('execution_ready')]
    strategy['executable_queue']=executable_queue
    strategy['next_executable']=executable_queue[0] if executable_queue else None
    strategy['mode']=policy.get('mode','DRY_RUN'); strategy['actor_enabled']=bool(policy.get('actor_enabled',False))
    strategy['generated_at']=time.strftime('%Y-%m-%dT%H:%M:%S'); strategy['game_root']=str(GAME_ROOT)
    strategy['hero_internal_names']=names
    strategy['sources']={k:{'size':v['size'],'sha256':v['sha256']} for k,v in src.items()}
    atomic_json(PLAN_FILE,strategy); return strategy

def main():
    once='--once' in sys.argv
    while True:
        try:
            s=build_plan(); n=s.get('next_executable')
            print(f"[{time.strftime('%H:%M:%S')}] mode={s['mode']} actor={s['actor_enabled']} next={n.get('actor_command') if n else 'NONE'} target={n.get('target') if n else '-'}",flush=True)
        except FileNotFoundError as e:
            print(f'bridge waiting: missing {e.filename}',flush=True)
        except Exception as e:
            print('bridge error:',repr(e),flush=True)
        if once:return
        time.sleep(2)
if __name__=='__main__':main()
