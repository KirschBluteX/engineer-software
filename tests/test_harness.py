from __future__ import annotations

import json
import re
import struct
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "plugins" / "engineer-software" / "skills" / "engineer-software"
PROJECTION = ROOT / ".dsh" / "skills" / "engineer-software"
CASES = ROOT / "evals" / "routing-cases.json"

sys.path.insert(0, str(ROOT / "scripts"))
from sync_harness_skill import compare_projection, expected_files  # noqa: E402
from validate_harness import OFFICIAL_SOURCES, static_errors  # noqa: E402


class HarnessContractTests(unittest.TestCase):
    def test_projection_passes_static_probe(self) -> None:
        self.assertEqual([], static_errors(PROJECTION))

    def test_projection_is_byte_identical_to_canonical_files(self) -> None:
        self.assertEqual([], compare_projection(PROJECTION))
        for relative in expected_files():
            with self.subTest(path=relative):
                self.assertEqual(
                    (CANONICAL / relative).read_bytes(),
                    (PROJECTION / relative).read_bytes(),
                )

    def test_only_one_editable_skill_source_exists(self) -> None:
        skill_files = {
            path
            for path in ROOT.rglob("SKILL.md")
            if ".git" not in path.parts
        }
        self.assertEqual({CANONICAL / "SKILL.md", PROJECTION / "SKILL.md"}, skill_files)

    def test_shared_routing_fixtures_cover_both_runtime_entries(self) -> None:
        cases = json.loads(CASES.read_text(encoding="utf-8"))
        routes = {case["route"] for case in cases if case["route"] != "bypass"}
        canonical_routes = {
            path.stem for path in (CANONICAL / "references").glob("*.md")
        }
        projected_routes = {
            path.stem for path in (PROJECTION / "references").glob("*.md")
        }
        self.assertTrue(routes <= canonical_routes)
        self.assertEqual(canonical_routes, projected_routes)

        expected = [
            (
                case["id"],
                "bypass" if case["route"] == "bypass" else "activate",
                case["route"],
                case["expected_behavior"],
                case["expected_result"],
            )
            for case in cases
        ]
        # Both runtime labels deliberately point at the same route/evidence record.
        runtime_expectations = {
            "codex": expected,
            "deepseek-harness": expected,
        }
        self.assertEqual(runtime_expectations["codex"], runtime_expectations["deepseek-harness"])

    def test_official_contract_sources_are_documented(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        compatibility = (ROOT / "docs" / "compatibility.md").read_text(encoding="utf-8")
        for source in OFFICIAL_SOURCES:
            with self.subTest(source=source):
                self.assertTrue(source in readme or source in compatibility)

    def test_readme_local_links_and_images_exist(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        links = re.findall(r"\]\(([^)]+)\)", readme)
        for raw in links:
            target = raw.split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            with self.subTest(target=target):
                self.assertTrue((ROOT / target).is_file(), target)

    def test_cover_asset_is_reasonable_png(self) -> None:
        cover = ROOT / "plugins" / "engineer-software" / "assets" / "engineer-software-cover.png"
        data = cover.read_bytes()
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
        width, height = struct.unpack(">II", data[16:24])
        self.assertEqual((1536, 1024), (width, height))
        self.assertLess(len(data), 5 * 1024 * 1024)

    def test_ci_keeps_matrix_and_disables_pip_cache(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn('python-version: ["3.9", "3.12", "3.13"]', workflow)
        self.assertNotIn("cache: pip", workflow)
        self.assertNotIn("cache-dependency-path", workflow)
        for command in (
            "python scripts/validate_plugin.py plugins/engineer-software",
            "python scripts/validate_evals.py",
            "python scripts/validate_project.py",
            "python -m unittest discover -s tests -v",
            "python -m compileall -q scripts tests",
        ):
            with self.subTest(command=command):
                self.assertIn(command, workflow)

    def test_workflow_is_parseable_yaml(self) -> None:
        try:
            import yaml
        except ImportError:  # pragma: no cover - requirements-dev supplies PyYAML
            self.skipTest("PyYAML is not installed")
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        parsed = yaml.safe_load(workflow)
        self.assertIsInstance(parsed, dict)
        self.assertIn("jobs", parsed)
        self.assertIn("validate", parsed["jobs"])

    def test_probe_command_is_reproducible(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/validate_harness.py", "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("static compatibility probe passed", completed.stdout)
        self.assertIn("developer preview", completed.stdout)


if __name__ == "__main__":
    unittest.main()
