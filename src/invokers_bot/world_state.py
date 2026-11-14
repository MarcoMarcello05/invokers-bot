from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .models import GameState


@dataclass
class WorldState:
    screen: GameState = GameState.UNKNOWN
    confidence: float = 0.0
    observed_at: float = field(default_factory=time.time)
    facts: dict[str, Any] = field(default_factory=dict)

    def age_seconds(self) -> float:
        return max(0.0, time.time() - self.observed_at)

    def fresh(self, max_age: float = 1.0) -> bool:
        return self.age_seconds() <= max_age
