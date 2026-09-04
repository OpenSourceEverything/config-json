from __future__ import annotations

import shutil
from pathlib import Path


def copy_template(template: str, dest: Path, force: bool = False) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    source_config = repo_root / "templates" / template / "config"
    if not source_config.exists():
        raise FileNotFoundError(f"template not found: {source_config}")

    target_config = dest / "config"
    if target_config.exists():
        if not force:
            raise FileExistsError(
                f"refusing to overwrite existing {target_config}; rerun with --force"
            )
        shutil.rmtree(target_config)

    target_config.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_config, target_config)
    return target_config
