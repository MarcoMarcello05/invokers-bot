import argparse, hashlib, json, os, time, struct
from pathlib import Path
from datetime import datetime

DEFAULT_ROOT = Path(os.environ.get('USERPROFILE','~')).expanduser()/r'AppData/LocalLow/Hit_Zone/Invokers'
MODELS = {
 'account':'PlayerModel.dat','quests':'PlayerQuestsModel.dat','events':'PlayerGlobalEventsModel.dat',
 'arena':'PlayerArenaModel.dat','battle':'PlayerBattleModel.dat','heroes':'PlayerHeroesModel.dat',
 'relics':'PlayerRelicsModel.dat','animas':'PlayerAnimasModel.dat','accessories':'PlayerAccessoriesModel.dat',
 'inbox':'PlayerInboxModel.dat','clan':'PlayerClanModel.dat','shop':'PlayerShopModel.dat'
}

def digest(p):
    data=p.read_bytes(); return len(data),hashlib.sha256(data).hexdigest()

def load_policy(path):
    if not path.exists():
        policy={
          'heroes': {'default_team_allowed': True, 'default_level_allowed': False, 'default_send_away_allowed': False,
                     'protected_inventory_ids': [], 'team_inventory_ids': [], 'level_inventory_ids': [], 'send_away_inventory_ids': []},
          'relics': {'default_upgrade_allowed': False, 'default_sell_allowed': False,
                     'protected_inventory_ids': [], 'upgrade_inventory_ids': [], 'sell_inventory_ids': []},
          'resources': {'allow_premium_spend': False, 'allow_gems': False, 'allow_wild_star_summon': True},
          'safety': {'min_heroes_after_send_away': 30, 'actor_enabled': False}
        }
        path.write_text(json.dumps(policy,indent=2),encoding='utf-8')
    return json.loads(path.read_text(encoding='utf-8'))

def decode_heroes(path):
    """Read-only PlayerHero primitive-field decoder.
    The field order is grounded in the dumped PlayerHero model and validated by the 31->32 BEFORE/AFTER test.
    We deliberately do not pretend to decode the whole MemoryPack object yet.
    """
    data=path.read_bytes(); heroes=[]
    for i in range(0,max(0,len(data)-28)):
        try:
            inv=struct.unpack_from('<i',data,i)[0]
            cfg=struct.unpack_from('<q',data,i+4)[0]
            rank=struct.unpack_from('<i',data,i+12)[0]
            level=struct.unpack_from('<i',data,i+16)[0]
            xp=struct.unpack_from('<i',data,i+20)[0]
            total=struct.unpack_from('<i',data,i+24)[0]
        except struct.error: break
        # Conservative signature for the observed PlayerHero primitive block.
        if not (0 < inv < 100000): continue
        if not (10**12 < cfg < 10**17): continue
        if not (0 <= rank <= 10 and 1 <= level <= 100): continue
        if not (0 <= xp < 10_000_000 and xp <= total < 100_000_000): continue
        heroes.append({'inventory_id':inv,'config_id':cfg,'config_id_hex':f'0x{cfg:016X}',
                       'rank':rank,'level':level,'experience':xp,'total_experience':total,
                       'record_offset':i})
    # Inventory IDs are unique in the model. If the signature ever yields duplicates, keep that visible as a warning.
    return heroes


