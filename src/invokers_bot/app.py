import argparse
from .config import load_config
from .engine import BotEngine

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",default="config/arena.json")
    p.add_argument("--mode",choices=["dry","live"],default="dry")
    args=p.parse_args()
    BotEngine(load_config(args.config),live=args.mode=="live").run()

if __name__=="__main__": main()
