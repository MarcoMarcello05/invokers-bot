"""Read-only availability summary over the existing GameState contract."""
import argparse
import json
from pathlib import Path
from game_state import build_game_state

SECTIONS = ('resources','campaign','arena','events','heroes','quests','relics',
            'hero_internal_names','quest_prototypes','hero_roster','main_team','bosses','quest_log')


def capabilities(state):
    result={}
    for name in SECTIONS:
        item=getattr(state,name)
        result[name]={'status':item.status,'method':item.method,
                      'sources':list(item.sources),'reason':item.reason,
                      'authorizes_input':False}
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    args=p.parse_args()
    print(json.dumps(capabilities(build_game_state(args.root)),indent=2))


if __name__=='__main__':
    main()