QUEST_ACTIONS={
0:'Unknown',2:'HeroSummon',3:'HeroLevelUp',4:'HeroAscend',5:'HeroAwake',6:'HeroSkillLevelUp',7:'HeroStatsChanged',
22:'AnimaSummon',23:'AnimaLevelUp',24:'AnimaEmpower',25:'AnimaSkillLevelUp',41:'RelicCollect',42:'RelicActivate',43:'RelicUpgrade',
45:'RelicGetMemoriumFromDestroy',46:'RelicGetGoldFromSell',47:'RelicActivateOrUpgrade',48:'RelicSell',49:'RelicDestroy',
51:'AccessoryCollect',52:'AccessoryActivate',53:'AccessoryUpgrade',55:'AccessoryGetMemoriumFromDestroy',56:'AccessoryGetGoldFromSell',
57:'AccessoryActivateOrUpgrade',58:'AccessorySell',59:'AccessoryDestroy',61:'BattleFinish',71:'GearUpgrade',72:'GearSell',73:'GearDestroy',
81:'QuestComplete',82:'QuestUpgradeProgress',101:'ResourcesSpent',121:'ShopPurchase',141:'PlayerLogIn',142:'ConnectAccount',
144:'EnablePushNotifications',145:'ChangeAccountName',146:'ChangeAccountAvatar',147:'ActivateBooster',161:'FormationUpgrade',
181:'HeroOrAnimaSummon',182:'HeroOrAnimaSkillLevelUp',191:'ArenaHallUpgrade',192:'ArenaPointsChange',201:'ClientAction'}
ACTION_DE={
'HeroSummon':'Invoker beschwören','HeroLevelUp':'Invoker leveln','HeroAscend':'Invoker aufsteigen lassen','HeroAwake':'Invoker erwecken',
'HeroSkillLevelUp':'Invoker-Fähigkeit verbessern','AnimaSummon':'Anima beschwören','AnimaLevelUp':'Anima leveln','AnimaEmpower':'Anima verstärken',
'RelicCollect':'Relikt erhalten','RelicActivate':'Relikt aktivieren','RelicUpgrade':'Relikt verbessern','RelicActivateOrUpgrade':'Relikt aktivieren/verbessern',
'RelicSell':'Relikt verkaufen','RelicDestroy':'Relikt zerstören','AccessoryCollect':'Accessoire erhalten','AccessoryUpgrade':'Accessoire verbessern',
'AccessorySell':'Accessoire verkaufen','BattleFinish':'Kampf abschließen','GearUpgrade':'Ausrüstung verbessern','GearSell':'Ausrüstung verkaufen',
'GearDestroy':'Ausrüstung zerstören','QuestComplete':'Quest abschließen','QuestUpgradeProgress':'Questgruppen-Fortschritt erhöhen',
'ResourcesSpent':'Ressourcen ausgeben','ShopPurchase':'Shop-Kauf durchführen','PlayerLogIn':'Einloggen','FormationUpgrade':'Formation verbessern',
'HeroOrAnimaSummon':'Invoker oder Anima beschwören','HeroOrAnimaSkillLevelUp':'Invoker-/Anima-Fähigkeit verbessern','ArenaHallUpgrade':'Arena-Halle verbessern',
'ArenaPointsChange':'Arena-Punkte verändern','ClientAction':'Client-Aktion ausführen','Unknown':'Unbekannte Aktion'}


AREA_NAMES={0:'Unknown',1:'Campaign',2:'Dungeon',3:'Tower',4:'AsyncPvp',5:'FactionWars',6:'ClanBoss',7:'Events',8:'InfinityDungeon'}
AREA_DE={1:'Kampagne',2:'Dungeon/Boss',3:'Turm',4:'Arena',5:'Fraktionskriege',6:'Clan-Boss',7:'Event',8:'Endlos-Dungeon'}
DIFFICULTY_NAMES={0:'Unknown',1:'Normal',2:'Hard',3:'Brutal',9:'None'}
REGION_NAMES={-1:'Prologue',0:'Unknown',1:'Chapter1_ELD',2:'Chapter2_MON',3:'Chapter3_CAV',4:'Chapter4_ICE',5:'Chapter5_VOL',6:'Chapter6_BRD',7:'Chapter7_TRO',8:'Chapter8_GRV',9:'Chapter9_GMO',10:'Chapter10_DES',11:'Chapter11_DEM',12:'Chapter12_CEL',21:'DungeonRelics1',22:'DungeonEssenceNeutral',23:'DungeonTitan',24:'DungeonMelee',25:'DungeonSupport',26:'DungeonTank',27:'DungeonRanged',28:'DungeonRelics2',29:'DungeonRelics3',30:'DungeonRelics4',31:'DungeonRelics5',32:'DungeonRelics6',33:'DungeonEssenceFire',34:'DungeonEssenceEarth',35:'DungeonEssenceWind',36:'DungeonEssenceWater',37:'DungeonEssenceLight',38:'DungeonEssenceDark',71:'TowerFire',72:'TowerEarth',73:'TowerWind',74:'TowerWater',75:'TowerLight',76:'TowerDark',101:'AsyncPvp1',301:'ClanBoss1',302:'ClanBoss2Neutral',303:'ClanBoss2Fire',304:'ClanBoss2Earth',305:'ClanBoss2Wind',306:'ClanBoss2Water',307:'ClanBoss2Light',308:'ClanBoss2Dark',501:'InfinityDungeon'}

