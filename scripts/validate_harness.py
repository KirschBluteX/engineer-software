#!/usr/bin/env python3
"""Run a static DeepSeek Harness compatibility probe.

The probe validates the official filesystem skill contract locally.  ``--live``
only checks whether a local ``dsh`` executable can answer ``--version``; it
does not call a model or claim API compatibility.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from sync_harness_skill import CANONICAL_DIR, DEFAULT_TARGET, compare_projection, expected_files


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_SOURCES = (
    "https://github.com/deepseek-ai/deepseek-harness",
    "https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md",
    "https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/publish.md",
)


def _skill_frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---" not in text[4:]:
        raise ValueError(f"{path} does not have closed YAML frontmatter")
    return text[4 : text.find("\n---", 4)]


def static_errors(target: Path = DEFAULT_TARGET) -> list[str]:
    """Return errors for the checked-in projection and its source ownership."""

    errors = compare_projection(target)
    try:
        frontmatter = _skill_frontmatter(CANONICAL_DIR / "SKILL.md")
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(str(exc))
        frontmatter = ""
    if "name: engineer-software" not in frontmatter:
        errors.append("canonical SKILL.md frontmatter name is not engineer-software")
    if "description:" not in frontmatter:
        errors.append("canonical SKILL.md frontmatter description is missing")

    expected = set(expected_files())
    if expected != {Path("SKILL.md"), *(Path("references") / name for name in (
        "deliver-change.md",
        "inspect-structure.md",
        "manage-work-items.md",
        "probe-choice.md",
        "shape-work.md",
        "trace-failure.md",
    ))}:
        errors.append("canonical skill file set changed; update the projection contract deliberately")

    # The projection may be duplicated only under the generated Harness root.
    for path in ROOT.rglob("SKILL.md"):
        if ".git" in path.parts:
            continue
        relative = path.relative_to(ROOT)
        if path == CANONICAL_DIR / "SKILL.md" or path == target / "SKILL.md":
            continue
        errors.append(f"unexpected non-canonical SKILL.md source: {relative}")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe the official DeepSeek Harness skill contract.")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument(
        "--check",
        action="store_true",
        help="run the static probe (the default; accepted for script symmetry)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="run local dsh --version when available; never contacts a model",
    )
    return parser.parse_args()


def live_probe() -> int:
    raw = os.environ.get("DSH_BIN", "dsh")
    executable = shutil.which(raw)
    if executable is None:
        print("Live Harness probe: not run (dsh executable not found; static contract only).")
        return 0
    try:
        completed = subprocess.run(
            [executable, "--version"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"Live Harness probe: not verified ({exc}); static contract passed.")
        return 0
    output = (completed.stdout or completed.stderr).strip().splitlines()
    version = output[0] if output else "no version output"
    if completed.returncode:
        print(f"Live Harness probe: dsh --version exited {completed.returncode} ({version}); static contract passed.")
        return 0
    print(f"Live Harness probe: dsh responded ({version}); skill loading/API still not live-verified.")
    return 0


def main() -> int:
    args = parse_args()
    target = args.target.expanduser().resolve()
    errors = static_errors(target)
    if errors:
        print("DeepSeek Harness static compatibility probe failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("DeepSeek Harness static compatibility probe passed.")
    print("Official contract: project .dsh/skills/<name>/SKILL.md plus relative resources.")
    print("Status: developer preview; no live model/API verification was performed.")
    if args.live:
        return live_probe()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
