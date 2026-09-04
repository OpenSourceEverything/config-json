from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Iterable

from .load import (
    discover_domain_dirs,
    load_active_domain_configs,
    load_overrides,
    load_schema,
    map_domain_overrides,
)
from .merge import deep_merge
from .resolve import build_wrapped_effective_config


def _json_pointer(path_parts: Iterable[Any]) -> str:
    items = list(path_parts)
    if not items:
        return "/"
    escaped = [str(p).replace("~", "~0").replace("/", "~1") for p in items]
    return "/" + "/".join(escaped)


def _write_effective(root: Path, effective: Any, *, filename: str = "config.json") -> Path:
    out = root / "config" / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(effective, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def _overlay_schema(schema: Any) -> Any:
    if isinstance(schema, dict):
        reduced: dict[str, Any] = {}
        for key, value in schema.items():
            if key == "required":
                continue
            reduced[key] = _overlay_schema(value)
        return reduced
    if isinstance(schema, list):
        return [_overlay_schema(item) for item in schema]
    return deepcopy(schema)


def _domain_label(config_root: Path, domain_dir: Path) -> str:
    rel = domain_dir.relative_to(config_root).as_posix()
    return rel if rel != "." else "<root>"


def _load_json(path: Path, context: str) -> tuple[Any | None, str | None]:
    try:
        text = path.read_text(encoding="utf-8")
        return json.loads(text.lstrip("\ufeff")), None
    except json.JSONDecodeError as ex:
        return None, (
            f"{context}: invalid JSON in {path} "
            f"(line {ex.lineno}, col {ex.colno}): {ex.msg}"
        )
    except OSError as ex:
        return None, f"{context}: cannot read {path}: {ex}"


def _validate_per_file(config_root: Path, overlay_validator: Any) -> list[str]:
    errors: list[str] = []
    for domain_dir in discover_domain_dirs(config_root):
        domain = _domain_label(config_root, domain_dir)
        for json_file in sorted(domain_dir.glob("*.json"), key=lambda p: p.name):
            context = f"domain '{domain}' file '{json_file.name}'"
            data, load_error = _load_json(json_file, context)
            if load_error:
                errors.append(load_error)
                continue
            assert data is not None
            file_errors = sorted(
                overlay_validator.iter_errors(data),
                key=lambda e: (list(e.path), e.message),
            )
            for err in file_errors:
                pointer = _json_pointer(err.path)
                errors.append(f"{context}: schema validation failed at {pointer}: {err.message}")
    return errors


_OBJECT_MARKER = {"__kind__": "object"}


def _flatten_paths(value: Any, path: tuple[str, ...], out: dict[tuple[str, ...], Any]) -> None:
    if isinstance(value, dict):
        out[path] = _OBJECT_MARKER
        for raw_key, child in value.items():
            key = str(raw_key)
            _flatten_paths(child, path + (key,), out)
        return
    out[path] = deepcopy(value)


def _detect_domain_collisions(domain_payloads: list[tuple[str, Any]]) -> list[str]:
    collisions: list[str] = []
    seen_value_by_path: dict[tuple[str, ...], Any] = {}
    seen_domain_by_path: dict[tuple[str, ...], str] = {}

    for domain_id, payload in domain_payloads:
        flattened: dict[tuple[str, ...], Any] = {}
        _flatten_paths(payload, (), flattened)
        for path, value in flattened.items():
            prior_value = seen_value_by_path.get(path)
            prior_domain = seen_domain_by_path.get(path)
            if prior_domain is None:
                seen_value_by_path[path] = value
                seen_domain_by_path[path] = domain_id
                continue
            if prior_value != value and prior_domain != domain_id:
                pointer = _json_pointer(path)
                collisions.append(
                    f"domain collision at {pointer}: '{domain_id}' conflicts with '{prior_domain}'"
                )
    return collisions


def run_validate(
    root: Path,
    validate_per_file: bool = True,
    *,
    write_wrapped_effective: bool = True,
) -> int:
    try:
        import jsonschema
    except ImportError:
        print("ERROR: missing dependency 'jsonschema' (install package dependencies)")
        return 1

    config_root = root / "config"
    if not config_root.is_dir():
        print(f"ERROR: missing config root: {config_root}")
        return 1

    errors: list[str] = []
    domain_configs, domain_errors = load_active_domain_configs(config_root)
    errors.extend(domain_errors)

    overrides, override_errors = load_overrides(config_root)
    errors.extend(override_errors)

    domain_overrides, domain_override_errors = map_domain_overrides(
        overrides,
        [cfg.domain_id for cfg in domain_configs],
    )
    errors.extend(domain_override_errors)

    domain_payloads: list[tuple[str, Any]] = []
    for cfg in domain_configs:
        payload = cfg.data
        override_payload = domain_overrides.get(cfg.domain_id)
        if override_payload is not None:
            payload = deep_merge(payload, override_payload)
        domain_payloads.append((cfg.domain_id, payload))

    errors.extend(_detect_domain_collisions(domain_payloads))

    base: Any = {}
    for _, payload in domain_payloads:
        base = deep_merge(base, payload)

    effective = base
    effective_path = _write_effective(root, effective)
    wrapped_effective_path: Path | None = None
    if write_wrapped_effective:
        wrapped_effective = build_wrapped_effective_config(domain_payloads)
        wrapped_effective_path = _write_effective(root, wrapped_effective, filename="config.wrapped.json")

    schema, schema_errors = load_schema(config_root)
    errors.extend(schema_errors)

    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        print(f"Wrote best-effort effective config: {effective_path}")
        if wrapped_effective_path is not None:
            print(f"Wrote wrapped effective config: {wrapped_effective_path}")
        return 1

    assert schema is not None
    try:
        validator_cls = jsonschema.validators.validator_for(schema)
        validator_cls.check_schema(schema)
        validator = validator_cls(schema)
        overlay_validator = validator_cls(_overlay_schema(schema))
    except jsonschema.exceptions.SchemaError as ex:
        print(f"ERROR: invalid schema in {config_root / 'config.schema.json'}: {ex.message}")
        print(f"Wrote best-effort effective config: {effective_path}")
        if wrapped_effective_path is not None:
            print(f"Wrote wrapped effective config: {wrapped_effective_path}")
        return 1

    if validate_per_file:
        errors.extend(_validate_per_file(config_root, overlay_validator))

    validation_errors = sorted(
        validator.iter_errors(effective),
        key=lambda e: (list(e.path), e.message),
    )
    for err in validation_errors:
        pointer = _json_pointer(err.path)
        errors.append(f"effective config: schema validation failed at {pointer}: {err.message}")

    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        print(f"Wrote effective config: {effective_path}")
        if wrapped_effective_path is not None:
            print(f"Wrote wrapped effective config: {wrapped_effective_path}")
        return 1

    print(f"OK: valid config ({config_root})")
    print(f"Wrote effective config: {effective_path}")
    if wrapped_effective_path is not None:
        print(f"Wrote wrapped effective config: {wrapped_effective_path}")
    return 0
