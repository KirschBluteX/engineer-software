#!/usr/bin/env python3
"""Validate the installable plugin and its progressive-disclosure contract."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins" / "engineer-software"
SKILL_DIR = PLUGIN_DIR / "skills" / "engineer-software"
SKILL_PATH = SKILL_DIR / "SKILL.md"
REFERENCE_DIR = SKILL_DIR / "references"
EXPECTED_REFERENCES = {
    "shape-work.md",
    "trace-failure.md",
    "probe-choice.md",
    "deliver-change.md",
    "inspect-structure.md",
    "manage-work-items.md",
}
EXPECTED_ROUTES = {path.removesuffix(".md") for path in EXPECTED_REFERENCES}
REQUIRED_REFERENCE_HEADINGS = ("## Enter", "## Execute", "## Exit")
SCAFFOLD_MARKER = "[TO" + "DO"


def read_text(path: Path, errors: list[str]) -> str:
    if not path.is_file():
        errors.append(f"missing file: {path.relative_to(ROOT)}")
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append(f"not UTF-8: {path.relative_to(ROOT)}")
        return ""


def load_json(path: Path, errors: list[str]) -> object:
    text = read_text(path, errors)
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")
        return {}


def frontmatter(text: str) -> str:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    return match.group(1) if match else ""


def validate_project() -> list[str]:
    errors: list[str] = []

    marketplace = load_json(ROOT / ".agents" / "plugins" / "marketplace.json", errors)
    plugin = load_json(PLUGIN_DIR / ".codex-plugin" / "plugin.json", errors)
    cases = load_json(ROOT / "evals" / "routing-cases.json", errors)
    skill = read_text(SKILL_PATH, errors)
    metadata = read_text(SKILL_DIR / "agents" / "openai.yaml", errors)
    readme = read_text(ROOT / "README.md", errors)
    license_text = read_text(ROOT / "LICENSE", errors)

    if isinstance(marketplace, dict):
        if marketplace.get("name") != "engineer-software":
            errors.append("marketplace name must be engineer-software")
        entries = marketplace.get("plugins")
        if not isinstance(entries, list) or len(entries) != 1:
            errors.append("marketplace must expose exactly one plugin")
        elif entries[0].get("source", {}).get("path") != "./plugins/engineer-software":
            errors.append("marketplace plugin path is not repository-relative")

    if isinstance(plugin, dict):
        expected_pairs = {
            "name": "engineer-software",
            "license": "MIT",
            "skills": "./skills/",
        }
        for key, expected in expected_pairs.items():
            if plugin.get(key) != expected:
                errors.append(f"plugin {key!r} must equal {expected!r}")
        if not re.fullmatch(r"0\.1\.0(?:\+codex\.[0-9]+)?", str(plugin.get("version", ""))):
            errors.append("plugin version must retain the 0.1.0 release base and valid cachebuster")
        if plugin.get("repository") != "https://github.com/KirschBluteX/engineer-software":
            errors.append("plugin repository URL is missing or incorrect")

    if not skill:
        return errors
    if SCAFFOLD_MARKER in skill:
        errors.append("SKILL.md still contains scaffold TODOs")
    if len(skill.splitlines()) > 120:
        errors.append("SKILL.md must remain at or below 120 lines")
    fm = frontmatter(skill)
    if not fm:
        errors.append("SKILL.md frontmatter is missing")
    else:
        if not re.search(r"(?m)^name:\s*engineer-software\s*$", fm):
            errors.append("SKILL.md name is incorrect")
        description_match = re.search(r"(?ms)^description:\s*>-\s*\n(.+)$", fm)
        if not description_match:
            errors.append("SKILL.md needs a folded description")
        else:
            description = " ".join(line.strip() for line in description_match.group(1).splitlines())
            if len(description) > 700:
                errors.append("SKILL.md description is too broad or verbose")
            for phrase in ("Do not use", "software", "failure", "refactor"):
                if phrase.casefold() not in description.casefold():
                    errors.append(f"SKILL.md description must contain {phrase!r}")

    linked = set(re.findall(r"\(references/([a-z0-9-]+\.md)\)", skill))
    if linked != EXPECTED_REFERENCES:
        errors.append(f"SKILL.md links {sorted(linked)}, expected {sorted(EXPECTED_REFERENCES)}")
    if "Read exactly one primary module" not in skill:
        errors.append("SKILL.md lacks the one-primary-module loading gate")
    if "Do not pre-read" not in skill:
        errors.append("SKILL.md lacks an explicit speculative-read prohibition")
    if "bypass" not in skill.casefold():
        errors.append("SKILL.md lacks a bypass route")

    actual_references = {path.name for path in REFERENCE_DIR.glob("*.md")}
    if actual_references != EXPECTED_REFERENCES:
        errors.append(
            f"reference set is {sorted(actual_references)}, expected {sorted(EXPECTED_REFERENCES)}"
        )
    for filename in sorted(EXPECTED_REFERENCES):
        text = read_text(REFERENCE_DIR / filename, errors)
        for heading in REQUIRED_REFERENCE_HEADINGS:
            if heading not in text:
                errors.append(f"{filename} lacks {heading}")
        if re.search(r"\]\((?:\.\./)?references/", text):
            errors.append(f"{filename} creates a nested reference hop")

    deliver = read_text(REFERENCE_DIR / "deliver-change.md", errors)
    for phrase in (
        "structure-risk gate",
        "existing owner",
        "parallel implementation",
        "final state",
    ):
        if phrase.casefold() not in deliver.casefold():
            errors.append(f"deliver-change.md must contain {phrase!r}")

    inspection = read_text(REFERENCE_DIR / "inspect-structure.md", errors)
    for phrase in (
        "migration",
        "generated",
        "fault isolation",
        "performance",
        "decision record",
    ):
        if phrase.casefold() not in inspection.casefold():
            errors.append(f"inspect-structure.md must exclude or qualify {phrase!r}")

    work_items = read_text(REFERENCE_DIR / "manage-work-items.md", errors)
    for phrase in ("local draft", "Do not publish", "remote tracker"):
        if phrase.casefold() not in work_items.casefold():
            errors.append(f"manage-work-items.md must contain {phrase!r}")

    if "allow_implicit_invocation: true" not in metadata:
        errors.append("engineer-software must allow precise implicit invocation")

    if not isinstance(cases, list) or not cases:
        errors.append("routing cases must be a non-empty array")
    else:
        ids: list[str] = []
        routes: list[str] = []
        for index, case in enumerate(cases):
            if not isinstance(case, dict):
                errors.append(f"routing case {index} is not an object")
                continue
            ids.append(str(case.get("id", "")))
            route = str(case.get("route", ""))
            routes.append(route)
            if route not in EXPECTED_ROUTES | {"bypass"}:
                errors.append(f"routing case {index} has unknown route {route!r}")
            allowed_next = case.get("allowed_next")
            if not isinstance(allowed_next, list) or any(
                next_route not in EXPECTED_ROUTES for next_route in allowed_next
            ):
                errors.append(f"routing case {index} has invalid allowed_next")
            if not str(case.get("prompt", "")).strip():
                errors.append(f"routing case {index} has an empty prompt")
        if len(ids) != len(set(ids)):
            errors.append("routing case ids must be unique")
        counts = Counter(routes)
        for route in EXPECTED_ROUTES:
            if counts[route] < 2:
                errors.append(f"route {route} needs at least two cases")
        if counts["bypass"] < 3:
            errors.append("bypass needs at least three cases")

    if "GitHub is a distribution target, not a runtime route" not in readme:
        errors.append("README must separate GitHub distribution from runtime routing")
    if "MIT License" not in license_text:
        errors.append("LICENSE is not the MIT License")

    ignored_parts = {".git", "__pycache__", ".pytest_cache", ".venv", "venv"}
    repository_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in ROOT.rglob("*")
        if path.is_file() and not ignored_parts.intersection(path.parts)
    )
    if SCAFFOLD_MARKER in repository_text:
        errors.append("repository contains a scaffold TODO")

    return errors


def main() -> int:
    errors = validate_project()
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Validation passed: plugin, skill, references, and routing cases are consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
