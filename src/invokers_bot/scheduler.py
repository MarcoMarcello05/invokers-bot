from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any

from .goals import Goal


@dataclass
class ScheduledTask:
    goal: Goal
    skill: str
    params: dict[str, Any]


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, fn: Callable[..., Any]) -> None:
        if name in self._skills:
            raise ValueError(f"Skill already registered: {name}")
        self._skills[name] = fn

    def get(self, name: str) -> Callable[..., Any]:
        try:
            return self._skills[name]
        except KeyError as exc:
            raise KeyError(f"Unknown skill: {name}") from exc


class TaskScheduler:
    def choose_goal(self, goals: list[Goal]) -> Goal | None:
        eligible = [g for g in goals if g.utility > 0]
        if not eligible:
            return None
        return max(eligible, key=lambda g: (g.utility, g.priority, g.expected_value))

    def plan(self, goal: Goal) -> ScheduledTask:
        skill = str(goal.metadata.get("skill", "wait"))
        params = dict(goal.metadata.get("params", {}))
        return ScheduledTask(goal=goal, skill=skill, params=params)
