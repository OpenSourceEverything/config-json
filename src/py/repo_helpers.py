from __future__ import annotations

from pathlib import Path
from typing import Any

from .load import load_active_domain_configs, load_overrides, map_domain_overrides
from .merge import deep_merge as _deep_merge
from .resolve import ResolveConfigTreeResult, resolve_config_tree as _resolve_config_tree


def deep_merge(base: Any, overlay: Any) -> Any:
    return _deep_merge(base, overlay)


def get_nested_object(payload: dict[str, Any], path_parts: list[str]) -> dict[str, Any] | None:
    node: Any = payload
    for segment in path_parts:
        if not isinstance(node, dict):
            return None
        node = node.get(segment)
    if not isinstance(node, dict):
        return None
    return node


def apply_domain_overrides(
    base_payload: dict[str, Any],
    overrides_payload: dict[str, Any],
    path_parts: list[str],
) -> dict[str, Any]:
    domain_overrides = get_nested_object(overrides_payload, path_parts)
    if not isinstance(domain_overrides, dict):
        return base_payload
    merged = deep_merge(base_payload, domain_overrides)
    if not isinstance(merged, dict):
        return base_payload
    return merged


def load_repo_overrides(config_root: Path) -> tuple[dict[str, Any], list[str]]:
    payload, load_errors = load_overrides(config_root)
    errors = [str(err) for err in load_errors]

    domain_configs, domain_errors = load_active_domain_configs(config_root)
    errors.extend([str(err) for err in domain_errors])

    mapped, mapping_errors = map_domain_overrides(payload, [cfg.domain_id for cfg in domain_configs])
    errors.extend([str(err) for err in mapping_errors])
    if errors:
        return {}, errors

    nested_payload: dict[str, Any] = {}
    for domain_id, domain_payload in mapped.items():
        node = nested_payload
        parts = [part for part in str(domain_id).split("/") if part]
        for part in parts[:-1]:
            child = node.get(part)
            if not isinstance(child, dict):
                child = {}
                node[part] = child
            node = child
        if parts:
            node[parts[-1]] = domain_payload
    return nested_payload, []


def validate_repo_overrides_payload(config_root: Path, payload: dict[str, Any]) -> list[str]:
    domain_configs, domain_errors = load_active_domain_configs(config_root)
    mapped, mapping_errors = map_domain_overrides(payload, [cfg.domain_id for cfg in domain_configs])
    _ = mapped
    return [str(err) for err in [*domain_errors, *mapping_errors]]


def resolve_repo_config_tree(
    root: Path,
    *,
    active_filename_overrides: dict[str, str] | None = None,
) -> ResolveConfigTreeResult:
    return _resolve_config_tree(root, domain_active_filenames=active_filename_overrides)
