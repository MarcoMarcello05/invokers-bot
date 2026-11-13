from pathlib import Path
from state_reader import read_player_resources, read_level_stats, campaign_summary
ROOT=Path('/mnt/data/workdeep/live/Invokers_LiveData'); DUMP=Path('/mnt/data/workdeep/dump')
r=read_player_resources(ROOT/'PlayerModel.dat',DUMP)
c=r['current']['values']; g=r['gained']['values']; s=r['spent']['values']
for name in ['Gold','Energy','Memorium','Arena_Token','SI_WildStar']:
    assert g[name]-s[name]==c[name], (name,g[name],s[name],c[name])
assert g['Gem']==c['Gem'] and s.get('Gem',0)==0
levels=read_level_stats(ROOT/'PlayerBattleModel.dat'); camp=campaign_summary(levels)
assert camp['Normal']['highest_won']['region']==7 and camp['Normal']['highest_won']['number']==5
assert camp['Normal']['first_failed']['region']==7 and camp['Normal']['first_failed']['number']==6
assert camp['Normal']['first_failed']['defeats']==2
print('PASS resources accounting + campaign state; level rows=',len(levels))
