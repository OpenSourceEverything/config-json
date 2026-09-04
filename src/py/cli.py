from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .init import copy_template
from .resolve import resolve_config_tree
from .validate import run_validate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="config-json")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Copy template config into destination")
    init_parser.add_argument("--template", default="base", help="Template name under templates/")
    init_parser.add_argument("--dest", default=".", help="Destination root folder")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing <dest>/config")

    validate_parser = subparsers.add_parser("validate", help="Merge and validate config tree")
    validate_parser.add_argument("--root", default=".", help="Project root containing config/")
    validate_parser.add_argument(
        "--no-validate-per-file",
        action="store_true",
        help="Disable per-file overlay validation pass",
    )
    validate_parser.add_argument(
        "--write-wrapped-effective",
        dest="write_wrapped_effective",
        action="store_true",
        help="Write config/config.wrapped.json using domain folder IDs as object namespaces (default: enabled).",
    )
    validate_parser.add_argument(
        "--no-write-wrapped-effective",
        dest="write_wrapped_effective",
        action="store_false",
        help="Disable writing config/config.wrapped.json.",
    )
    validate_parser.set_defaults(write_wrapped_effective=True)

    resolve_parser = subparsers.add_parser("resolve", help="Show resolved active files and effective config")
    resolve_parser.add_argument("--root", default=".", help="Project root containing config/")
    resolve_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    resolve_parser.add_argument(
        "--include-effective",
        action="store_true",
        help="Include merged effective config in output",
    )
    resolve_parser.add_argument(
        "--wrap-domains",
        dest="wrap_domains",
        action="store_true",
        help="When including effective config, emit the domain-wrapped shape (default: enabled).",
    )
    resolve_parser.add_argument(
        "--no-wrap-domains",
        dest="wrap_domains",
        action="store_false",
        help="When including effective config, emit the legacy flat merged shape.",
    )
    resolve_parser.set_defaults(wrap_domains=True)

    return parser


def _as_relative_text(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def _print_resolve_text(root: Path, *, include_effective: bool, wrap_domains: bool) -> int:
    result = resolve_config_tree(root)
    for domain in result.domains:
        rel = _as_relative_text(result.root, domain.file_path)
        print(f"{domain.domain_id} -> {domain.active_filename} ({rel})")
    if include_effective:
        effective_payload = result.wrapped_effective_config if wrap_domains else result.effective_config
        print(json.dumps(effective_payload, indent=2, sort_keys=True))
    for err in result.errors:
        print(f"ERROR: {err}")
    return 1 if result.errors else 0


def _print_resolve_json(root: Path, *, include_effective: bool, wrap_domains: bool) -> int:
    result = resolve_config_tree(root)
    payload: dict[str, object] = {
        "root": str(result.root),
        "configRoot": str(result.config_root),
        "errors": list(result.errors),
        "domains": [
            {
                "domainId": domain.domain_id,
                "activeFilename": domain.active_filename,
                "filePath": _as_relative_text(result.root, domain.file_path),
                "overrideApplied": domain.override_data is not None,
            }
            for domain in result.domains
        ],
    }
    if include_effective:
        payload["effectiveConfig"] = result.wrapped_effective_config if wrap_domains else result.effective_config
        payload["effectiveShape"] = "wrapped" if wrap_domains else "flat"
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if result.errors else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        dest = Path(args.dest).resolve()
        try:
            copied = copy_template(args.template, dest=dest, force=args.force)
        except (FileNotFoundError, FileExistsError) as ex:
            print(f"ERROR: {ex}")
            return 1
        print(f"Initialized config at {copied}")
        return 0

    if args.command == "validate":
        return run_validate(
            Path(args.root).resolve(),
            validate_per_file=not args.no_validate_per_file,
            write_wrapped_effective=bool(args.write_wrapped_effective),
        )

    if args.command == "resolve":
        root = Path(args.root).resolve()
        if args.format == "json":
            return _print_resolve_json(
                root,
                include_effective=bool(args.include_effective),
                wrap_domains=bool(args.wrap_domains),
            )
        return _print_resolve_text(
            root,
            include_effective=bool(args.include_effective),
            wrap_domains=bool(args.wrap_domains),
        )

    parser.print_help()
    return 2
