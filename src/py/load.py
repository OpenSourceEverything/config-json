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


def _is_hidden_domain(config_root: Path, domain_dir: Path) -> bool:
    rel = domain_dir.relative_to(config_root)
    return any(part.startswith(".") for part in rel.parts)


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


def _valid_domain_filename(name: str) -> bool:
    candidate = str(name or "").strip()
    if not candidate or not candidate.endswith(".json"):
        return False
    if any(ch in candidate for ch in ("\r", "\n", "\t")):
        return False
    p = Path(candidate)
    return (not p.is_absolute()) and len(p.parts) == 1 and "/" not in candidate and "\\" not in candidate


def _resolve_config_json_path(
    config_root: Path,
    raw_name: str,
    context: str,
) -> tuple[Path | None, str | None]:
    candidate = str(raw_name or "").strip()
    if not candidate or not candidate.endswith(".json"):
        return None, f"{context}: expected a '<profile>.json' path under {config_root}"

    rel = Path(candidate)
    if rel.is_absolute():
        return None, f"{context}: absolute paths are not allowed: {candidate}"
    if any(part in {"", ".", ".."} for part in rel.parts):
        return None, f"{context}: path must stay within {config_root} and cannot contain '.' or '..': {candidate}"

    resolved = (config_root / rel).resolve()
    try:
        resolved.relative_to(config_root.resolve())
    except ValueError:
        return None, f"{context}: path escapes {config_root}: {candidate}"
    return resolved, None


def _read_pointer_value(path: Path, context: str, *, required: bool = True) -> tuple[str | None, str | None]:
    try:
        lines = path.read_text(encoding="utf-8").lstrip("\ufeff").splitlines()
    except OSError as ex:
        return None, f"{context}: cannot read {path}: {ex}"
    value = ""
    selected_line = 0
    for line_number, raw_line in enumerate(lines, start=1):
        text = raw_line.strip()
        if not text or text.startswith("#"):
            continue
        if value:
            return (
                None,
                f"{context}: expected exactly one active value in {path}; found additional entry at line {line_number}",
            )
        value = text
        selected_line = line_number
    if not value:
        if not required:
            return None, None
        return None, f"{context}: expected exactly one active value in {path}"
    return value, None


def _read_filename(path: Path, context: str) -> tuple[str | None, str | None]:
    value, read_error = _read_pointer_value(path, context)
    if read_error:
        return None, read_error
    assert value is not None
    if not _valid_domain_filename(value):
        return None, f"{context}: expected a single '<profile>.json' filename in {path}"
    return value, None


def _read_config_json_path(
    path: Path,
    config_root: Path,
    context: str,
    *,
    required: bool = True,
) -> tuple[Path | None, str | None]:
    value, read_error = _read_pointer_value(path, context, required=required)
    if read_error:
        return None, read_error
    if value is None:
        return None, None
    assert value is not None
    return _resolve_config_json_path(config_root, value, context)


def discover_domain_dirs(config_root: Path) -> list[Path]:
    domain_dirs = {active.parent for active in config_root.rglob("active.txt")}
    domain_dirs = {domain for domain in domain_dirs if domain != config_root}
    domain_dirs = {domain for domain in domain_dirs if not _is_hidden_domain(config_root, domain)}
    return sorted(domain_dirs, key=lambda path: _domain_id(config_root, path))


def _load_root_active_map(
    config_root: Path, domains_by_id: dict[str, Path]
) -> tuple[dict[str, str], bool, Path | None, list[str]]:
    selector_path = config_root / "active.txt"
    if not selector_path.exists():
        return {}, False, None, []

    selector_json, selector_error = _read_config_json_path(
        selector_path,
        config_root,
        "root active selector",
        required=False,
    )
    if selector_error:
        return {}, True, None, [selector_error]
    if selector_json is None:
        return {}, False, None, []
    assert selector_json is not None

    data, json_error = _load_json(selector_json, "root active selector")
    if json_error:
        return {}, True, selector_json, [json_error]
    if not isinstance(data, dict):
        return {}, True, selector_json, [f"root active selector: {selector_json} must be a JSON object"]

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
        if not isinstance(filename, str) or not _valid_domain_filename(filename):
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

    return overrides, True, selector_json, errors


def _load_domain_active_filenames(
    config_root: Path,
    domains_by_id: dict[str, Path],
) -> tuple[dict[str, str], list[str]]:
    filenames: dict[str, str] = {}
    errors: list[str] = []
    for domain_id, domain_dir in domains_by_id.items():
        active_txt = domain_dir / "active.txt"
        active_filename, active_error = _read_filename(
            active_txt,
            f"domain '{domain_id}' active selector",
        )
        if active_error:
            errors.append(active_error)
            continue
        assert active_filename is not None
        filenames[domain_id] = active_filename
    return filenames, errors


