from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from config_json.resolve import resolve_config_tree


class ResolveConfigTreeTests(unittest.TestCase):
    def test_resolve_reports_active_domain_files_and_effective_merge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_root = root / "config"
            app_dir = config_root / "app"
            plc_dir = config_root / "simulators" / "plc"
            profiles_dir = config_root / ".profiles"
            for folder in [app_dir, plc_dir, profiles_dir]:
                folder.mkdir(parents=True, exist_ok=True)

            (app_dir / "active.txt").write_text("app.local.json\n", encoding="utf-8")
            (app_dir / "app.local.json").write_text(json.dumps({"app": {"mode": "local"}}), encoding="utf-8")
            (app_dir / "app.prod.json").write_text(json.dumps({"app": {"mode": "prod"}}), encoding="utf-8")
            (plc_dir / "active.txt").write_text("default.json\n", encoding="utf-8")
            (plc_dir / "default.json").write_text(
                json.dumps({"scenarioDir": "config/simulators/plc/scenarios"}),
                encoding="utf-8",
            )

            (profiles_dir / "active.prod.json").write_text(
                json.dumps({"app": "app.prod.json", "simulators/plc": "default.json"}),
                encoding="utf-8",
            )
            (config_root / "active.txt").write_text(".profiles/active.prod.json\n", encoding="utf-8")

            result = resolve_config_tree(root)
            self.assertEqual(result.errors, [])
            self.assertEqual([d.domain_id for d in result.domains], ["app", "simulators/plc"])
            by_id = {d.domain_id: d for d in result.domains}
            self.assertEqual(by_id["app"].active_filename, "app.prod.json")
            self.assertEqual(by_id["simulators/plc"].active_filename, "default.json")
            self.assertEqual(result.effective_config["app"]["mode"], "prod")
            self.assertEqual(result.effective_config["scenarioDir"], "config/simulators/plc/scenarios")
            self.assertEqual(result.wrapped_effective_config["app"]["app"]["mode"], "prod")
            self.assertEqual(
                result.wrapped_effective_config["simulators"]["plc"]["scenarioDir"],
                "config/simulators/plc/scenarios",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
