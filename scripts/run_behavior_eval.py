#!/usr/bin/env python3
"""Run paired, task-level behavior evaluations in pre-isolated worktrees.

The runner deliberately does not decide whether a response is good. It records the
raw final response, JSONL tool events, timing, and filesystem evidence so a reviewer
can score behavior before comparing the conditions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_routing_eval import resolve_codex_command


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evals" / "behavior-cases.json"
SKILL_PATH = ROOT / "plugins" / "engineer-software" / "skills" / "engineer-software" / "SKILL.md"
RUNNER_PATH = Path(__file__).resolve()
MAX_UNTRACKED_BYTES = 64 * 1024
DISABLED_FEATURES = ("plugins", "skill_search")
DEFAULT_TIMEOUT_SECONDS = 3600


def load_cases() -> list[dict[str, Any]]:
    value = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, list) or not value:
        raise ValueError("behavior case file must contain a non-empty array")
    required = {"id", "route", "source", "source_url", "prompt"}
    cases: list[dict[str, Any]] = []
    for case in value:
        if not isinstance(case, dict) or set(case) != required:
            raise ValueError("each behavior case must contain exactly id, route, source, source_url, prompt")
        cases.append(case)
    if len({case["id"] for case in cases}) != len(cases):
        raise ValueError("behavior case ids must be unique")
    return cases


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a paired Engineer Software behavior evaluation.")
    parser.add_argument("--condition", choices=("baseline", "treatment"), required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--model")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--use-user-config",
        action="store_true",
        help="load the active model-provider config; use the same config for both conditions",
    )
    parser.add_argument("--live", action="store_true", help="invoke Codex; without this flag only validate selection")
    return parser.parse_args()


def select_cases(cases: list[dict[str, Any]], requested: list[str]) -> list[dict[str, Any]]:
    if not requested:
        return cases
    by_id = {case["id"]: case for case in cases}
    missing = sorted(set(requested) - set(by_id))
    if missing:
        raise ValueError(f"unknown behavior case ids: {missing}")
    return [by_id[case_id] for case_id in requested]


def prompt_for(case: dict[str, Any], condition: str) -> str:
    if condition == "treatment":
        condition_text = (
            f"Use $engineer-software at {SKILL_PATH} for this request. Load only the primary module "
            "that the skill's routing contract requires before acting."
        )
    else:
        condition_text = "Do not load or use Engineer Software or any other optional workflow skill."
    return f"""You are working in an isolated repository worktree.
{condition_text}
Do not commit, push, publish, or touch paths outside the worktree. Preserve unrelated user work.
This is a headless evaluation. Do not call interactive user-input tools; put any blocking questions
or approval request in the final response instead.
At the end, give a concise user-facing response with changed paths, exact verification evidence,
blockers, and remaining uncertainty. Do not claim a check passed unless you ran it.

