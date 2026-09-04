from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .load import DomainConfig, load_active_domain_configs, load_overrides, map_domain_overrides
from .merge import deep_merge


@dataclass(frozen=True)
class ResolvedDomain:
    domain_id: str
    domain_dir: Path
    active_filename: str
    file_path: Path
    base_data: Any
    override_data: dict[str, Any] | None
    effective_data: Any


@dataclass(frozen=True)
class ResolveConfigTreeResult:
    root: Path
    config_root: Path
    domains: list[ResolvedDomain]
    overrides_payload: Any
    domain_overrides: dict[str, dict[str, Any]]
    effective_config: Any
    wrapped_effective_config: Any
    errors: list[str]


def _as_override_filename_map(value: Mapping[str, str] | None) -> dict[str, str]:
    if value is None:
        return {}
    result: dict[str, str] = {}
    for key, item in value.items():
        result[str(key)] = str(item)
    return result


def _wrap_domain_payload(domain_id: str, payload: Any) -> Any:
    parts = [part for part in str(domain_id or "").split("/") if part]
    if not parts:
        return payload
    wrapped: Any = payload
    for part in reversed(parts):
        wrapped = {part: wrapped}
    return wrapped


def build_wrapped_effective_config(domain_payloads: list[tuple[str, Any]]) -> Any:
    wrapped_effective: Any = {}
    for domain_id, payload in domain_payloads:
        wrapped_effective = deep_merge(wrapped_effective, _wrap_domain_payload(domain_id, payload))
    return wrapped_effective


def resolve_config_tree(
    root: Path,
    *,
    domain_active_filenames: Mapping[str, str] | None = None,
) -> ResolveConfigTreeResult:
    root_path = Path(root).resolve()
    config_root = root_path / "config"
    if not config_root.is_dir():
        return ResolveConfigTreeResult(
            root=root_path,
            config_root=config_root,
            domains=[],
            overrides_payload={},
            domain_overrides={},
            effective_config={},
            wrapped_effective_config={},
            errors=[f"missing config root: {config_root}"],
        )

    domain_configs, domain_errors = load_active_domain_configs(
        config_root,
        active_filename_overrides=_as_override_filename_map(domain_active_filenames),
    )

    overrides_payload, override_errors = load_overrides(config_root)
    domain_ids = [cfg.domain_id for cfg in domain_configs]
    domain_overrides, domain_override_errors = map_domain_overrides(overrides_payload, domain_ids)

    resolved_domains: list[ResolvedDomain] = []
    effective: Any = {}
    wrapped_effective: Any = {}
    wrapped_domain_payloads: list[tuple[str, Any]] = []
    for cfg in domain_configs:
        base_payload = cfg.data
        override_payload = domain_overrides.get(cfg.domain_id)
        domain_effective = deep_merge(base_payload, override_payload) if override_payload is not None else base_payload
        resolved_domains.append(
            ResolvedDomain(
                domain_id=cfg.domain_id,
                domain_dir=cfg.domain_dir,
                active_filename=cfg.active_filename,
                file_path=cfg.file_path,
                base_data=base_payload,
                override_data=override_payload,
                effective_data=domain_effective,
            )
        )
        effective = deep_merge(effective, domain_effective)
        wrapped_domain_payloads.append((cfg.domain_id, domain_effective))

    wrapped_effective = build_wrapped_effective_config(wrapped_domain_payloads)

    return ResolveConfigTreeResult(
        root=root_path,
        config_root=config_root,
        domains=resolved_domains,
        overrides_payload=overrides_payload,
        domain_overrides=domain_overrides,
        effective_config=effective,
        wrapped_effective_config=wrapped_effective,
        errors=[str(item) for item in [*domain_errors, *override_errors, *domain_override_errors]],
    )
