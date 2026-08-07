from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = (
    ROOT
    / "plugins"
    / "engineer-software"
    / "skills"
    / "engineer-software"
    / "references"
)
sys.path.insert(0, str(ROOT / "scripts"))

from validate_project import EXPECTED_ROUTES, validate_project  # noqa: E402


class ProjectContractTests(unittest.TestCase):
    def test_repository_contract(self) -> None:
        errors = validate_project()
        self.assertEqual([], errors, "\n".join(errors))

    def test_routing_fixture_covers_every_module_and_bypass(self) -> None:
        cases = json.loads((ROOT / "evals" / "routing-cases.json").read_text(encoding="utf-8"))
        routes = {case["route"] for case in cases}
        self.assertEqual(EXPECTED_ROUTES | {"bypass"}, routes)

    def test_every_transition_names_a_real_module(self) -> None:
        cases = json.loads((ROOT / "evals" / "routing-cases.json").read_text(encoding="utf-8"))
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertLessEqual(set(case["allowed_next"]), EXPECTED_ROUTES)

    def test_fixture_transitions_are_supported_by_module_exits(self) -> None:
        cases = json.loads((ROOT / "evals" / "routing-cases.json").read_text(encoding="utf-8"))
        for case in cases:
            if case["route"] == "bypass":
                self.assertEqual([], case["allowed_next"])
                continue
            module = (REFERENCE_DIR / f"{case['route']}.md").read_text(encoding="utf-8")
            exit_text = module.split("## Exit", maxsplit=1)[1]
            for next_route in case["allowed_next"]:
                with self.subTest(case=case["id"], next_route=next_route):
                    self.assertIn(f"`{next_route}`", exit_text)


if __name__ == "__main__":
    unittest.main()
