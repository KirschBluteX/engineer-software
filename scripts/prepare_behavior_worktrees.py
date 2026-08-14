#!/usr/bin/env python3
"""Prepare matched Git worktrees for the task-level behavior pilot."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "evals" / "behavior-fixtures"
CONDITIONS = ("baseline", "treatment")
GENERATED_GITIGNORE = "__pycache__/\n*.py[cod]\n.pytest_cache/\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Copy behavior fixtures into matched Git worktrees.")
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--case-id", action="append", default=[])
    return parser.parse_args()


def run(command: list[str], cwd: Path) -> None:
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "git command failed")


def main() -> int:
    args = parse_args()
    if not FIXTURE_ROOT.is_dir():
        print(f"missing fixture root: {FIXTURE_ROOT}", file=sys.stderr)
        return 2
    available = {path.name for path in FIXTURE_ROOT.iterdir() if path.is_dir()}
    selected = set(args.case_id) if args.case_id else available
    missing = sorted(selected - available)
    if missing:
        print(f"unknown behavior fixture ids: {missing}", file=sys.stderr)
        return 2
    output_root = args.output_root.expanduser().resolve()
    try:
        output_root.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        print("behavior worktrees must be created outside the source repository", file=sys.stderr)
        return 2
    destinations = [
        output_root / f"{case_id}--{condition}"
        for case_id in sorted(selected)
        for condition in CONDITIONS
    ]
    conflicts = [destination for destination in destinations if destination.exists()]
    if conflicts:
        for destination in conflicts:
            print(f"worktree already exists: {destination}", file=sys.stderr)
        return 2
    output_root.mkdir(parents=True, exist_ok=True)
    try:
        for case_id in sorted(selected):
            source = FIXTURE_ROOT / case_id
            for condition in CONDITIONS:
                destination = output_root / f"{case_id}--{condition}"
                shutil.copytree(
                    source,
                    destination,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".pytest_cache"),
                )
                (destination / ".gitignore").write_text(GENERATED_GITIGNORE, encoding="utf-8")
                run(["git", "init", "-q"], destination)
                run(["git", "add", "."], destination)
                run(
                    [
                        "git",
                        "-c",
                        "user.name=Engineer Software Eval",
                        "-c",
                        "user.email=eval@example.invalid",
                        "commit",
                        "-qm",
                        "chore: initialize behavior fixture",
                    ],
                    destination,
                )
    except (OSError, RuntimeError) as exc:
        print(f"unable to prepare behavior worktrees: {exc}", file=sys.stderr)
        return 1
    print(f"Prepared {len(selected) * len(CONDITIONS)} worktrees under {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
