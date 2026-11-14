import json
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class BotConfig:
    raw:dict
    path:Path
    @property
    def window_title_contains(self): return str(self.raw["window"]["title_contains"])
    @property
    def fps(self): return float(self.raw.get("runtime",{}).get("fps",4))
    @property
    def stable_frames(self): return int(self.raw.get("runtime",{}).get("stable_frames",2))
    @property
    def post_action_delay(self): return float(self.raw.get("runtime",{}).get("post_action_delay",0.8))
    @property
    def unknown_dump_after(self): return int(self.raw.get("runtime",{}).get("unknown_dump_after",8))
    @property
    def states(self): return self.raw.get("states",{})
    @property
    def flows(self): return self.raw.get("flows",{})
    @property
    def allow_purchase_actions(self): return bool(self.raw.get("safety",{}).get("allow_purchase_actions",False))

def load_config(path):
    p=Path(path).resolve()
    data=json.loads(p.read_text(encoding="utf-8"))
    missing=[k for k in ("window","states","flows") if k not in data]
    if missing: raise ValueError("Missing config keys: "+", ".join(missing))
    return BotConfig(data,p)

def resolve_asset(config,value):
    p=Path(value)
    return p if p.is_absolute() else (config.path.parent.parent/p).resolve()
