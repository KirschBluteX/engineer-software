#!/usr/bin/env python3
"""Run a static DeepSeek Harness filesystem-skill compatibility probe."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sync_harness_skill import CANONICAL_DIR, DEFAULT_TARGET, compare_projection


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

    # The checked-in projection and an explicitly selected target are generated views,
    # not editable sources.
    allowed_skills = {
        CANONICAL_DIR / "SKILL.md",
        DEFAULT_TARGET / "SKILL.md",
        target / "SKILL.md",
    }
    for path in ROOT.rglob("SKILL.md"):
        if ".git" in path.parts:
            continue
        relative = path.relative_to(ROOT)
        if path in allowed_skills:
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
    return parser.parse_args()


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