def _nullable_i32(data,pos):
    # MemoryPack serializes Nullable<int/enum> as the native 8-byte nullable layout.
    # Padding bytes are not semantic; only byte 0 (HasValue) and int32 at +4 are used.
    if pos+8>len(data): raise ValueError('nullable out of range')
    return struct.unpack_from('<i',data,pos+4)[0] if data[pos] else None

def _nullable_bool(data,pos):
    if pos+2>len(data): raise ValueError('nullable bool out of range')
    return bool(data[pos+1]) if data[pos] else None

def _read_i32_list(data,pos):
    if pos+4>len(data): raise ValueError('list out of range')
    n=struct.unpack_from('<i',data,pos)[0]; pos+=4
    if n<0: return [],pos
    if n>1000 or pos+4*n>len(data): raise ValueError('bad list count')
    vals=list(struct.unpack_from('<'+'i'*n,data,pos)) if n else []
    return vals,pos+4*n

def decode_battle_condition(main, proto_offset):
    # QuestPrototypeBase prefix is 12 bytes, Conditions list count is next int32.
    try:
        count=struct.unpack_from('<i',main,proto_offset+12)[0]
        if count < 1: return None
        pos=proto_offset+16
        # IQuestCondition union tag 5 = Battle, then MemoryPack object member-count 12.
        if main[pos] != 5 or main[pos+1] != 12: return None
        pos += 2
        area=_nullable_i32(main,pos); pos+=8
        region=_nullable_i32(main,pos); pos+=8
        difficulty=_nullable_i32(main,pos); pos+=8
        number=_nullable_i32(main,pos); pos+=8
        region_ids,pos=_read_i32_list(main,pos)
        auto_battle=_nullable_bool(main,pos); pos+=2
        animas_count=_nullable_i32(main,pos); pos+=8
        min_number=_nullable_i32(main,pos); pos+=8
        numbers,pos=_read_i32_list(main,pos)
        allow_defeat=_nullable_bool(main,pos); pos+=2
        collect_stars=_nullable_bool(main,pos); pos+=2
        clan_boss_damage_difficulty_id=_nullable_i32(main,pos); pos+=8
        d={'type':'Battle','area_id':area,'area':AREA_NAMES.get(area,str(area)) if area is not None else None,
           'region_id':region,'region':REGION_NAMES.get(region,str(region)) if region is not None else None,
           'difficulty_id':difficulty,'difficulty':DIFFICULTY_NAMES.get(difficulty,str(difficulty)) if difficulty is not None else None,
           'number':number,'region_ids':region_ids,'regions':[REGION_NAMES.get(x,str(x)) for x in region_ids],
           'auto_battle':auto_battle,'animas_count':animas_count,'min_number':min_number,'numbers':numbers,
           'allow_defeat':allow_defeat,'collect_stars':collect_stars,
           'clan_boss_damage_difficulty_id':clan_boss_damage_difficulty_id}
        parts=[]
        if area is not None: parts.append(AREA_DE.get(area,d['area']))
        if region is not None: parts.append(d['region'])
        if region_ids: parts.append('/'.join(d['regions']))
        if difficulty is not None: parts.append(d['difficulty'])
        if number is not None: parts.append(f'Level {number}')
        if numbers: parts.append('Level '+','.join(map(str,numbers)))
        d['target_de']=' | '.join(parts) if parts else 'Kampfbedingung'
        d['navigation_area']=d['area']
        return d
    except (ValueError,struct.error,IndexError):
        return None