def load_active_domain_configs(
    config_root: Path,
    *,
    active_filename_overrides: dict[str, str] | None = None,
) -> tuple[list[DomainConfig], list[str]]:
    errors: list[str] = []
    configs: list[DomainConfig] = []
    override_filenames = dict(active_filename_overrides or {})

    domain_dirs = discover_domain_dirs(config_root)
    domains_by_id = {_domain_id(config_root, domain_dir): domain_dir for domain_dir in domain_dirs}
    root_active_overrides, has_root_active_selector, root_active_map_path, root_active_errors = _load_root_active_map(
        config_root, domains_by_id
    )
    errors.extend(root_active_errors)
    domain_active_filenames, domain_active_errors = _load_domain_active_filenames(
        config_root,
        domains_by_id,
    )
    errors.extend(domain_active_errors)

    normalized_override_filenames: dict[str, str] = {}
    for domain_id, filename in override_filenames.items():
        domain_id_text = str(domain_id or "").strip()
        filename_text = str(filename or "").strip()
        if not domain_id_text:
            errors.append("active filename override: domain id must be non-empty")
            continue
        if domain_id_text not in domains_by_id:
            errors.append(f"active filename override: unknown domain id '{domain_id_text}'")
            continue
        if not _valid_domain_filename(filename_text):
            errors.append(
                f"active filename override: domain '{domain_id_text}' must use a '<profile>.json' filename"
            )
            continue
        normalized_override_filenames[domain_id_text] = filename_text

    selected_domains: list[tuple[str, Path]] = []
    selected_domain_ids: set[str] = set()
    if has_root_active_selector:
        for domain_id, domain_dir in domains_by_id.items():
            if domain_id in normalized_override_filenames or domain_id in root_active_overrides:
                selected_domains.append((domain_id, domain_dir))
                selected_domain_ids.add(domain_id)
        missing_domain_ids = [
            domain_id for domain_id in domains_by_id if domain_id not in selected_domain_ids
        ]
        if missing_domain_ids:
            map_label = str(root_active_map_path or (config_root / "active.txt"))
            missing_text = ", ".join(missing_domain_ids)
            errors.append(
                f"root active selector: {map_label} is missing explicit selections for: {missing_text}"
            )
    else:
        selected_domains = list(domains_by_id.items())
        selected_domain_ids = {domain_id for domain_id, _ in selected_domains}

    for domain_id in normalized_override_filenames:
        if domain_id in selected_domain_ids:
            continue
        selected_domains.append((domain_id, domains_by_id[domain_id]))
        selected_domain_ids.add(domain_id)

    for domain_id, domain_dir in selected_domains:
        domain_id = _domain_id(config_root, domain_dir)
        active_filename = normalized_override_filenames.get(domain_id)
        if active_filename is None:
            active_filename = root_active_overrides.get(domain_id)
        if active_filename is None:
            active_filename = domain_active_filenames.get(domain_id)
        if active_filename is None:
            # Missing/invalid domain active pointer error was already collected above.
            continue

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
            if not isinstance(raw_name, str):
                errors.append(
                    f"active overrides selector: index {index} must be a '<profile>.json' path"
                )
                continue
            override_path, path_error = _resolve_config_json_path(
                config_root,
                raw_name,
                f"active overrides selector: index {index}",
            )
            if path_error:
                errors.append(path_error)
                continue
            assert override_path is not None
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


def map_domain_overrides(
    payload: Any,
    domain_ids: list[str],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if payload is None:
        return {}, []
    if not isinstance(payload, dict):
        return {}, ["overrides: expected root JSON object"]

    domain_parts: dict[tuple[str, ...], str] = {}
    prefixes: set[tuple[str, ...]] = {()}
    for domain_id in domain_ids:
        parts = tuple(part for part in domain_id.split("/") if part)
        if not parts:
            continue
        domain_parts[parts] = domain_id
        current: tuple[str, ...] = ()
        for part in parts:
            current = current + (part,)
            prefixes.add(current)

    errors: list[str] = []
    mapped: dict[str, dict[str, Any]] = {}

    def _walk(node: Any, path: tuple[str, ...]) -> None:
        if path in domain_parts:
            domain_id = domain_parts[path]
            if not isinstance(node, dict):
                pointer = "/" + "/".join(path)
                errors.append(
                    f"overrides: domain '{domain_id}' payload at {pointer} must be a JSON object"
                )
                return
            mapped[domain_id] = node
            return

        if path not in prefixes:
            pointer = "/" + "/".join(path)
            errors.append(f"overrides: unknown domain path '{pointer}'")
            return

        if not isinstance(node, dict):
            pointer = "/" + "/".join(path) if path else "/"
            errors.append(f"overrides: namespace payload at {pointer} must be a JSON object")
            return

        for raw_key, value in node.items():
            key = str(raw_key or "").strip()
            if not key:
                pointer = "/" + "/".join(path) if path else "/"
                errors.append(f"overrides: invalid empty key under {pointer}")
                continue
            _walk(value, path + (key,))

    _walk(payload, ())
    return mapped, errors


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
