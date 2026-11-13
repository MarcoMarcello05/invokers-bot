"""Reproducible source build from committed files; excludes private game/runtime data."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PREFIX='InvokersBot_CODEX_HANDOFF/'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    git_root=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=ROOT,text=True).strip())
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    files=subprocess.check_output(['git','ls-tree','-r','--name-only','HEAD'],cwd=git_root,text=True).splitlines()
    selected=[]
    templates={'auto_off.png','victory.png','home_fight.png','arena_token.png'}
    extras={'README.md','requirements-arena.txt','docs/ARENA_SPRINT_01.md','research/MASTER_STATUS.md',
            'tests/test_arena_autopilot.py','tests/fixture_support.py','tools/build_arena_source.py'}
    for name in files:
        if not name.startswith(PREFIX):continue
        relative=name[len(PREFIX):];path=Path(relative)
        if relative in extras or (path.parent==Path('src') and path.suffix in ('.py','.cmd')) or relative=='src/autonomy_policy.json' or relative=='src/knowledge/game_knowledge.json' or relative=='src/schemas/ResourceTypeId.cs' or (path.parent==Path('src/templates') and path.name in templates):
            selected.append((name,relative))
    # Read from HEAD objects, never from local untracked/private files.
    manifest={'commit':commit,'type':'source','live_tested':False,
              'privacy':'No account snapshots, configs, manifests, screenshots or credentials bundled',
              'files':{},'simulation':'python src/arena_runner.py --simulate --cycles 2',
              'tests':'python -m unittest discover -s tests -p test_arena_autopilot.py -v'}
    required={'src/arena_runner.py','src/arena_autopilot.py','src/arena_windows.py',
              'src/schemas/ResourceTypeId.cs','src/templates/arena_token.png','requirements-arena.txt'}
    if not required <= {relative for _,relative in selected}:
        raise RuntimeError('Commit the complete sprint source before producing a build')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for full,relative in selected:
            data=subprocess.check_output(['git','show',commit+':'+full],cwd=git_root)
            info=zipfile.ZipInfo('InvokersBot_Arena_Sprint01/'+relative,date_time=(2026,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,data)
            manifest['files'][relative]=hashlib.sha256(data).hexdigest()
        info=zipfile.ZipInfo('InvokersBot_Arena_Sprint01/BUILD_MANIFEST.json',date_time=(2026,1,1,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED
        archive.writestr(info,json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'artifact':str(args.output),'commit':commit,'files':len(selected),
                      'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest()}))


if __name__=='__main__':main()
