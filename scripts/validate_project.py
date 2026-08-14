#!/usr/bin/env python3
"""Validate repository policy, plugin packaging, and routing contracts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - exercised on minimal installations
    yaml = None

from validate_evals import ROUTES as EXPECTED_ROUTES
from validate_evals import load_cases, validate_cases
from validate_harness import static_errors
from validate_plugin import validate_plugin


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "plugins" / "engineer-software"
SKILL_DIR = PLUGIN_DIR / "skills" / "engineer-software"
SKILL_PATH = SKILL_DIR / "SKILL.md"
REFERENCE_DIR = SKILL_DIR / "references"
EXPECTED_REFERENCES = {f"{route}.md" for route in EXPECTED_ROUTES}
REQUIRED_REFERENCE_HEADINGS = ("## Enter", "## Execute", "## Exit")
REQUIRED_PUBLIC_FILES = {
    "README.md",
    "README.zh-CN.md",
    "LICENSE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SUPPORT.md",
    "SECURITY.md",
    "PRIVACY.md",
    "TERMS.md",
    "ROADMAP.md",
    "docs/compatibility.md",
}
SCAFFOLD_MARKER = "[TO" + "DO"
CHINESE_README_REQUIRED_LINKS = (
    "README.md",
    "docs/compatibility.md",
    "CONTRIBUTING.md",
    "ROADMAP.md",
    "SECURITY.md",
    "PRIVACY.md",
    "TERMS.md",
    "plugins/engineer-software/skills/engineer-software/SKILL.md",
)
CHINESE_README_BOUNDARIES = (
    "canonical",
    ".dsh/skills",
    "developer preview",
    "loader smoke",
    "不是 DeepSeek 官方插件",
)


def relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_text(path: Path, errors: list[str]) -> str:
    if not path.is_file():
        errors.append(f"missing file: {relative(path)}")
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        errors.append(f"file is not readable UTF-8: {relative(path)}")
        return ""


def load_json(path: Path, errors: list[str], *, expected: type | None = None) -> Any:
    text = read_text(path, errors)
    if not text:
        return None
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {relative(path)}: {exc}")
        return None
    if expected is not None and not isinstance(value, expected):
        errors.append(f"{relative(path)} must contain a {expected.__name__}")
        return None
    return value


def parse_yaml_text(text: str, label: str, errors: list[str]) -> Any:
    if yaml is None:
        errors.append("PyYAML is required; install requirements-dev.txt")
        return None
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        errors.append(f"invalid YAML in {label}: {exc}")
        return None


def parse_frontmatter(text: str, label: str, errors: list[str]) -> dict[str, Any] | None:
    if not text.startswith("---\n"):
        errors.append(f"{label} frontmatter is missing")
        return None
    end = text.find("\n---", 4)
    if end == -1:
        errors.append(f"{label} frontmatter is not closed")
        return None
    value = parse_yaml_text(text[4:end], label, errors)
    if not isinstance(value, dict):
        errors.append(f"{label} frontmatter must be an object")
        return None
    return value


def validate_marketplace(marketplace: dict[str, Any] | None, errors: list[str]) -> None:
    if marketplace is None:
        return
    if marketplace.get("name") != "engineer-software":
        errors.append("marketplace name must be engineer-software")
    interface = marketplace.get("interface")
    if not isinstance(interface, dict) or interface.get("displayName") != "Engineer Software":
        errors.append("marketplace interface.displayName must be Engineer Software")
    entries = marketplace.get("plugins")
    if not isinstance(entries, list) or len(entries) != 1 or not isinstance(entries[0], dict):
        errors.append("marketplace must expose exactly one plugin object")
        return
    entry = entries[0]
    if entry.get("name") != "engineer-software":
        errors.append("marketplace plugin name must be engineer-software")
    source = entry.get("source")
    if source != {"source": "local", "path": "./plugins/engineer-software"}:
        errors.append("marketplace source must be the repository-relative local plugin")
    policy = entry.get("policy")
    if policy != {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}:
        errors.append("marketplace policy must use AVAILABLE and ON_INSTALL")
    if entry.get("category") != "Developer Tools":
        errors.append("marketplace category must be Developer Tools")


def validate_skill(skill: str, metadata: str, errors: list[str]) -> None:
    if not skill:
        return
    if SCAFFOLD_MARKER in skill:
        errors.append("SKILL.md still contains a scaffold TODO")
    if len(skill.splitlines()) > 120:
        errors.append("SKILL.md must remain at or below 120 lines")
    front = parse_frontmatter(skill, "SKILL.md", errors)
    if front is not None:
        if front.get("name") != "engineer-software":
            errors.append("SKILL.md frontmatter name is incorrect")
        description = front.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append("SKILL.md frontmatter description is required")
        else:
            if len(description) > 700:
                errors.append("SKILL.md description is too broad or verbose")
            for phrase in ("Do not use", "software", "failure", "refactor"):
                if phrase.casefold() not in description.casefold():
                    errors.append(f"SKILL.md description must contain {phrase!r}")
    linked = set(re.findall(r"\(references/([a-z0-9-]+\.md)\)", skill))
    if linked != EXPECTED_REFERENCES:
        errors.append(f"SKILL.md links {sorted(linked)}, expected {sorted(EXPECTED_REFERENCES)}")
    for phrase in ("Read exactly one primary module", "Do not pre-read", "bypass"):
        if phrase.casefold() not in skill.casefold():
            errors.append(f"SKILL.md lacks required routing phrase {phrase!r}")

    if metadata:
        value = parse_yaml_text(metadata, "agents/openai.yaml", errors)
        if not isinstance(value, dict):
            errors.append("agents/openai.yaml must contain an object")
        else:
            policy = value.get("policy")
            if not isinstance(policy, dict) or policy.get("allow_implicit_invocation") is not True:
                errors.append("engineer-software must explicitly allow implicit invocation")


def validate_references(errors: list[str]) -> None:
    actual = {path.name for path in REFERENCE_DIR.glob("*.md")}
    if actual != EXPECTED_REFERENCES:
        errors.append(f"reference set is {sorted(actual)}, expected {sorted(EXPECTED_REFERENCES)}")
    for filename in sorted(EXPECTED_REFERENCES):
        text = read_text(REFERENCE_DIR / filename, errors)
        for heading in REQUIRED_REFERENCE_HEADINGS:
            if heading not in text:
                errors.append(f"{filename} lacks {heading}")
        if re.search(r"\]\((?:\.\./)?references/", text):
            errors.append(f"{filename} creates a nested reference hop")

    deliver = read_text(REFERENCE_DIR / "deliver-change.md", errors)
    for phrase in ("structure-risk gate", "existing owner", "parallel implementation", "final state"):
        if phrase.casefold() not in deliver.casefold():
            errors.append(f"deliver-change.md must contain {phrase!r}")
    inspection = read_text(REFERENCE_DIR / "inspect-structure.md", errors)
    for phrase in ("migration", "generated", "fault isolation", "performance", "decision record"):
        if phrase.casefold() not in inspection.casefold():
            errors.append(f"inspect-structure.md must qualify {phrase!r}")
    work_items = read_text(REFERENCE_DIR / "manage-work-items.md", errors)
    for phrase in ("local draft", "Do not publish", "remote tracker"):
        if phrase.casefold() not in work_items.casefold():
            errors.append(f"manage-work-items.md must contain {phrase!r}")


def validate_public_files(readme: str, license_text: str, errors: list[str]) -> None:
    for filename in sorted(REQUIRED_PUBLIC_FILES):
        if not (ROOT / filename).is_file():
            errors.append(f"missing public release file: {filename}")
    for phrase in (
        "GitHub is a distribution target, not a runtime route",
        "Python 3.9",
        "validate_plugin.py",
        "validate_evals.py",
        "runtime-neutral",
        ".dsh/skills",
        "README.zh-CN.md",
    ):
        if phrase not in readme:
            errors.append(f"README must contain {phrase!r}")
    if "MIT License" not in license_text:
        errors.append("LICENSE is not the MIT License")


def validate_local_markdown_links(path: Path, text: str, errors: list[str]) -> None:
    """Reject missing or repository-escaping local Markdown links."""
    label = relative(path)
    for raw in re.findall(r"\]\(([^)]+)\)", text):
        target = raw.split("#", 1)[0].strip()
        if target.startswith(("http://", "https://", "mailto:", "//")):
            continue
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        if not target:
            continue
        candidate = (path.parent / target).resolve()
        try:
            candidate.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f"{label} link escapes repository: {target}")
        else:
            if not candidate.is_file():
                errors.append(f"{label} links to missing file: {target}")


def validate_chinese_readme(text: str, errors: list[str]) -> None:
    """Keep the Chinese entry linked and honest without making it a second specification."""
    if not text:
        return
    for phrase in CHINESE_README_BOUNDARIES:
        if phrase not in text:
            errors.append(f"README.zh-CN.md must contain {phrase!r}")
    for target in CHINESE_README_REQUIRED_LINKS:
        if f"]({target})" not in text:
            errors.append(f"README.zh-CN.md must link to {target}")


def validate_repository_text(errors: list[str]) -> None:
    ignored_parts = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "runs", "dist"}
    ignored_files = {"validate_plugin.py", "validate_project.py"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.name in ignored_files or ignored_parts.intersection(path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if path.suffix.casefold() == ".md":
            validate_local_markdown_links(path, text, errors)
        if SCAFFOLD_MARKER in text:
            errors.append(f"repository contains a scaffold TODO in {relative(path)}")


def validate_harness_projection(errors: list[str]) -> None:
    for error in static_errors():
        errors.append(f"Harness compatibility preflight: {error}")


def validate_project() -> list[str]:
    errors: list[str] = []
    marketplace = load_json(
        ROOT / ".agents" / "plugins" / "marketplace.json", errors, expected=dict
    )
    plugin = load_json(
        PLUGIN_DIR / ".codex-plugin" / "plugin.json", errors, expected=dict
    )
    skill = read_text(SKILL_PATH, errors)
    metadata = read_text(SKILL_DIR / "agents" / "openai.yaml", errors)
    readme = read_text(ROOT / "README.md", errors)
    chinese_readme = read_text(ROOT / "README.zh-CN.md", errors)
    license_text = read_text(ROOT / "LICENSE", errors)

    validate_marketplace(marketplace, errors)
    if plugin is not None:
        expected_pairs = {"name": "engineer-software", "license": "MIT", "skills": "./skills/"}
        for key, expected in expected_pairs.items():
            if plugin.get(key) != expected:
                errors.append(f"plugin {key!r} must equal {expected!r}")
        if plugin.get("repository") != "https://github.com/KirschBluteX/engineer-software":
            errors.append("plugin repository URL is missing or incorrect")
        version = plugin.get("version")
        if isinstance(version, str) and "+" in version and not version.split("+", 1)[1].startswith("codex."):
            errors.append("plugin build metadata must use one +codex.<cachebuster> suffix")

    plugin_errors = validate_plugin(PLUGIN_DIR)
    errors.extend(f"plugin preflight: {error}" for error in plugin_errors)
    validate_skill(skill, metadata, errors)
    validate_references(errors)

    case_errors: list[str] = []
    cases = load_cases(ROOT / "evals" / "routing-cases.json", case_errors)
    case_errors.extend(validate_cases(cases, REFERENCE_DIR))
    errors.extend(f"routing preflight: {error}" for error in case_errors)

    validate_public_files(readme, license_text, errors)
    validate_chinese_readme(chinese_readme, errors)
    validate_harness_projection(errors)
    validate_repository_text(errors)
    return errors


def main() -> int:
    errors = validate_project()
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Validation passed: repository, plugin, skill, references, and routing cases are consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
