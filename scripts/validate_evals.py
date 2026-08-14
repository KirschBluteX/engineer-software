#!/usr/bin/env python3
"""Validate structured routing and public-submission test cases."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROUTES = {
    "shape-work",
    "trace-failure",
    "probe-choice",
    "deliver-change",
    "inspect-structure",
    "manage-work-items",
}
MODES = {"direct", "indirect", "follow-up", "boundary", "negative"}
POLARITIES = {"positive", "negative"}
EXPECTED_TRANSITIONS = {
    "shape-work": {"trace-failure", "probe-choice", "deliver-change", "manage-work-items"},
    "trace-failure": {"shape-work", "deliver-change"},
    "probe-choice": {"shape-work", "trace-failure", "deliver-change"},
    "deliver-change": {"shape-work", "trace-failure", "inspect-structure"},
    "inspect-structure": {"shape-work", "deliver-change"},
    "manage-work-items": {"deliver-change"},
}
REQUIRED_FIELDS = {
    "id",
    "polarity",
    "mode",
    "prompt",
    "route",
    "allowed_next",
    "expected_behavior",
    "expected_result",
    "fixture",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Engineer Software routing cases.")
    parser.add_argument(
        "cases",
        nargs="?",
        default="evals/routing-cases.json",
        help="Path to the routing case JSON array",
    )
    parser.add_argument(
        "--references",
        default="plugins/engineer-software/skills/engineer-software/references",
        help="Directory containing route reference modules",
    )
    return parser.parse_args()


def load_cases(path: Path, errors: list[str]) -> list[Any]:
    if not path.is_file():
        errors.append(f"routing case file is missing: {path}")
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        errors.append("routing case file must contain valid UTF-8 JSON")
        return []
    if not isinstance(value, list):
        errors.append("routing case file must contain a JSON array")
        return []
    return value


def non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_cases(cases: list[Any], reference_dir: Path | None = None) -> list[str]:
    errors: list[str] = []
    ids: list[str] = []
    routes: list[str] = []
    polarities: list[str] = []
    modes: list[str] = []
    observed_transitions: dict[str, set[str]] = {route: set() for route in ROUTES}

    if not cases:
        return ["routing cases must be a non-empty array"]

    for index, case in enumerate(cases):
        label = f"case[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{label} must be an object")
            continue
        missing = REQUIRED_FIELDS - set(case)
        extra = set(case) - REQUIRED_FIELDS
        if missing:
            errors.append(f"{label} is missing fields: {sorted(missing)}")
        if extra:
            errors.append(f"{label} has unsupported fields: {sorted(extra)}")
        case_id = case.get("id")
        if not non_empty_string(case_id) or re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", case_id) is None:
            errors.append(f"{label}.id must be unique kebab-case")
            case_id = f"index-{index}"
        ids.append(case_id)
        route = case.get("route")
        if route not in ROUTES | {"bypass"}:
            errors.append(f"{label}.route is unknown: {route!r}")
        else:
            routes.append(route)
        polarity = case.get("polarity")
        if polarity not in POLARITIES:
            errors.append(f"{label}.polarity must be positive or negative")
        else:
            polarities.append(polarity)
        mode = case.get("mode")
        if mode not in MODES:
            errors.append(f"{label}.mode is unknown: {mode!r}")
        else:
            modes.append(mode)
        if polarity == "negative" and route != "bypass":
            errors.append(f"{label} negative cases must exercise the bypass boundary")
        if polarity == "positive" and route == "bypass":
            errors.append(f"{label} positive cases must select a workflow module")
        if mode == "negative" and polarity != "negative":
            errors.append(f"{label} negative mode must have negative polarity")
        if polarity == "negative" and mode != "negative":
            errors.append(f"{label} negative polarity must use negative mode")
        for field in ("prompt", "expected_behavior", "expected_result", "fixture"):
            if not non_empty_string(case.get(field)):
                errors.append(f"{label}.{field} must be a non-empty string")
        allowed = case.get("allowed_next")
        if not isinstance(allowed, list) or any(next_route not in ROUTES for next_route in allowed):
            errors.append(f"{label}.allowed_next must contain only workflow modules")
            continue
        if len(allowed) != len(set(allowed)):
            errors.append(f"{label}.allowed_next must not contain duplicates")
        if route == "bypass" and allowed:
            errors.append(f"{label} bypass cases cannot transition")
        if route in ROUTES:
            if route in allowed:
                errors.append(f"{label} cannot transition to the same module")
            unexpected = set(allowed) - EXPECTED_TRANSITIONS[route]
            if unexpected:
                errors.append(f"{label} declares unsupported transitions: {sorted(unexpected)}")
            observed_transitions[route].update(allowed)

    if len(ids) != len(set(ids)):
        errors.append("routing case ids must be unique")
    counts = Counter(routes)
    for route in ROUTES:
        if counts[route] < 2:
            errors.append(f"route {route} needs at least two cases")
    if counts["bypass"] < 3:
        errors.append("bypass needs at least three negative cases")
    polarity_counts = Counter(polarities)
    if polarity_counts["positive"] < 5:
        errors.append("public submission needs at least five positive cases")
    if polarity_counts["negative"] < 3:
        errors.append("public submission needs at least three negative cases")
    for mode in MODES:
        if mode not in modes:
            errors.append(f"routing suite needs at least one {mode} case")
    for route, expected in EXPECTED_TRANSITIONS.items():
        missing_edges = expected - observed_transitions[route]
        if missing_edges:
            errors.append(f"route {route} lacks transition coverage for {sorted(missing_edges)}")

    if reference_dir is not None:
        for route, expected in EXPECTED_TRANSITIONS.items():
            path = reference_dir / f"{route}.md"
            if not path.is_file():
                errors.append(f"missing route reference: {path}")
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if "## Exit" not in text:
                errors.append(f"{path.name} lacks an Exit section")
                continue
            exit_text = text.split("## Exit", maxsplit=1)[1]
            for next_route in expected:
                if f"`{next_route}`" not in exit_text:
                    errors.append(f"{path.name} Exit does not document transition to {next_route}")

    return errors


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    cases = load_cases(Path(args.cases), errors)
    errors.extend(validate_cases(cases, Path(args.references)))
    if errors:
        print("Routing evaluation validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    counts = Counter(case["polarity"] for case in cases)
    print(
        "Routing evaluation validation passed: "
        f"{len(cases)} cases ({counts['positive']} positive, {counts['negative']} negative)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
