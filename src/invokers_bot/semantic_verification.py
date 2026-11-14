"""Reusable semantic resource predicates against parsed account observations."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResourcePredicate:
    source: str
    resource_id: int
    kind: str
    delta: int | None = None

    def value(self, account):
        item = account.sources.get(self.source) if account else None
        if item is None or item.error or item.model is None or item.awaiting_change:
            return None
        value = getattr(item.model, "resources", {}).get(self.resource_id)
        return value if type(value) is int else None

    def matches(self, baseline, current):
        item = current.sources.get(self.source) if current else None
        if item is None or not item.fresh(2.0):
            return False
        before, after = self.value(baseline), self.value(current)
        if before is None or after is None:
            return False
        difference = after - before
        return difference < 0 if self.kind == "resource_decreased" else difference == self.delta


def _resource(spec):
    source = spec.get("source", "player")
    resource_id = spec.get("resource_id")
    kind = spec["kind"]
    delta = spec.get("delta")
    if source != "player" or type(resource_id) is not int:
        raise ValueError("resource predicate requires player and numeric resource_id")
    if kind == "resource_delta" and (type(delta) is not int or delta == 0):
        raise ValueError("resource_delta requires a nonzero integer delta")
    if kind == "resource_decreased" and delta is not None:
        raise ValueError("resource_decreased does not take delta")
    return ResourcePredicate(source, resource_id, kind, delta)


_REGISTRY = {"resource_decreased": _resource, "resource_delta": _resource}


def parse_predicates(specs):
    if not isinstance(specs, (list, tuple)):
        raise ValueError("semantic_predicates must be a sequence")
    result = []
    for spec in specs:
        if not isinstance(spec, dict) or spec.get("kind") not in _REGISTRY:
            raise ValueError("unknown semantic predicate")
        result.append(_REGISTRY[spec["kind"]](spec))
    return tuple(result)
