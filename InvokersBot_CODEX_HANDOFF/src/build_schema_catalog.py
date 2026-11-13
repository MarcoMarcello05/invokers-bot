import re,json
from pathlib import Path
ROOT=Path('/mnt/data/workdeep/dump/InvokersDump/DiffableCs/Shared.Choreograph.Models')
classes=['Resources','PlayerModel','PlayerBattleModel','LevelStats','TeamPresetData','TeamPresetSlot','MetaBattleSetup','BattlePlayerTeamSetup','PlayerGlobalEventsModel','TournamentParticipationState','LevelProgressionIdentifier']
out={}
for cls in classes:
 fs=list(ROOT.rglob(cls+'.cs'))
 if not fs: continue
 t=fs[0].read_text(errors='ignore')
 layout='VersionTolerant' if 'GenerateType::VersionTolerant' in t else ('Sequential' if 'SerializeLayout::Sequential' in t else 'unknown')
 fields=[]
 for typ,name in re.findall(r'private(?: readonly)?\s+([^\n;]+?)\s+<([^>]+)>k__BackingField;',t): fields.append({'name':name,'type':typ.strip()})
 if cls=='LevelProgressionIdentifier':
  fields=[{'name':n,'type':ty} for ty,n in re.findall(r'public readonly\s+([\w<>`,]+)\s+(\w+);',t)]
 out[cls]={'layout':layout,'fields':fields,'source':str(fs[0].relative_to(ROOT))}
Path('/mnt/data/workdeep/schema_catalog.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps({k:{'layout':v['layout'],'field_count':len(v['fields'])} for k,v in out.items()},indent=2))