def decode_quest_prototypes(static_path, wanted_ids=None):
    """Decode the stable QuestPrototypeBase prefix from StaticQuestData.
    Dump-grounded fields: Id, QuestAction, RequiredAmount. Conditions are intentionally not guessed yet.
    """
    main=extract_static_main_chunk(static_path) if static_path else None
    if not main: return {}
    wanted=set(wanted_ids or [])
    result={}
    # In current pack IQuestPrototype union tag + object header precede the base prefix as 01 0A.
    for i in range(2,len(main)-12):
        if main[i-2:i] != b'\x01\x0a': continue
        pid,action,required=struct.unpack_from('<iii',main,i)
        if wanted and pid not in wanted: continue
        if not (1000 <= pid < 1_000_000 and action in QUEST_ACTIONS and 0 <= required < 10_000_000): continue
        # Prefer the static quest region occurrence; duplicate integer patterns elsewhere usually fail the prefix signature.
        if pid not in result:
            name=QUEST_ACTIONS[action]
            result[pid]={'prototype_id':pid,'action_id':action,'action':name,'required_amount':required,
                         'objective_de':ACTION_DE.get(name,name),'static_offset':i,
                         'conditions_decoded':False}
            if action==61:
                cond=decode_battle_condition(main,i)
                if cond:
                    result[pid]['conditions']=[cond]; result[pid]['conditions_decoded']=True; result[pid]['target_de']=cond['target_de']
    return result

def enrich_quests(quests, prototypes):
    out=[]
    for q in quests:
        x=dict(q); meta=prototypes.get(q['prototype_id'])
        if meta:
            x.update({'action_id':meta['action_id'],'action':meta['action'],'required_amount':meta['required_amount'],
                      'objective_de':meta['objective_de'],'conditions_decoded':meta.get('conditions_decoded',False),
                      'conditions':meta.get('conditions',[]),'target_de':meta.get('target_de')})
            req=meta['required_amount']
            x['progress_text']=f'{q["progress"]}/{req}' if req>0 else str(q['progress'])
            x['remaining']=max(0,req-q['progress']) if req>0 else None
        else:
            x.update({'action_id':None,'action':None,'required_amount':None,'objective_de':None,'conditions_decoded':False,
                      'progress_text':str(q['progress']),'remaining':None})
        out.append(x)
    return out

QUEST_STATES={0:'Unknown',1:'New',2:'InProgress',3:'Completed'}
QUEST_GROUPS={1:'Daily',2:'Weekly',3:'Monthly',4:'Advance',5:'Clan'}

def decode_quests(path):
    """Read-only QuestState decoder validated against dumped QuestStateBase/Periodic field layout."""
    data=path.read_bytes(); out=[]
    # Observed serialized periodic state: marker 0x04, QuestId, PrototypeId, StateId, DateTime, Progress, Group.
    for i in range(0,max(0,len(data)-30)):
        if data[i] != 4: continue
        try:
            qid,proto,state=struct.unpack_from('<iii',data,i+1)
            ticks=struct.unpack_from('<Q',data,i+13)[0]
            progress=struct.unpack_from('<i',data,i+21)[0]
            extra=struct.unpack_from('<i',data,i+25)[0]
        except struct.error: continue
        clean_ticks=ticks & ((1<<62)-1)
        if not (0 < qid < 100000 and 1000 <= proto < 1000000 and state in QUEST_STATES): continue
        if not (600_000_000_000_000_000 < clean_ticks < 700_000_000_000_000_000): continue
        if not (0 <= progress < 10_000_000): continue
        group=QUEST_GROUPS.get(extra) if 10000 <= proto < 19000 else None
        # Periodic prototype ranges are strongly identified by the dumped StaticQuestData parent IDs.
        if 10000 <= proto < 19000 and group:
            kind='Periodic'
        elif 20000 <= proto < 1000000:
            kind='Other/Book/Achievement'
        else:
            kind='Unknown'
        out.append({'quest_id':qid,'prototype_id':proto,'state_id':state,'state':QUEST_STATES[state],
                    'progress':progress,'extra':extra,'group':group,'kind':kind,'record_offset':i})
    # qid is unique; preserve file order.
    seen=set(); clean=[]
    for q in out:
        if q['quest_id'] in seen: continue
        seen.add(q['quest_id']); clean.append(q)
    return clean

def _read_mp_string_at(data,pos):
    # CharacterConfig Name in this pack is encoded by MemoryPack's UTF-8 string representation.
    if pos+8>len(data): return None
    marker=struct.unpack_from('<i',data,pos)[0]
    n=struct.unpack_from('<i',data,pos+4)[0]
    if marker >= 0 or not (1 <= n <= 80) or pos+8+n>len(data): return None
    raw=data[pos+8:pos+8+n]
    try: txt=raw.decode('utf-8')
    except UnicodeDecodeError: return None
    return txt if txt.isprintable() else None

