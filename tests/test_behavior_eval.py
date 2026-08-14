from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_behavior_worktrees import FIXTURE_ROOT  # noqa: E402
from run_behavior_eval import (  # noqa: E402
    SKILL_PATH,
    build_command,
    classify_completion,
    git_evidence,
    load_cases,
    prompt_for,
    workspace_errors,
)
from summarize_behavior_eval import METRICS, collect_scores  # noqa: E402


class BehaviorEvaluationContractTests(unittest.TestCase):
    def test_cases_are_unique_and_cover_all_primary_routes(self) -> None:
        cases = load_cases()
        self.assertEqual(len(cases), len({case["id"] for case in cases}))
        self.assertEqual(
            {
                "shape-work",
                "trace-failure",
                "probe-choice",
                "deliver-change",
                "inspect-structure",
                "manage-work-items",
                "bypass",
            },
            {case["route"] for case in cases},
        )

    def test_treatment_prompt_names_canonical_skill_and_baseline_disables_it(self) -> None:
        case = load_cases()[0]
        treatment = prompt_for(case, "treatment")
        baseline = prompt_for(case, "baseline")
        self.assertIn(str(SKILL_PATH), treatment)
        self.assertIn("Use $engineer-software", treatment)
        self.assertNotIn("Use $engineer-software", baseline)
        self.assertIn("Do not load or use Engineer Software", baseline)

    def test_case_file_is_plain_json_with_source_provenance(self) -> None:
        value = json.loads((ROOT / "evals" / "behavior-cases.json").read_text(encoding="utf-8"))
        for case in value:
            self.assertTrue(case["source"])
            self.assertTrue(case["source_url"].startswith("https://"))

    def test_every_behavior_case_has_one_checked_in_fixture(self) -> None:
        case_ids = {case["id"] for case in load_cases()}
        fixture_ids = {path.name for path in FIXTURE_ROOT.iterdir() if path.is_dir()}
        self.assertEqual(case_ids, fixture_ids)

    def test_worktree_preparation_creates_clean_testable_pair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "worktrees"
            prepared = subprocess.run(
                [
                    sys.executable,
                    "scripts/prepare_behavior_worktrees.py",
                    "--output-root",
                    str(output),
                    "--case-id",
                    "shape-cache-contract",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(0, prepared.returncode, prepared.stderr)
            for condition in ("baseline", "treatment"):
                workspace = output / f"shape-cache-contract--{condition}"
                with self.subTest(condition=condition):
                    self.assertTrue((workspace / ".git").is_dir())
                    status = subprocess.run(
                        ["git", "status", "--porcelain=v1"],
                        cwd=workspace,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        check=False,
                    )
                    self.assertEqual(0, status.returncode, status.stderr)
                    self.assertEqual("", status.stdout)
                    tracked = subprocess.run(
                        ["git", "ls-files"],
                        cwd=workspace,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        check=False,
                    )
                    self.assertEqual(0, tracked.returncode, tracked.stderr)
                    tracked_paths = tracked.stdout.splitlines()
                    self.assertIn(".gitignore", tracked_paths)
                    self.assertFalse(any("__pycache__" in path for path in tracked_paths))
                    self.assertFalse(any(path.endswith((".pyc", ".pyo")) for path in tracked_paths))
                    tests = subprocess.run(
                        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                        cwd=workspace,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        check=False,
                    )
                    self.assertEqual(0, tests.returncode, tests.stderr)
                    status_after_tests = subprocess.run(
                        ["git", "status", "--porcelain=v1"],
                        cwd=workspace,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        check=False,
                    )
                    self.assertEqual(0, status_after_tests.returncode, status_after_tests.stderr)
                    self.assertEqual("", status_after_tests.stdout)

            dirty_workspace = output / "shape-cache-contract--baseline"
            scratch = dirty_workspace / "scratch.txt"
            scratch.write_text("contamination\n", encoding="utf-8")
            search = dirty_workspace / "search.py"
            search.write_text(search.read_text(encoding="utf-8") + "\n# tracked change\n", encoding="utf-8")
            evidence = git_evidence(dirty_workspace)
            self.assertIn("tracked change", evidence["diff_patch"])
            self.assertEqual(
                scratch.read_bytes().decode("utf-8"),
                evidence["untracked_files"]["scratch.txt"]["text"],
            )
            self.assertEqual(64, len(evidence["untracked_files"]["scratch.txt"]["sha256"]))
            errors = workspace_errors(
                [next(case for case in load_cases() if case["id"] == "shape-cache-contract")],
                "baseline",
                output,
            )
            self.assertTrue(any("not clean" in error for error in errors))

    def test_worktree_preparation_rejects_output_inside_source_repository(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory) / "worktrees"
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/prepare_behavior_worktrees.py",
                    "--output-root",
                    str(output),
                    "--case-id",
                    "shape-cache-contract",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(2, completed.returncode)
            self.assertIn("outside the source repository", completed.stderr)
            self.assertFalse(output.exists())

    def test_worktree_preparation_checks_all_conflicts_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "worktrees"
            conflict = output / "deliver-profile-error--baseline"
            conflict.mkdir(parents=True)
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/prepare_behavior_worktrees.py",
                    "--output-root",
                    str(output),
                    "--case-id",
                    "bypass-mechanical-rename",
                    "--case-id",
                    "deliver-profile-error",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
            self.assertEqual(2, completed.returncode)
            self.assertIn("worktree already exists", completed.stderr)
            self.assertFalse((output / "bypass-mechanical-rename--baseline").exists())
            self.assertFalse((output / "bypass-mechanical-rename--treatment").exists())

    def test_runner_places_global_approval_flag_before_exec(self) -> None:
        command = build_command(["codex"], Path("last.txt"), "prompt")
        self.assertLess(command.index("--ask-for-approval"), command.index("exec"))
        self.assertIn("--sandbox", command)
        self.assertIn(["--disable", "plugins"], [command[index : index + 2] for index in range(len(command) - 1)])
        self.assertIn(
            ["--disable", "skill_search"],
            [command[index : index + 2] for index in range(len(command) - 1)],
        )
        self.assertEqual(2, command.count("--disable"))
        self.assertIn("--ignore-user-config", command)
        configured = build_command(
            ["codex"],
            Path("last.txt"),
            "prompt",
            ignore_user_config=False,
        )
        self.assertNotIn("--ignore-user-config", configured)

    def test_completion_state_distinguishes_cli_failure_from_missing_response(self) -> None:
        self.assertEqual("completed", classify_completion(0, "done"))
        self.assertEqual("no_final_response", classify_completion(0, ""))
        self.assertEqual("command_failed", classify_completion(1, "provider error"))

    def test_score_collector_rejects_out_of_range_and_incomplete_scores(self) -> None:
        scores = {metric: 2 for metric in METRICS}
        scores["evidence"] = 5
        paired, errors, unscored = collect_scores(
            [
                {
                    "id": "case",
                    "condition": "baseline",
                    "completion_state": "completed",
                    "exit_code": 0,
                    "scores": scores,
                },
                {"id": "case", "condition": "treatment"},
            ]
        )
        self.assertEqual({}, paired)
        self.assertEqual({"baseline": 0, "treatment": 1}, unscored)
        self.assertTrue(any("evidence" in error and "0 to 4" in error for error in errors))

    def test_score_summary_uses_only_complete_pairs(self) -> None:
        scores = {metric: 2 for metric in METRICS}
        rows = [
            {
                "id": "complete",
                "condition": "baseline",
                "completion_state": "completed",
                "exit_code": 0,
                "scores": scores,
            },
            {
                "id": "complete",
                "condition": "treatment",
                "completion_state": "completed",
                "exit_code": 0,
                "scores": {metric: 3 for metric in METRICS},
            },
            {"id": "raw-only", "condition": "baseline"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scores.json"
            path.write_text(json.dumps({"results": rows}), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "scripts/summarize_behavior_eval.py", str(path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("Scored paired cases: 1", completed.stdout)
        self.assertIn("Unscored raw rows: baseline=1, treatment=0", completed.stdout)
        self.assertIn("mean_delta=+1.00", completed.stdout)

    def test_score_collector_rejects_duplicate_unscored_rows(self) -> None:
        paired, errors, unscored = collect_scores(
            [
                {"id": "case", "condition": "baseline"},
                {"id": "case", "condition": "baseline"},
            ]
        )
        self.assertEqual({}, paired)
        self.assertEqual({"baseline": 1, "treatment": 0}, unscored)
        self.assertTrue(any("duplicate score row" in error for error in errors))

    def test_score_collector_rejects_environment_failures(self) -> None:
        scores = {metric: 2 for metric in METRICS}
        paired, errors, unscored = collect_scores(
            [
                {
                    "id": "case",
                    "condition": "baseline",
                    "completion_state": "command_failed",
                    "exit_code": 1,
                    "scores": scores,
                }
            ]
        )
        self.assertEqual({}, paired)
        self.assertEqual({"baseline": 0, "treatment": 0}, unscored)
        self.assertTrue(any("cannot be scored" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
