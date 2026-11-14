from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any


class GoalStatus(str, Enum):
    AVAILABLE = "available"
    BLOCKED = "blocked"
    ACTIVE = "active"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass(frozen=True)
class Goal:
    name: str
    priority: float
    expected_value: float = 1.0
    resource_cost: float = 0.0
    risk: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def utility(self) -> float:
        return self.priority + self.expected_value - self.resource_cost - self.risk


GoalFactory = Callable[[dict[str, Any]], list[Goal]]
