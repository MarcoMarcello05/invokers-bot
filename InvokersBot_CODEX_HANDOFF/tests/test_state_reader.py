from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from state_reader import read_player_resources, read_level_stats, campaign_summary

class StateReaderTests(unittest.TestCase):
    def test_resources(self):
        r=read_player_resources(ROOT/'tests/fixtures/PlayerModel.dat')
        c,g,s=(r[k]['values'] for k in ('current','gained','spent'))
        for name in ['Gold','Energy','Memorium','Arena_Token','SI_WildStar']:
            self.assertEqual(g[name]-s[name],c[name],name)
        self.assertEqual(g['Gem'],c['Gem']); self.assertEqual(s.get('Gem',0),0)
        self.assertEqual((c['Gem'],c['Gold']),(310,631640))

    def test_campaign(self):
        rows=read_level_stats(ROOT/'tests/fixtures/PlayerBattleModel.dat')
        self.assertEqual(len(rows),78)
        c=campaign_summary(rows)['Normal']
        self.assertEqual((c['highest_won']['region'],c['highest_won']['number']),(7,5))
        self.assertEqual((c['first_failed']['region'],c['first_failed']['number'],c['first_failed']['defeats']),(7,6,2))

if __name__=='__main__': unittest.main()
