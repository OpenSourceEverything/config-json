from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from config_json.load import load_active_domain_configs


class LoadActiveDomainConfigsTests(unittest.TestCase):
    def test_root_selector_requires_explicit_selection_for_all_domains(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_root = root / "config"
            app_dir = config_root / "app"
            db_dir = config_root / "db"
            gui_dir = config_root / "gui"
            profiles_dir = config_root / ".profiles"
            for folder in [app_dir, db_dir, gui_dir, profiles_dir]:
                folder.mkdir(parents=True, exist_ok=True)

            (app_dir / "active.txt").write_text("app.local.json\n", encoding="utf-8")
            (db_dir / "active.txt").write_text("db.json\n", encoding="utf-8")
            (gui_dir / "active.txt").write_text("gui.json\n", encoding="utf-8")
            (app_dir / "app.local.json").write_text(json.dumps({"a": 0}), encoding="utf-8")
            (app_dir / "app.json").write_text(json.dumps({"a": 1}), encoding="utf-8")
            (db_dir / "db.json").write_text(json.dumps({"b": 2}), encoding="utf-8")
            (gui_dir / "gui.json").write_text(json.dumps({"c": 3}), encoding="utf-8")

            (profiles_dir / "active.live.json").write_text(
                json.dumps({"app": "app.json", "db": "db.json"}),
                encoding="utf-8",
            )
            (config_root / "active.txt").write_text(".profiles/active.live.json\n", encoding="utf-8")

            configs, errors = load_active_domain_configs(config_root)
            self.assertEqual([cfg.domain_id for cfg in configs], ["app", "db"])
            cfg_by_id = {cfg.domain_id: cfg for cfg in configs}
            self.assertEqual(cfg_by_id["app"].active_filename, "app.json")
            self.assertEqual(cfg_by_id["db"].active_filename, "db.json")
            self.assertTrue(
                any("missing explicit selections for: gui" in error for error in errors),
                msg=f"expected strict root selector error, got: {errors}",
            )

    def test_without_root_selector_loads_all_domains(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_root = root / "config"
            app_dir = config_root / "app"
            db_dir = config_root / "db"
            for folder in [app_dir, db_dir]:
                folder.mkdir(parents=True, exist_ok=True)

            (app_dir / "active.txt").write_text("app.json\n", encoding="utf-8")
            (db_dir / "active.txt").write_text("db.json\n", encoding="utf-8")
            (app_dir / "app.json").write_text(json.dumps({"a": 1}), encoding="utf-8")
            (db_dir / "db.json").write_text(json.dumps({"b": 2}), encoding="utf-8")

            configs, errors = load_active_domain_configs(config_root)
            self.assertEqual(errors, [])
            self.assertEqual([cfg.domain_id for cfg in configs], ["app", "db"])

    def test_active_filename_overrides_apply_without_editing_active_txt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_root = root / "config"
            plc_dir = config_root / "simulators" / "plc"
            plc_dir.mkdir(parents=True, exist_ok=True)

            (plc_dir / "active.txt").write_text("default.json\n", encoding="utf-8")
            (plc_dir / "default.json").write_text(json.dumps({"mode": "default"}), encoding="utf-8")
            (plc_dir / "local.json").write_text(json.dumps({"mode": "local"}), encoding="utf-8")

            configs, errors = load_active_domain_configs(
                config_root,
                active_filename_overrides={"simulators/plc": "local.json"},
            )
            self.assertEqual(errors, [])
            self.assertEqual(len(configs), 1)
            self.assertEqual(configs[0].active_filename, "local.json")

    def test_active_selector_allows_comments_and_blank_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_root = root / "config"
            app_dir = config_root / "app"
            app_dir.mkdir(parents=True, exist_ok=True)

            (app_dir / "active.txt").write_text(
                "# app selector\n\napp.local.json\n",
                encoding="utf-8",
            )
            (app_dir / "app.local.json").write_text(json.dumps({"app": {"mode": "local"}}), encoding="utf-8")

            configs, errors = load_active_domain_configs(config_root)
            self.assertEqual(errors, [])
            self.assertEqual(len(configs), 1)
            self.assertEqual(configs[0].active_filename, "app.local.json")

    def test_active_selector_rejects_multiple_non_comment_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_root = root / "config"
            app_dir = config_root / "app"
            app_dir.mkdir(parents=True, exist_ok=True)

            (app_dir / "active.txt").write_text("app.local.json\napp.prod.json\n", encoding="utf-8")
            (app_dir / "app.local.json").write_text(json.dumps({"app": {"mode": "local"}}), encoding="utf-8")
            (app_dir / "app.prod.json").write_text(json.dumps({"app": {"mode": "prod"}}), encoding="utf-8")

            configs, errors = load_active_domain_configs(config_root)
            self.assertEqual(configs, [])
            self.assertTrue(
                any("expected exactly one active value" in error for error in errors),
                msg=f"expected single-value pointer error, got: {errors}",
            )

    def test_root_selector_allows_comments_and_blank_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_root = root / "config"
            app_dir = config_root / "app"
            profiles_dir = config_root / ".profiles"
            app_dir.mkdir(parents=True, exist_ok=True)
            profiles_dir.mkdir(parents=True, exist_ok=True)

            (app_dir / "active.txt").write_text("app.local.json\n", encoding="utf-8")
            (app_dir / "app.local.json").write_text(json.dumps({"app": {"mode": "local"}}), encoding="utf-8")
            (app_dir / "app.prod.json").write_text(json.dumps({"app": {"mode": "prod"}}), encoding="utf-8")
            (profiles_dir / "active.prod.json").write_text(
                json.dumps({"app": "app.prod.json"}),
                encoding="utf-8",
            )
            (config_root / "active.txt").write_text(
                "# profile selector\n\n.profiles/active.prod.json\n",
                encoding="utf-8",
            )

            configs, errors = load_active_domain_configs(config_root)
            self.assertEqual(errors, [])
            self.assertEqual(len(configs), 1)
            self.assertEqual(configs[0].active_filename, "app.prod.json")

    def test_domain_active_selector_is_validated_even_when_root_selector_maps_domain(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_root = root / "config"
            app_dir = config_root / "app"
            profiles_dir = config_root / ".profiles"
            app_dir.mkdir(parents=True, exist_ok=True)
            profiles_dir.mkdir(parents=True, exist_ok=True)

            # Invalid domain pointer form (path) should still be reported by loader validation.
            (app_dir / "active.txt").write_text("config/app/app.prod.json\n", encoding="utf-8")
            (app_dir / "app.prod.json").write_text(json.dumps({"app": {"mode": "prod"}}), encoding="utf-8")
            (profiles_dir / "active.prod.json").write_text(
                json.dumps({"app": "app.prod.json"}),
                encoding="utf-8",
            )
            (config_root / "active.txt").write_text(".profiles/active.prod.json\n", encoding="utf-8")

            configs, errors = load_active_domain_configs(config_root)
            self.assertEqual([cfg.domain_id for cfg in configs], ["app"])
            self.assertEqual(configs[0].active_filename, "app.prod.json")
            self.assertTrue(
                any("expected a single '<profile>.json' filename" in error for error in errors),
                msg=f"expected domain active selector format error, got: {errors}",
            )

    def test_empty_root_selector_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_root = root / "config"
            app_dir = config_root / "app"
            db_dir = config_root / "db"
            app_dir.mkdir(parents=True, exist_ok=True)
            db_dir.mkdir(parents=True, exist_ok=True)

            (app_dir / "active.txt").write_text("app.local.json\n", encoding="utf-8")
            (db_dir / "active.txt").write_text("db.local.json\n", encoding="utf-8")
            (app_dir / "app.local.json").write_text(json.dumps({"app": {"mode": "local"}}), encoding="utf-8")
            (db_dir / "db.local.json").write_text(json.dumps({"db": {"mode": "local"}}), encoding="utf-8")
            (config_root / "active.txt").write_text("# intentionally empty\n\n", encoding="utf-8")

            configs, errors = load_active_domain_configs(config_root)
            self.assertEqual(errors, [])
            self.assertEqual([cfg.domain_id for cfg in configs], ["app", "db"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
