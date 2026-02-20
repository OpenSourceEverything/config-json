from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .init import copy_template
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

    return parser


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
        )

    parser.print_help()
    return 2
