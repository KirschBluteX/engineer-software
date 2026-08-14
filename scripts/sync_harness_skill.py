#!/usr/bin/env python3
"""Synchronize the canonical Engineer Software skill into a Harness skill root.

The Codex plugin tree is the only editable source.  DeepSeek Harness discovers
project skills from ``.dsh/skills`` (or another configured skill root), so this
small projection keeps the two runtimes byte-identical without hand-maintained
copies.  The command never deletes files; stale output is reported by
``--check`` and must be removed deliberately by its owner.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_DIR = ROOT / "plugins" / "engineer-software" / "skills" / "engineer-software"
DEFAULT_TARGET = ROOT / ".dsh" / "skills" / "engineer-software"


def expected_files(source_dir: Path = CANONICAL_DIR) -> tuple[Path, ...]:
    """Return the source-relative files that form the Harness skill bundle."""

    references = source_dir / "references"
    if not (source_dir / "SKILL.md").is_file():
        raise FileNotFoundError(f"canonical skill is missing: {source_dir / 'SKILL.md'}")
    if not references.is_dir():
        raise FileNotFoundError(f"canonical references directory is missing: {references}")
    files = [Path("SKILL.md")]
    files.extend(
        sorted(
            path.relative_to(source_dir)
            for path in references.glob("*.md")
            if path.is_file()
        )
    )
    if not files[1:]:
        raise FileNotFoundError(f"canonical references are empty: {references}")
    return tuple(files)


def _file_map(root: Path) -> set[Path]:
    if not root.exists():
        return set()
    return {
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file()
    }


def compare_projection(
    target: Path = DEFAULT_TARGET,
    source_dir: Path = CANONICAL_DIR,
) -> list[str]:
    """Return deterministic drift errors for one generated projection."""

    expected = set(expected_files(source_dir))
    actual = _file_map(target)
    errors: list[str] = []
    for relative in sorted(expected - actual):
        errors.append(f"missing Harness projection file: {target / relative}")
    for relative in sorted(actual - expected):
        errors.append(f"unexpected Harness projection file: {target / relative}")
    for relative in sorted(expected & actual):
        source = source_dir / relative
        projected = target / relative
        if source.read_bytes() != projected.read_bytes():
            errors.append(f"Harness projection drift: {target / relative}")
    return errors


def write_projection(
    target: Path = DEFAULT_TARGET,
    source_dir: Path = CANONICAL_DIR,
) -> None:
    """Copy the canonical skill files into ``target`` without deleting output."""

    target.mkdir(parents=True, exist_ok=True)
    for relative in expected_files(source_dir):
        source = source_dir / relative
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate or check the DeepSeek Harness skill projection."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--write",
        action="store_true",
        help="write canonical files to the target (never removes stale files)",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="check the target for missing, extra, or drifted files",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_TARGET,
        help="Harness skill bundle directory (default: .dsh/skills/engineer-software)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = args.target.expanduser().resolve()
    try:
        if args.write:
            write_projection(target)
        errors = compare_projection(target)
    except (OSError, FileNotFoundError) as exc:
        print(f"Harness projection failed: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("Harness projection check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    action = "written and verified" if args.write else "verified"
    print(f"Harness projection {action}: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
