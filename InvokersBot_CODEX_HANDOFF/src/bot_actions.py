"""Concrete planner-to-execution contract; no readers, OCR or policy imports."""
from dataclasses import asdict, dataclass, field
import json
from typing import Any


@dataclass(frozen=True)
class Action:
    action_id: str
    kind: str
    module: str
    target: dict[str, Any] = field(default_factory=dict)
    resource_costs: dict[str, int] | None = None
    preconditions: dict[str, Any] = field(default_factory=dict)
    expected_effects: dict[str, Any] = field(default_factory=dict)
    reasons: tuple[str, ...] = ()
    score: int = 0

    @property
    def key(self):
        identity = self.target
        if self.kind == 'ARENA_BATTLE':
            # Strength, points and list position can change after refresh. Those
            # changes must not erase a failure against the same account.
            player_id = self.target.get('player_id_bytes') or self.target.get('player_id')
            identity = {'player_id': player_id} if player_id is not None else {'name': self.target.get('name')}
        return self.kind + '|' + json.dumps(identity, sort_keys=True, separators=(',', ':'))

    def to_dict(self):
        return asdict(self)


def section_value(state, name):
    """Unknown observations stay None, including serialized GameState input."""
    section = state.get(name) if isinstance(state, dict) else getattr(state, name, None)
    if isinstance(section, dict) and 'status' in section:
        return section.get('value') if section.get('status') == 'available' else None
    if hasattr(section, 'status'):
        return section.value if section.status == 'available' else None
    return None


def resource_values(state):
    resources = section_value(state, 'resources') or {}
    return resources.get('current', {}).get('values', {})


def hero_values(state):
    heroes = section_value(state, 'heroes')
    # A structured roster may additionally describe UI-order confidence.
    return heroes.get('heroes', heroes.get('items', [])) if isinstance(heroes, dict) else heroes
