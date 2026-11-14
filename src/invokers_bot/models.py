from dataclasses import dataclass
from enum import Enum

class GameState(str, Enum):
    MAIN="main"; ARENA_LIST="arena_list"; FORMATION="formation"; BATTLE="battle"
    VICTORY="victory"; DEFEAT="defeat"; POPUP="popup"; UNKNOWN="unknown"

@dataclass(frozen=True)
class Rect:
    left:int; top:int; width:int; height:int
    @property
    def right(self): return self.left+self.width
    @property
    def bottom(self): return self.top+self.height

@dataclass(frozen=True)
class Match:
    state:GameState; score:float; x:int; y:int; width:int; height:int; template:str
    @property
    def center(self): return self.x+self.width//2, self.y+self.height//2

@dataclass(frozen=True)
class TargetMatch:
    score:float; x:int; y:int; width:int; height:int; template:str
    @property
    def center(self): return self.x+self.width//2, self.y+self.height//2
