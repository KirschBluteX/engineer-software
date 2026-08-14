#!/usr/bin/env python3
"""Validate a plugin package against the Codex ingestion and directory contract.

The official package checker is still the final authority.  This repository keeps a small,
reproducible preflight so that CI catches the common manifest, asset, and skill errors before a
submission is uploaded.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

try:
    import yaml
except ImportError:  # pragma: no cover - exercised on minimal installations
    yaml = None


SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\."
    r"(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
HEX_COLOR_RE = re.compile(r"^#[0-9A-F]{6}$", re.IGNORECASE)
NUMBER_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")
PUBLIC_CATEGORIES = {
    "Productivity",
    "Creativity",
    "Developer Tools",
    "Business & Operations",
    "Data & Analytics",
    "Communication",
    "Education & Research",
    "Security",
    "Finance",
    "Healthcare",
    "Travel",
    "Entertainment",
    "Other",
}
TODO_MARKER = "[TODO:"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a local Codex plugin package.")
    parser.add_argument("plugin_path", help="Path to the plugin root directory")
    return parser.parse_args()


def load_json_object(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"{label} is missing")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        errors.append(f"{label} must contain valid UTF-8 JSON")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label} must contain a JSON object")
        return None
    return value


def reject_todos(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, str):
        if TODO_MARKER in value:
            errors.append(f"{path} still contains a [TODO: ...] placeholder")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            reject_todos(item, f"{path}[{index}]", errors)
    elif isinstance(value, dict):
        for key, item in value.items():
            reject_todos(item, f"{path}.{key}", errors)


def require_string(
    payload: dict[str, Any], key: str, errors: list[str], *, prefix: str = "plugin.json"
) -> str | None:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{prefix}.{key} must be a non-empty string")
        return None
    return value


def optional_string(
    payload: dict[str, Any], key: str, errors: list[str], *, prefix: str = "plugin.json"
) -> None:
    if key in payload and payload[key] is not None and (
        not isinstance(payload[key], str) or not payload[key].strip()
    ):
        errors.append(f"{prefix}.{key} must be a non-empty string when provided")


def reject_unknown(payload: dict[str, Any], allowed: set[str], prefix: str, errors: list[str]) -> None:
    for key in sorted(set(payload) - allowed):
        errors.append(f"{prefix}.{key} is not an accepted field")


def validate_https(value: Any, field: str, errors: list[str]) -> None:
    if value is None:
        return
    parsed = urlparse(value) if isinstance(value, str) else None
    if parsed is None or parsed.scheme != "https" or not parsed.netloc or parsed.username:
        errors.append(f"{field} must be an absolute https:// URL without credentials")
    elif len(value) > 1024:
        errors.append(f"{field} must be 1,024 characters or fewer")


def validate_path(
    plugin_root: Path,
    raw_path: Any,
    field: str,
    errors: list[str],
    *,
    expected_directory: bool = False,
) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        errors.append(f"{field} must be a non-empty relative path")
        return None
    candidate = PurePosixPath(raw_path.replace("\\", "/"))
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        errors.append(f"{field} must stay inside the plugin archive")
        return None
    resolved = (plugin_root / candidate.as_posix()).resolve()
    try:
        resolved.relative_to(plugin_root.resolve())
    except ValueError:
        errors.append(f"{field} must stay inside the plugin archive")
        return None
    if expected_directory and not resolved.is_dir():
        errors.append(f"{field} must point to an existing directory")
        return None
    if not expected_directory and not resolved.is_file():
        errors.append(f"{field} points to a missing file")
        return None
    return resolved


def validate_svg(path: Path, field: str, errors: list[str]) -> None:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError, UnicodeError):
        errors.append(f"{field} must be readable, well-formed SVG")
        return
    if root.tag.rsplit("}", 1)[-1] != "svg":
        errors.append(f"{field} must have an svg root element")
        return
    view_box = root.attrib.get("viewBox", "").split()
    dimensions: tuple[float, float] | None = None
    if len(view_box) == 4 and all(NUMBER_RE.fullmatch(part) for part in view_box):
        dimensions = (float(view_box[2]), float(view_box[3]))
    else:
        width = root.attrib.get("width", "")
        height = root.attrib.get("height", "")
        if NUMBER_RE.fullmatch(width) and NUMBER_RE.fullmatch(height):
            dimensions = (float(width), float(height))
    if dimensions is None:
        errors.append(f"{field} must define numeric square dimensions or viewBox")
        return
    width, height = dimensions
    if width <= 0 or height <= 0 or width != height:
        errors.append(f"{field} must be square with positive dimensions")
    elif width < 48:
        errors.append(f"{field} must be at least 48x48")


def validate_asset(plugin_root: Path, raw_path: Any, field: str, errors: list[str]) -> None:
    path = validate_path(plugin_root, raw_path, field, errors)
    if path is None:
        return
    suffix = path.suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
        errors.append(f"{field} must use .png, .jpg, .jpeg, .webp, or .svg")
    if path.stat().st_size > 5 * 1024 * 1024:
        errors.append(f"{field} must not exceed 5 MiB")
    if suffix == ".svg":
        validate_svg(path, field, errors)


def parse_yaml(path: Path, label: str, errors: list[str]) -> Any:
    if yaml is None:
        errors.append("PyYAML is required for plugin frontmatter validation; install requirements-dev.txt")
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError):
        errors.append(f"{label} must contain valid UTF-8 YAML")
        return None


def validate_skill(skill_root: Path, plugin_root: Path, errors: list[str]) -> None:
    skill_path = skill_root / "SKILL.md"
    if not skill_path.is_file():
        errors.append(f"skill {skill_root.name} is missing SKILL.md")
        return
    try:
        text = skill_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        errors.append(f"skill {skill_root.name}/SKILL.md is not readable UTF-8")
        return
    if not text.startswith("---\n"):
        errors.append(f"skill {skill_root.name} must start with YAML frontmatter")
    else:
        end = text.find("\n---", 4)
        if end == -1:
            errors.append(f"skill {skill_root.name} frontmatter is not closed")
        else:
            front = parse_yaml_text(text[4:end], f"skill {skill_root.name} frontmatter", errors)
            if not isinstance(front, dict):
                errors.append(f"skill {skill_root.name} frontmatter must be an object")
            else:
                if not isinstance(front.get("name"), str) or not front["name"].strip():
                    errors.append(f"skill {skill_root.name} frontmatter name is required")
                if not isinstance(front.get("description"), str) or not front["description"].strip():
                    errors.append(f"skill {skill_root.name} frontmatter description is required")
                disable = front.get("disable-model-invocation", front.get("disable_model_invocation"))
                if disable not in (None, False):
                    errors.append(f"skill {skill_root.name} must not disable model invocation")
    agent_path = skill_root / "agents" / "openai.yaml"
    if agent_path.is_file():
        agent = parse_yaml(agent_path, f"skill {skill_root.name} agent YAML", errors)
        if not isinstance(agent, dict):
            errors.append(f"skill {skill_root.name} agent YAML must be an object")
            return
        interface = agent.get("interface")
        if not isinstance(interface, dict):
            errors.append(f"skill {skill_root.name} agent interface is required")
        else:
            for key in ("display_name", "short_description"):
                if not isinstance(interface.get(key), str) or not interface[key].strip():
                    errors.append(f"skill {skill_root.name} interface.{key} is required")
            color = interface.get("brand_color")
            if color is not None and (not isinstance(color, str) or not HEX_COLOR_RE.fullmatch(color)):
                errors.append(f"skill {skill_root.name} interface.brand_color must be #RRGGBB")
        policy = agent.get("policy")
        if policy is not None and (
            not isinstance(policy, dict) or not isinstance(policy.get("allow_implicit_invocation"), bool)
        ):
            errors.append(f"skill {skill_root.name} policy.allow_implicit_invocation must be boolean")


def parse_yaml_text(text: str, label: str, errors: list[str]) -> Any:
    if yaml is None:
        errors.append("PyYAML is required for plugin frontmatter validation; install requirements-dev.txt")
        return None
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError:
        errors.append(f"{label} must be valid YAML")
        return None


def validate_manifest(plugin_root: Path, manifest: dict[str, Any], errors: list[str]) -> None:
    allowed = {
        "id",
        "name",
        "version",
        "description",
        "skills",
        "apps",
        "mcpServers",
        "interface",
        "author",
        "homepage",
        "repository",
        "license",
        "keywords",
    }
    reject_unknown(manifest, allowed, "plugin.json", errors)
    name = require_string(manifest, "name", errors)
    if name is not None and (" " in name or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)):
        errors.append("plugin.json.name must be kebab-case")
    version = require_string(manifest, "version", errors)
    if version is not None and SEMVER_RE.fullmatch(version) is None:
        errors.append("plugin.json.version must be strict SemVer")
    require_string(manifest, "description", errors)
    author = manifest.get("author")
    if not isinstance(author, dict):
        errors.append("plugin.json.author must be an object")
    else:
        reject_unknown(author, {"name", "email", "url"}, "plugin.json.author", errors)
        require_string(author, "name", errors, prefix="plugin.json.author")
        optional_string(author, "email", errors, prefix="plugin.json.author")
        validate_https(author.get("url"), "plugin.json.author.url", errors)
    for field in ("homepage", "repository"):
        validate_https(manifest.get(field), f"plugin.json.{field}", errors)
    skills = manifest.get("skills")
    if skills != "./skills/":
        errors.append("plugin.json.skills must be ./skills/")
    else:
        validate_path(plugin_root, skills, "plugin.json.skills", errors, expected_directory=True)
    keywords = manifest.get("keywords")
    if not isinstance(keywords, list) or not all(isinstance(item, str) and item.strip() for item in keywords):
        errors.append("plugin.json.keywords must be a list of non-empty strings")
    interface = manifest.get("interface")
    if not isinstance(interface, dict):
        errors.append("plugin.json.interface must be an object")
        return
    reject_unknown(
        interface,
        {
            "displayName",
            "shortDescription",
            "longDescription",
            "developerName",
            "category",
            "capabilities",
            "websiteURL",
            "privacyPolicyURL",
            "termsOfServiceURL",
            "defaultPrompt",
            "default_prompt",
            "brandColor",
            "composerIcon",
            "logo",
            "logoDark",
            "screenshots",
        },
        "plugin.json.interface",
        errors,
    )
    display = require_string(interface, "displayName", errors, prefix="plugin.json.interface")
    if display is not None and len(display) > 30:
        errors.append("plugin.json.interface.displayName must be <= 30 characters for directory submission")
    short = require_string(interface, "shortDescription", errors, prefix="plugin.json.interface")
    if short is not None:
        if "\n" in short or len(short) > 30:
            errors.append("plugin.json.interface.shortDescription must be one line and <= 30 characters")
    long = require_string(interface, "longDescription", errors, prefix="plugin.json.interface")
    if long is not None and len(long) > 4000:
        errors.append("plugin.json.interface.longDescription must be <= 4,000 characters")
    developer = require_string(interface, "developerName", errors, prefix="plugin.json.interface")
    if developer is not None and len(developer) > 80:
        errors.append("plugin.json.interface.developerName must be <= 80 characters")
    category = require_string(interface, "category", errors, prefix="plugin.json.interface")
    if category is not None and category not in PUBLIC_CATEGORIES:
        errors.append(f"plugin.json.interface.category must be one of {sorted(PUBLIC_CATEGORIES)}")
    capabilities = interface.get("capabilities")
    if not isinstance(capabilities, list) or not all(isinstance(item, str) and item.strip() for item in capabilities):
        errors.append("plugin.json.interface.capabilities must be a list of strings")
    elif len(capabilities) > 20 or any(len(item) > 120 for item in capabilities):
        errors.append("plugin.json.interface.capabilities must contain <=20 entries of <=120 characters")
    prompts = interface.get("defaultPrompt", interface.get("default_prompt"))
    if not isinstance(prompts, list) or not 1 <= len(prompts) <= 3 or not all(
        isinstance(item, str) and item.strip() and len(item) <= 128 for item in prompts
    ):
        errors.append("plugin.json.interface.defaultPrompt must contain 1-3 strings of <=128 characters")
    color = interface.get("brandColor")
    if color is not None and (not isinstance(color, str) or not HEX_COLOR_RE.fullmatch(color)):
        errors.append("plugin.json.interface.brandColor must be #RRGGBB")
    for field in ("websiteURL", "privacyPolicyURL", "termsOfServiceURL"):
        validate_https(interface.get(field), f"plugin.json.interface.{field}", errors)
    # Both assets are required by the public directory even though local marketplaces can omit them.
    for field in ("composerIcon", "logo"):
        raw = interface.get(field)
        validate_asset(plugin_root, raw, f"plugin.json.interface.{field}", errors)
    for field in ("logoDark",):
        if field in interface and interface[field] is not None:
            validate_asset(plugin_root, interface[field], f"plugin.json.interface.{field}", errors)
    screenshots = interface.get("screenshots", [])
    if not isinstance(screenshots, list):
        errors.append("plugin.json.interface.screenshots must be a list")
    else:
        for index, raw in enumerate(screenshots):
            validate_asset(plugin_root, raw, f"plugin.json.interface.screenshots[{index}]", errors)

    skills_root = plugin_root / "skills"
    if skills_root.is_dir():
        for skill_root in sorted(skills_root.iterdir(), key=lambda path: path.name):
            if skill_root.is_dir() and not skill_root.name.startswith("."):
                validate_skill(skill_root, plugin_root, errors)


def validate_plugin(plugin_root: Path) -> list[str]:
    plugin_root = plugin_root.expanduser().resolve()
    errors: list[str] = []
    manifest = load_json_object(plugin_root / ".codex-plugin" / "plugin.json", "plugin.json", errors)
    if manifest is None:
        return errors
    reject_todos(manifest, "plugin.json", errors)
    validate_manifest(plugin_root, manifest, errors)
    return errors


def main() -> int:
    errors = validate_plugin(Path(parse_args().plugin_path))
    if errors:
        print("Plugin validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Plugin validation passed: manifest, public metadata, assets, and skills are consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
