"""Root slot 15 profile independently corroborated by archived schema inventories
and structured_state.read_arena_collections, which decoded both collections.
Result and timestamp slots are not verified.
"""
from dataclasses import dataclass
from hashlib import sha256
from .arena_opponent import ArenaOpponent, parse_opponent

@dataclass(frozen=True,slots=True)
class FinishedOpponent:
    opponent: ArenaOpponent
    entry_digest: str

    @property
    def identity(self):
        return self.opponent.identity


def parse_finished_opponent(raw):
    return FinishedOpponent(parse_opponent(raw),sha256(raw).hexdigest())