def extract_static_main_chunk(path):
    """Extract HZCP main chunk. Format is grounded in dumped ChunkPackHeader/PackChunk structs."""
    import brotli
    b=path.read_bytes()
    if b[:4] != b'HZCP': return None
    pos=8
    try:
        for _ in range(2):
            n=b[pos]; pos+=1+n
        header_size,header_raw_size=struct.unpack_from('<II',b,pos); pos+=8
        header=brotli.decompress(b[pos:pos+header_size]); data_start=pos+header_size
        count=struct.unpack_from('<i',header,1)[0]
        if not (1 <= count <= 100000): return None
        chunks_pos=1+4+16*count+4
        # Main key is first in current pack; verify first key category is Main(0), id 0.
        first_id=struct.unpack_from('<q',header,5)[0]; first_cat=header[13]
        if first_id!=0 or first_cat!=0: return None
        off,size,usize=struct.unpack_from('<iii',header,chunks_pos); compressed=bool(header[chunks_pos+12])
        raw=b[data_start+off:data_start+off+size]
        return brotli.decompress(raw) if compressed else raw
    except Exception:
        return None

def find_static_data(root):
    candidates=[]
    sd=root/'static_data'
    if sd.exists(): candidates += list(sd.glob('static-data*.dat')) + list(sd.glob('*.dat'))
    # Optional nearby launcher installs are deliberately not scanned; keep reader scoped to game LocalLow data.
    return max(candidates,key=lambda x:x.stat().st_mtime) if candidates else None

def map_hero_internal_names(heroes,static_path):
    if not static_path: return {}
    main=extract_static_main_chunk(static_path)
    if not main: return {}
    names={}
    for h in heroes:
        pat=struct.pack('<q',h['config_id']); start=0
        while True:
            i=main.find(pat,start)
            if i<0: break
            # BaseCharacterConfig: ID, GDID, Name. Name payload begins at ID+16.
            name=_read_mp_string_at(main,i+16)
            if name and 3 <= len(name) <= 40:
                names[h['inventory_id']]=name; break
            start=i+1
    return names

RELIC_SLOTS={1:'Weapon',2:'Shield',3:'Helmet',4:'Pauldrons',5:'Gauntlets',6:'Chestplate',7:'Belt',8:'Boots'}
RELIC_RARITY={1:'Common',2:'Uncommon',3:'Rare',4:'Epic',5:'Legendary',6:'Greater'}
RELIC_SETS={1:'CrushTolerance',2:'ManaShockTolerance',3:'FrostTolerance',4:'DazeTolerance',5:'ParalysisTolerance',6:'NightmareTolerance',7:'MindFogTolerance',8:'FatigueTolerance',9:'BlightTolerance',10:'ManaBurnTolerance',11:'AtrophyTolerance',12:'BloodRotTolerance',101:'Attack',102:'Defense',103:'Health',104:'CriticalRate',105:'CriticalDamage',106:'Accuracy',107:'Resistance',108:'Instinct',109:'ManaGeneration',110:'SkillSpeed',111:'SkillRecovery',112:'LifeSteal',113:'IgnoreDefense',114:'Support',115:'ReduceBuffDuration',116:'EventSet1',117:'EventSet2',118:'ClanBossSet1',119:'ClanBossSet2'}

