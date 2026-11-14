import argparse
from .config import load_config
from .engine import BotEngine

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",default="config/arena.json")
    p.add_argument("--mode",choices=["dry","live"],default="dry")
    p.add_argument("--snapshot-dir", help="Read-only directory containing aggregate .dat files")
    args=p.parse_args()
    config = load_config(args.config)
    directory = args.snapshot_dir or config.raw.get("runtime", {}).get("snapshot_dir")
    BotEngine(config, live=args.mode=="live", snapshot_dir=directory).run()

if __name__=="__main__": main()
