from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable


def deep_merge(base: Any, override: Any) -> Any:
    """Deep-merge JSON-like values.

    object + object -> recurse
    otherwise -> override replaces base
    """
    if isinstance(base, dict) and isinstance(override, dict):
        merged: dict[str, Any] = {k: deepcopy(v) for k, v in base.items()}
        for key, value in override.items():
            if key in merged:
                merged[key] = deep_merge(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged
    return deepcopy(override)


def merge_all(values: Iterable[Any]) -> Any:
    result: Any = {}
    for value in values:
        result = deep_merge(result, value)
    return result
