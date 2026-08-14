from __future__ import annotations

import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "plugins" / "engineer-software" / "skills" / "engineer-software"
PROJECTION = ROOT / ".dsh" / "skills" / "engineer-software"
CASES = ROOT / "evals" / "routing-cases.json"

sys.path.insert(0, str(ROOT / "scripts"))
from sync_harness_skill import compare_projection, write_projection  # noqa: E402
from validate_evals import validate_cases  # noqa: E402
from validate_harness import OFFICIAL_SOURCES, static_errors  # noqa: E402


class HarnessContractTests(unittest.TestCase):
    def test_projection_checker_rejects_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "engineer-software"
            write_projection(target)
            reference = target / "references" / "deliver-change.md"
            reference.write_text(reference.read_text(encoding="utf-8") + "\nDrift.\n", encoding="utf-8")
            errors = compare_projection(target)
        self.assertTrue(any("projection drift" in error.casefold() for error in errors))

    def test_static_probe_accepts_explicit_external_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "engineer-software"
            write_projection(target)
            errors = static_errors(target)
        self.assertEqual([], errors, "\n".join(errors))

    def test_static_probe_rejects_rogue_skill_source(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            rogue = Path(directory) / "rogue" / "SKILL.md"
            rogue.parent.mkdir()
            rogue.write_text("---\nname: rogue\ndescription: rogue\n---\n", encoding="utf-8")
            errors = static_errors(PROJECTION)
        self.assertTrue(any("unexpected non-canonical" in error for error in errors))

    def test_shared_routing_fixtures_validate_against_both_skill_trees(self) -> None:
        cases = json.loads(CASES.read_text(encoding="utf-8"))
        for runtime, skill_dir in (("codex", CANONICAL), ("deepseek-harness", PROJECTION)):
            with self.subTest(runtime=runtime):
                errors = validate_cases(cases, skill_dir / "references")
                self.assertEqual([], errors, "\n".join(errors))

    def test_official_contract_sources_are_documented(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        compatibility = (ROOT / "docs" / "compatibility.md").read_text(encoding="utf-8")
        for source in OFFICIAL_SOURCES:
            with self.subTest(source=source):
                self.assertTrue(source in readme or source in compatibility)

    def test_cover_asset_is_reasonable_png(self) -> None:
        cover = ROOT / "plugins" / "engineer-software" / "assets" / "engineer-software-cover.png"
        data = cover.read_bytes()
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
        width, height = struct.unpack(">II", data[16:24])
        self.assertEqual((1536, 1024), (width, height))
        self.assertLess(len(data), 5 * 1024 * 1024)

    def test_workflow_contracts(self) -> None:
        try:
            import yaml
        except ImportError:  # pragma: no cover - requirements-dev supplies PyYAML
            self.skipTest("PyYAML is not installed")
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        parsed = yaml.safe_load(workflow)
        job = parsed["jobs"]["validate"]
        self.assertEqual(["3.9", "3.12", "3.13"], job["strategy"]["matrix"]["python-version"])
        setup = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/setup-python"))
        self.assertNotIn("cache", setup.get("with", {}))
        commands = "\n".join(step.get("run", "") for step in job["steps"])
        for command in (
            "python scripts/validate_project.py",
            "python -m unittest discover -s tests -v",
            "python -m compileall -q scripts tests",
        ):
            with self.subTest(command=command):
                self.assertIn(command, commands)
        self.assertNotIn("python scripts/validate_plugin.py", commands)
        self.assertNotIn("python scripts/validate_evals.py", commands)

        release = yaml.safe_load(
            (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        )
        release_commands = "\n".join(
            step.get("run", "") for step in release["jobs"]["release"]["steps"]
        )
        for command in (
            "python scripts/validate_project.py",
            "python -m unittest discover -s tests -v",
            "python -m compileall -q scripts tests",
        ):
            with self.subTest(workflow="release", command=command):
                self.assertIn(command, release_commands)
        self.assertNotIn("python scripts/validate_plugin.py", release_commands)
        self.assertNotIn("python scripts/validate_evals.py", release_commands)

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
