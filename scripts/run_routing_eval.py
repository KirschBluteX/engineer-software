#!/usr/bin/env python3
"""Run selected routing cases through an installed Codex plugin in read-only mode."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validate_evals import load_cases, validate_cases


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evals" / "routing-cases.json"
SCHEMA_PATH = ROOT / "evals" / "route-output.schema.json"
PUBLIC_CASE_IDS = (
    "direct-unclear-cache-behavior",
    "direct-intermittent-duplicate",
    "direct-state-model-experiment",
    "direct-closed-feature",
    "direct-duplicate-policy-audit",
    "negative-explain-code",
    "negative-mechanical-rename",
    "negative-format-only",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run live Engineer Software routing evaluations.")
    parser.add_argument("--live", action="store_true", help="Actually invoke codex exec")
    parser.add_argument(
        "--public-submission",
        action="store_true",
        help="Run the five positive and three negative reviewer-ready cases",
    )
    parser.add_argument("--case-id", action="append", default=[], help="Case id to run; repeatable")
    parser.add_argument("--limit", type=int, help="Run only the first N selected cases")
    parser.add_argument("--codex", default="codex", help="Codex CLI executable")
    parser.add_argument("--model", help="Optional explicit Codex model override")
    parser.add_argument("--output", type=Path, help="JSON result path; required with --live")
    return parser.parse_args()


def select_cases(cases: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    requested: set[str] = set(args.case_id)
    if args.public_submission:
        requested.update(PUBLIC_CASE_IDS)
    if requested:
        selected = [case for case in cases if case["id"] in requested]
        missing = requested - {case["id"] for case in selected}
        if missing:
            raise ValueError(f"unknown case ids: {sorted(missing)}")
    else:
        selected = list(cases)
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("--limit must be positive")
        selected = selected[: args.limit]
    return selected


def routing_prompt(case: dict[str, Any]) -> str:
    return f"""This is a read-only routing evaluation. Do not inspect files, run tools, or perform the task.
Use the installed skill catalog to decide whether Engineer Software should activate and, if it
activates, which single primary module must start from the user's current uncertainty. Return only
the JSON object required by the output schema.

User prompt:
{case['prompt']}
"""


def resolve_codex_command(raw_command: str) -> list[str]:
    """Resolve Codex without executing a Windows batch wrapper through a shell."""
    candidates: list[str | None]
    if os.name == "nt" and not Path(raw_command).suffix:
        candidates = [
            shutil.which(f"{raw_command}.cmd"),
            shutil.which(f"{raw_command}.exe"),
            shutil.which(raw_command),
        ]
    else:
        candidates = [shutil.which(raw_command)]
    resolved = next((candidate for candidate in candidates if candidate), None)
    if resolved is None:
        raise FileNotFoundError(f"Codex executable not found: {raw_command}")
    path = Path(resolved)
    if os.name == "nt" and path.suffix.lower() in {".cmd", ".bat"}:
        script = path.parent / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
        sibling_node = path.parent / "node.exe"
        node = str(sibling_node) if sibling_node.is_file() else shutil.which("node")
        if not script.is_file() or node is None:
            raise FileNotFoundError(
                "Windows Codex batch wrapper could not be resolved safely to node and codex.js"
            )
        return [node, str(script)]
    return [str(path)]


def run_case(case: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="engineer-software-eval-") as temp_dir:
        output_path = Path(temp_dir) / "last-message.json"
        command = [
            *args.codex_command,
            "exec",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--output-schema",
            str(SCHEMA_PATH),
            "--output-last-message",
            str(output_path),
        ]
        if args.model:
            command.extend(["--model", args.model])
        command.append(routing_prompt(case))
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )
        actual: dict[str, Any] | None = None
        parse_error: str | None = None
        if output_path.is_file():
            try:
                value = json.loads(output_path.read_text(encoding="utf-8"))
                if isinstance(value, dict):
                    actual = value
                else:
                    parse_error = "final response was not a JSON object"
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                parse_error = f"unable to parse final response: {exc}"
        else:
            parse_error = "Codex did not write a final response"
        expected_activation = "bypass" if case["route"] == "bypass" else "activate"
        passed = (
            completed.returncode == 0
            and actual is not None
            and actual.get("activation") == expected_activation
            and actual.get("route") == case["route"]
        )
        return {
            "id": case["id"],
            "expected": {"activation": expected_activation, "route": case["route"]},
            "actual": actual,
            "passed": passed,
            "exit_code": completed.returncode,
            "error": parse_error,
            "stderr_tail": completed.stderr[-1000:] if completed.returncode else "",
        }


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    raw_cases = load_cases(CASES_PATH, errors)
    errors.extend(validate_cases(raw_cases))
    if errors:
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2
    cases = [case for case in raw_cases if isinstance(case, dict)]
    try:
        selected = select_cases(cases, args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not args.live:
        print(f"Selected {len(selected)} valid cases. Add --live and --output to invoke Codex.")
        for case in selected:
            print(f"- {case['id']}: {case['route']}")
        return 0
    if args.output is None:
        print("--output is required with --live", file=sys.stderr)
        return 2
    try:
        args.codex_command = resolve_codex_command(args.codex)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    results: list[dict[str, Any]] = []
    for index, case in enumerate(selected, start=1):
        print(f"[{index}/{len(selected)}] {case['id']}", flush=True)
        try:
            results.append(run_case(case, args))
        except (subprocess.TimeoutExpired, OSError) as exc:
            results.append(
                {
                    "id": case["id"],
                    "expected": {
                        "activation": "bypass" if case["route"] == "bypass" else "activate",
                        "route": case["route"],
                    },
                    "actual": None,
                    "passed": False,
                    "exit_code": None,
                    "error": str(exc),
                    "stderr_tail": "",
                }
            )
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runner": "codex exec --ephemeral --sandbox read-only",
        "plugin": "engineer-software",
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    passed = sum(bool(result["passed"]) for result in results)
    print(f"Live routing evaluation: {passed}/{len(results)} passed; results: {args.output}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
