from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .merge import deep_merge


@dataclass(frozen=True)
class DomainConfig:
    domain_id: str
    domain_dir: Path
    active_filename: str
    file_path: Path
    data: Any


def _domain_id(config_root: Path, domain_dir: Path) -> str:
    rel = domain_dir.relative_to(config_root).as_posix()
    return "" if rel == "." else rel


def _json_error(path: Path, ex: json.JSONDecodeError, prefix: str) -> str:
    return (
        f"{prefix}: invalid JSON in {path} "
        f"(line {ex.lineno}, col {ex.colno}): {ex.msg}"
    )


def _load_json(path: Path, prefix: str) -> tuple[Any | None, str | None]:
    try:
        text = path.read_text(encoding="utf-8")
        return json.loads(text.lstrip("\ufeff")), None
    except FileNotFoundError:
        return None, f"{prefix}: missing file {path}"
    except json.JSONDecodeError as ex:
        return None, _json_error(path, ex, prefix)


def _valid_active_filename(name: str) -> bool:
    if not name or not name.endswith(".json"):
        return False
    p = Path(name)
    return (not p.is_absolute()) and len(p.parts) == 1 and "/" not in name and "\\" not in name


def _read_filename(path: Path, context: str) -> tuple[str | None, str | None]:
    try:
        value = path.read_text(encoding="utf-8").lstrip("\ufeff").strip()
    except OSError as ex:
        return None, f"{context}: cannot read {path}: {ex}"
    if not _valid_active_filename(value):
        return None, f"{context}: expected a single '<profile>.json' filename in {path}"
    return value, None


def discover_domain_dirs(config_root: Path) -> list[Path]:
    domain_dirs = {active.parent for active in config_root.rglob("active.txt")}
    domain_dirs = {domain for domain in domain_dirs if domain != config_root}
    return sorted(domain_dirs, key=lambda path: _domain_id(config_root, path))


def _load_root_active_map(
    config_root: Path, domains_by_id: dict[str, Path]
) -> tuple[dict[str, str], list[str]]:
    selector_path = config_root / "active.txt"
    if not selector_path.exists():
        return {}, []

    selector_name, selector_error = _read_filename(selector_path, "root active selector")
    if selector_error:
        return {}, [selector_error]
    assert selector_name is not None

    selector_json = config_root / selector_name
    data, json_error = _load_json(selector_json, "root active selector")
    if json_error:
        return {}, [json_error]
    if not isinstance(data, dict):
        return {}, [f"root active selector: {selector_json} must be a JSON object"]

    overrides: dict[str, str] = {}
    errors: list[str] = []
    for domain_id, filename in data.items():
        if not isinstance(domain_id, str) or not domain_id:
            errors.append(
                "root active selector: map keys must be non-empty domain-id strings"
            )
            continue
        if domain_id not in domains_by_id:
            errors.append(
                f"root active selector: unknown domain id '{domain_id}' in {selector_json}"
            )
            continue
        if not isinstance(filename, str) or not _valid_active_filename(filename):
            errors.append(
                f"root active selector: domain '{domain_id}' must map to a '<profile>.json' filename"
            )
            continue
        payload = domains_by_id[domain_id] / filename
        if not payload.exists():
            errors.append(
                f"root active selector: domain '{domain_id}' references missing file {payload}"
            )
            continue
        overrides[domain_id] = filename

    return overrides, errors


def load_active_domain_configs(config_root: Path) -> tuple[list[DomainConfig], list[str]]:
    errors: list[str] = []
    configs: list[DomainConfig] = []

    domain_dirs = discover_domain_dirs(config_root)
    domains_by_id = {_domain_id(config_root, domain_dir): domain_dir for domain_dir in domain_dirs}
    root_active_overrides, root_active_errors = _load_root_active_map(config_root, domains_by_id)
    errors.extend(root_active_errors)

    for domain_id, domain_dir in domains_by_id.items():
        domain_id = _domain_id(config_root, domain_dir)
        active_filename = root_active_overrides.get(domain_id)
        if active_filename is None:
            active_txt = domain_dir / "active.txt"
            active_filename, active_error = _read_filename(
                active_txt, f"domain '{domain_id}' active selector"
            )
            if active_error:
                errors.append(active_error)
                continue
            assert active_filename is not None

        payload = domain_dir / active_filename
        data, error = _load_json(payload, f"domain '{domain_id}'")
        if error:
            errors.append(error)
            continue

        configs.append(
            DomainConfig(
                domain_id=domain_id,
                domain_dir=domain_dir,
                active_filename=active_filename,
                file_path=payload,
                data=data,
            )
        )

    return configs, errors


def load_overrides(config_root: Path) -> tuple[Any, list[str]]:
    selector_path = config_root / "active-overrides.txt"
    if selector_path.exists():
        data, selector_error = _load_json(selector_path, "active overrides selector")
        if selector_error:
            return {}, [selector_error]
        if not isinstance(data, list):
            return {}, [f"active overrides selector: {selector_path} must be a JSON array of filenames"]

        errors: list[str] = []
        merged: Any = {}
        for index, raw_name in enumerate(data):
            if not isinstance(raw_name, str) or not _valid_active_filename(raw_name):
                errors.append(
                    f"active overrides selector: index {index} must be a '<profile>.json' filename"
                )
                continue
            override_path = config_root / raw_name
            payload, payload_error = _load_json(override_path, f"override '{raw_name}'")
            if payload_error:
                errors.append(payload_error)
                continue
            merged = deep_merge(merged, payload)
        return merged, errors

    overrides_path = config_root / "overrides.json"
    if not overrides_path.exists():
        return {}, []

    data, error = _load_json(overrides_path, "overrides")
    if error:
        return {}, [error]
    return data, []


def load_schema(config_root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    schema_path = config_root / "config.schema.json"
    if not schema_path.exists():
        return None, [f"schema: missing file {schema_path}"]

    data, error = _load_json(schema_path, "schema")
    if error:
        return None, [error]
    if not isinstance(data, dict):
        return None, [f"schema: {schema_path} must be a JSON object"]
    return data, []