def decode_relics(path):
    if not path.exists(): return []
    b=path.read_bytes(); out=[]; seen=set()
    # PlayerRelic primitive prefix is stable in the VersionTolerant payload:
    # InventoryId, Slot, Rank, Rarity, Set, Nullable<int> EquippedHeroId, Level, IsSeen.
    for i in range(0,max(0,len(b)-36)):
        try: inv,slot,rank,rar,setv=struct.unpack_from('<5i',b,i)
        except struct.error: break
        if not (0 < inv < 1000000 and 1 <= slot <= 8 and 1 <= rank <= 6 and 1 <= rar <= 6 and setv in RELIC_SETS): continue
        # suppress accidental overlapping matches and duplicate ids
        if inv in seen: continue
        has_eq=struct.unpack_from('<i',b,i+20)[0]
        if has_eq not in (0,1): continue
        eq=struct.unpack_from('<i',b,i+24)[0] if has_eq else None
        level=struct.unpack_from('<i',b,i+28)[0]
        if not (0 <= level <= 30): continue
        if eq is not None and not (0 < eq < 1000000): continue
        seen.add(inv)
        out.append({'inventory_id':inv,'slot_id':slot,'slot':RELIC_SLOTS[slot],'rank':rank,
                    'rarity_id':rar,'rarity':RELIC_RARITY[rar],'set_id':setv,'set':RELIC_SETS[setv],
                    'equipped_hero_id':eq,'level':level,'record_offset':i})
    return sorted(out,key=lambda x:x['inventory_id'])

def relic_summary(relics):
    by_rarity={}; equipped=0
    for r in relics:
        by_rarity[r['rarity']]=by_rarity.get(r['rarity'],0)+1
        equipped += r['equipped_hero_id'] is not None
    return {'count':len(relics),'equipped':equipped,'unequipped':len(relics)-equipped,'by_rarity':by_rarity}

def planner_preview(*args, **kwargs):
    raise RuntimeError('Legacy quest-only scoring retired; use Planner.plan with the complete GameState')


def print_relics(relics):
    s=relic_summary(relics)
    print(f'=== RELIC READER: {s["count"]} records | equipped {s["equipped"]} | unequipped {s["unequipped"]} ===')
    print(' Rarity:', ', '.join(f'{k}={v}' for k,v in sorted(s['by_rarity'].items())))
    print(' Safety: equipped relics are PROTECTED; no selling/upgrading is executed in read-only core.\n')

def print_planner(plan):
    print('=== PLANNER PREVIEW (NO CLICKS) ===')
    for i,x in enumerate(plan.get('top_actions',[])[:5],1):
        tgt=(' -> '+x['target']) if x.get('target') else ''
        qs=', '.join(f'{q.get("group") or "Other"}#{q["prototype_id"]}' for q in x['quests'])
        print(f' {i}. score={x["score"]:4} {x["action"]}{tgt} | helps: {qs}')
    print()


RESOURCE_TYPES={1:'Gem',2:'Gold',3:'Energy',4:'Memorium',11:'MultiBattleToken',12:'ClanBoss2Key',21:'ArenaToken',22:'ArenaCoin',23:'ArenaMedalBronze',24:'ArenaMedalSilver',25:'ArenaMedalGold',34:'AccountXp',35:'HeroXp',51:'XpPotionSmall',52:'XpPotionRegular',53:'XpPotionBig',54:'XpPotionPremium',101:'WildStar',102:'FateStar',103:'DestinyStar',104:'DivineStar',105:'RadiantStar',106:'DreamOrb',107:'WonderOrb',108:'MiracleOrb',111:'LegendaryStar',112:'MythicOrb'}

def resource_capabilities():
    # IDs are grounded in ResourceTypeId from the game dump. Balances remain unknown until the MemoryPack dictionary is validated.
    return {'schema_known':True,'balances_decoded':False,'types':RESOURCE_TYPES,
            'hard_blocks':['Gem','premium purchases'],'explicit_auto_allow':['WildStar'],
            'note':'Resource IDs are known; balances are intentionally not guessed.'}

def build_account_strategy(*args, **kwargs):
    raise RuntimeError('Legacy list-based planner retired; use Planner.plan(GameState, UserConfig, FailureMemory, now)')


def print_strategy(strategy):
    print('=== AUTONOMOUS PLANNER V1 (READ-ONLY) ===')
    mt=', '.join(f"ID{x['inventory_id']} Lv{x['level']}" for x in strategy.get('main_team',[]))
    print(' Main six:',mt)
    n=strategy.get('next_action')
    if n: print(f" NEXT: {n['action']} -> {n.get('target')} | score={n.get('score')}")
    for i,j in enumerate(strategy.get('queue',[])[:8],1):
        flag='BLOCKED' if j.get('blocked') else 'READY'
        print(f" {i}. [{flag}] {j['action']} -> {j.get('target')} score={j.get('score')}")
        if j.get('block_reason'): print('    ',j['block_reason'])
    print(' Safety: Gems/Premium BLOCKED | WildStar allowed | campaign stops on first defeat | equipped relics protected\n')