User request:
{case['prompt']}
"""


def build_command(
    codex: list[str],
    last_message: Path,
    prompt: str,
    model: str | None = None,
    *,
    ignore_user_config: bool = True,
) -> list[str]:
    """Build a version-compatible command with global flags before ``exec``."""

    command = [
        *codex,
        "--ask-for-approval",
        "never",
        "exec",
        "--ephemeral",
        "--sandbox",
        "workspace-write",
        "--skip-git-repo-check",
        "--json",
        "--output-last-message",
        str(last_message),
    ]
    if ignore_user_config:
        command.insert(command.index("exec") + 2, "--ignore-user-config")
    for feature in DISABLED_FEATURES:
        command.extend(["--disable", feature])
    if model:
        command.extend(["--model", model])
    command.append(prompt)
    return command


def git_evidence(workspace: Path) -> dict[str, Any]:
    status = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=workspace,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    diff = subprocess.run(
        ["git", "diff", "--stat", "HEAD"],
        cwd=workspace,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    patch = subprocess.run(
        ["git", "diff", "--no-ext-diff", "--binary", "HEAD"],
        cwd=workspace,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=workspace,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    untracked_files: dict[str, dict[str, Any]] = {}
    if untracked.returncode == 0:
        for relative_text in filter(None, untracked.stdout.split("\0")):
            relative = Path(relative_text)
            candidate = workspace / relative
            if relative.is_absolute() or ".." in relative.parts or candidate.is_symlink():
                untracked_files[relative_text] = {"kind": "non-regular"}
                continue
            raw = candidate.read_bytes()
            record: dict[str, Any] = {
                "size": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
            if len(raw) <= MAX_UNTRACKED_BYTES:
                try:
                    record["text"] = raw.decode("utf-8")
                except UnicodeDecodeError:
                    record["text"] = None
            else:
                record["text"] = None
            untracked_files[relative_text] = record
    return {
        "status": status.stdout,
        "diff_stat": diff.stdout,
        "diff_patch": patch.stdout,
        "untracked_files": untracked_files,
        "status_exit_code": status.returncode,
        "diff_exit_code": diff.returncode,
        "patch_exit_code": patch.returncode,
        "untracked_exit_code": untracked.returncode,
    }


def workspace_errors(
    cases: list[dict[str, Any]], condition: str, workspace_root: Path
) -> list[str]:
    """Reject missing or contaminated worktrees before any model call."""

    errors: list[str] = []
    for case in cases:
        workspace = workspace_root / f"{case['id']}--{condition}"
        if not workspace.is_dir():
            errors.append(f"missing prepared worktree: {workspace}")
            continue
        evidence = git_evidence(workspace)
        if any(
            evidence[key] != 0
            for key in ("status_exit_code", "diff_exit_code", "patch_exit_code", "untracked_exit_code")
        ):
            errors.append(f"unable to inspect prepared worktree: {workspace}")
        elif evidence["status"].strip():
            errors.append(f"prepared worktree is not clean: {workspace}")
    return errors


def classify_completion(exit_code: int, final_response: str) -> str:
    if exit_code != 0:
        return "command_failed"
    if not final_response:
        return "no_final_response"
    return "completed"


def evaluation_settings(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "requested_model": args.model,
        "timeout_seconds": args.timeout,
        "use_user_config": args.use_user_config,
        "disabled_features": list(DISABLED_FEATURES),
        "skill_sha256": hashlib.sha256(SKILL_PATH.read_bytes()).hexdigest(),
        "runner_sha256": hashlib.sha256(RUNNER_PATH.read_bytes()).hexdigest(),
    }


def settings_fingerprint(settings: dict[str, Any]) -> str:
    serialized = json.dumps(settings, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def run_case(
    case: dict[str, Any],
    args: argparse.Namespace,
    codex: list[str],
    settings: dict[str, Any],
) -> dict[str, Any]:
    workspace = args.workspace_root / f"{case['id']}--{args.condition}"
    if not workspace.is_dir():
        raise FileNotFoundError(f"missing prepared worktree: {workspace}")
    with tempfile.TemporaryDirectory(prefix="engineer-software-behavior-") as temp_dir:
        temp = Path(temp_dir)
        last_message = temp / "last-message.txt"
        command = build_command(
            codex,
            last_message,
            prompt_for(case, args.condition),
            args.model,
            ignore_user_config=not args.use_user_config,
        )
        started = datetime.now(timezone.utc)
        completed = subprocess.run(
            command,
            cwd=workspace,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=args.timeout,
            check=False,
        )
        finished = datetime.now(timezone.utc)
        final = last_message.read_text(encoding="utf-8") if last_message.is_file() else ""
        return {
            "id": case["id"],
            "condition": args.condition,
            "route_target": case["route"],
            "source": case["source"],
            "source_url": case["source_url"],
            "experiment_settings": settings,
            "experiment_fingerprint": settings_fingerprint(settings),
            "workspace": str(workspace),
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "exit_code": completed.returncode,
            "timed_out": False,
            "completion_state": classify_completion(completed.returncode, final),
            "final_response": final,
            "events_jsonl": completed.stdout,
            "stderr_tail": completed.stderr[-4000:],
            "git": git_evidence(workspace),
        }


def main() -> int:
    args = parse_args()
    try:
        cases = select_cases(load_cases(), args.case_id)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not args.live:
        print(f"Selected {len(cases)} behavior cases for {args.condition}; add --live to invoke Codex.")
        for case in cases:
            print(f"- {case['id']}: expected workflow {case['route']}")
        return 0
    if args.output is None:
        print("--output is required with --live", file=sys.stderr)
        return 2
    preflight_errors = workspace_errors(cases, args.condition, args.workspace_root)
    if preflight_errors:
        for error in preflight_errors:
            print(error, file=sys.stderr)
        return 2
    try:
        codex = resolve_codex_command(args.codex)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    settings = evaluation_settings(args)
    fingerprint = settings_fingerprint(settings)
    results: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['id']}", flush=True)
        case_started = datetime.now(timezone.utc)
        try:
            results.append(run_case(case, args, codex, settings))
        except subprocess.TimeoutExpired as exc:
            case_finished = datetime.now(timezone.utc)
            results.append(
                {
                    "id": case["id"],
                    "condition": args.condition,
                    "route_target": case["route"],
                    "source": case["source"],
                    "source_url": case["source_url"],
                    "experiment_settings": settings,
                    "experiment_fingerprint": fingerprint,
                    "workspace": str(args.workspace_root / f"{case['id']}--{args.condition}"),
                    "started_at": case_started.isoformat(),
                    "finished_at": case_finished.isoformat(),
                    "exit_code": None,
                    "timed_out": True,
                    "completion_state": "timed_out",
                    "error": str(exc),
                    "git": git_evidence(args.workspace_root / f"{case['id']}--{args.condition}"),
                }
            )
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runner": "codex exec --ephemeral --json",
        "condition": args.condition,
        "experiment_settings": settings,
        "experiment_fingerprint": fingerprint,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(results)} raw behavior results to {args.output}")
    return 0 if all(result.get("exit_code") == 0 for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
