from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins" / "engineer-software"
REFERENCE_DIR = PLUGIN_DIR / "skills" / "engineer-software" / "references"
sys.path.insert(0, str(ROOT / "scripts"))

from run_routing_eval import PUBLIC_CASE_IDS  # noqa: E402
from validate_evals import load_cases, validate_cases  # noqa: E402
from validate_plugin import SEMVER_RE, validate_manifest  # noqa: E402
from validate_project import load_json, validate_local_markdown_links  # noqa: E402


class ProjectContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = json.loads((ROOT / "evals" / "routing-cases.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads(
            (PLUGIN_DIR / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )

    def test_validator_rejects_directory_overlong_short_description(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["interface"]["shortDescription"] = "x" * 31
        errors: list[str] = []
        validate_manifest(PLUGIN_DIR, manifest, errors)
        self.assertTrue(any("shortDescription" in error and "<= 30" in error for error in errors))

    def test_semver_allows_future_release_bases_and_one_cachebuster(self) -> None:
        for version in ("0.1.0", "1.2.3", "2.0.0-beta.1", "1.2.3+codex.20260813010101"):
            with self.subTest(version=version):
                self.assertIsNotNone(SEMVER_RE.fullmatch(version))
        for version in ("01.2.3", "1.2", "1.2.3+bad suffix", "v1.2.3"):
            with self.subTest(version=version):
                self.assertIsNone(SEMVER_RE.fullmatch(version))

    def test_json_loader_rejects_wrong_root_type(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not-an-object.json"
            path.write_text("[]\n", encoding="utf-8")
            errors: list[str] = []
            value = load_json(path, errors, expected=dict)
        self.assertIsNone(value)
        self.assertTrue(any("must contain a dict" in error for error in errors))

    def test_markdown_link_validator_rejects_missing_local_target(self) -> None:
        errors: list[str] = []
        validate_local_markdown_links(ROOT / "README.md", "[missing](not-here.md)", errors)
        self.assertEqual(["README.md links to missing file: not-here.md"], errors)

    def test_case_validator_rejects_unsupported_transition(self) -> None:
        cases = copy.deepcopy(self.cases)
        target = next(case for case in cases if case["route"] == "manage-work-items")
        target["allowed_next"].append("shape-work")
        errors = validate_cases(cases, REFERENCE_DIR)
        self.assertTrue(any("unsupported transitions" in error for error in errors))

    def test_public_submission_case_minimum_and_fields(self) -> None:
        by_id = {case["id"]: case for case in self.cases}
        selected = [by_id[case_id] for case_id in PUBLIC_CASE_IDS]
        counts = Counter(case["polarity"] for case in selected)
        self.assertEqual(5, counts["positive"])
        self.assertEqual(3, counts["negative"])
        for case in selected:
            with self.subTest(case=case["id"]):
                self.assertTrue(case["expected_behavior"].strip())
                self.assertTrue(case["expected_result"].strip())
                self.assertTrue(case["fixture"].strip())

    def test_case_loader_rejects_non_array_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text("{}\n", encoding="utf-8")
            errors: list[str] = []
            cases = load_cases(path, errors)
        self.assertEqual([], cases)
        self.assertIn("routing case file must contain a JSON array", errors)


if __name__ == "__main__":
    unittest.main()