def quest_diff(old,new):
    a={x['quest_id']:x for x in old}; b={x['quest_id']:x for x in new}; out=[]
    for qid in sorted(b.keys()-a.keys()):
        q=b[qid]; out.append(f'Quest + #{qid} proto {q["prototype_id"]} {q.get("group") or q["kind"]}: {q["state"]} progress={q["progress"]}')
    for qid in sorted(a.keys()-b.keys()): out.append(f'Quest - #{qid} removed/closed')
    for qid in sorted(a.keys()&b.keys()):
        x,y=a[qid],b[qid]; changes=[]
        if x['state_id']!=y['state_id']: changes.append(f'State {x["state"]}->{y["state"]}')
        if x['progress']!=y['progress']: changes.append(f'Progress {x["progress"]}->{y["progress"]}')
        if changes: out.append(f'Quest #{qid} proto {y["prototype_id"]}: '+', '.join(changes))
    return out

def print_quests(quests):
    print(f'=== QUEST READER: {len(quests)} decoded states ===')
    print(' QID   Proto   Group       State       Progress   Objective')
    for q in quests:
        label=q.get('group') or q['kind']
        obj=q.get('objective_de') or '?'
        prog=q.get('progress_text',str(q['progress']))
        
        if q.get('target_de'):
            suffix=' -> '+q['target_de']
        elif q.get('action') in ('BattleFinish','ResourcesSpent','ShopPurchase','ClientAction'):
            suffix=' [Bedingungen offen]'
        else:
            suffix='' 
        print(f'{q["quest_id"]:4}  {q["prototype_id"]:6}  {label:10}  {q["state"]:10} {prog:>9}   {obj}{suffix}')
    print('NOTE: Action + RequiredAmount kommen aus StaticQuestData. Spezifische Conditions (z.B. welcher Kampf) werden noch nicht geraten.\n')

def hero_diff(old,new):
    a={x['inventory_id']:x for x in old}; b={x['inventory_id']:x for x in new}; out=[]
    for hid in sorted(b.keys()-a.keys()): out.append(f'Hero + ID {hid}: Lv {b[hid]["level"]}, Rank {b[hid]["rank"]}')
    for hid in sorted(a.keys()-b.keys()): out.append(f'Hero - ID {hid} removed')
    for hid in sorted(a.keys()&b.keys()):
        x,y=a[hid],b[hid]; changes=[]
        for key,label in [('level','Level'),('experience','XP'),('total_experience','TotalXP'),('rank','Rank')]:
            if x[key]!=y[key]: changes.append(f'{label} {x[key]}->{y[key]}')
        if changes: out.append(f'Hero ID {hid}: '+', '.join(changes))
    return out

def snapshot(root):
    d=root/'aggregate_snapshots'; out={}
    for key,name in MODELS.items():
        p=d/name
        if p.exists():
            size,sha=digest(p); st=p.stat(); out[key]={'file':name,'size':size,'sha256':sha,'mtime':st.st_mtime}
    pending=root/'actions'/'pending_deterministic_actions.dat'
    if pending.exists():
        size,sha=digest(pending); out['pending_actions']={'file':str(pending),'size':size,'sha256':sha,'mtime':pending.stat().st_mtime}
    return out

def print_heroes(heroes,names=None):
    names=names or {}
    print(f'\n=== HERO READER: {len(heroes)} records ===')
    print(' ID     Lv  Rk       XP    TotalXP   InternalName  ConfigId')
    for h in heroes:
        nm=names.get(h['inventory_id'],'?')
        print(f'{h["inventory_id"]:4}  {h["level"]:5} {h["rank"]:3} {h["experience"]:8} {h["total_experience"]:10}   {nm:12} {h["config_id_hex"]}')
    print('NOTE: InternalName is the static config code, not yet the localized German display name.\n')

def main():
    # Legacy CLI remains available; all decisions now belong to Planner/GameState.
    from runtime import main as runtime_main
    return runtime_main()

if __name__=='__main__':
    raise SystemExit(main())
