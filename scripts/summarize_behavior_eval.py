#!/usr/bin/env python3
"""Compute paired descriptive statistics from reviewed behavior scores."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


METRICS = ("outcome", "evidence", "scope", "verification", "friction")
CONDITIONS = frozenset(("baseline", "treatment"))
COMPARISON_SETTING_KEYS = (
    "requested_model",
    "use_user_config",
    "disabled_features",
    "skill_sha256",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize paired baseline/treatment scores.")
    parser.add_argument("scores", type=Path, help="JSON file with results carrying a scores object")
    return parser.parse_args()


def two_sided_sign_p(wins: int, losses: int) -> float | None:
    usable = wins + losses
    if usable == 0:
        return None
    tail = sum(math.comb(usable, index) for index in range(max(wins, losses), usable + 1))
    return min(1.0, 2.0 * tail / (2**usable))


def collect_scores(
    rows: list[Any],
) -> tuple[dict[str, dict[str, dict[str, float]]], list[str], dict[str, int]]:
    """Validate reviewer scores without turning missing evidence into zeros."""

    paired: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    errors: list[str] = []
    unscored = {condition: 0 for condition in CONDITIONS}
    seen_rows: set[tuple[str, str]] = set()
    comparison_settings: dict[str, dict[str, str]] = defaultdict(dict)
    for index, row in enumerate(rows):
        label = f"results[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label} must be an object")
            continue
        condition = row.get("condition")
        case_id = row.get("id")
        if condition not in CONDITIONS:
            errors.append(f"{label}.condition must be baseline or treatment")
            continue
        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(f"{label}.id must be a non-empty string")
            continue
        row_key = (case_id, condition)
        if row_key in seen_rows:
            errors.append(f"duplicate score row for {case_id!r} / {condition}")
            continue
        seen_rows.add(row_key)
        fingerprint = row.get("experiment_fingerprint")
        if not isinstance(fingerprint, str) or len(fingerprint) != 64:
            errors.append(f"{label}.experiment_fingerprint must be a SHA-256 string")
            continue
        settings = row.get("experiment_settings")
        if settings is None:
            comparison_settings[case_id][condition] = fingerprint
        elif not isinstance(settings, dict):
            errors.append(f"{label}.experiment_settings must be an object")
            continue
        else:
            missing_settings = set(COMPARISON_SETTING_KEYS) - set(settings)
            if missing_settings:
                errors.append(
                    f"{label}.experiment_settings is missing comparison keys: {sorted(missing_settings)}"
                )
                continue
            comparable = {key: settings[key] for key in COMPARISON_SETTING_KEYS}
            comparison_settings[case_id][condition] = json.dumps(
                comparable, sort_keys=True, separators=(",", ":")
            )
        scores = row.get("scores")
        if scores is None:
            unscored[condition] += 1
            continue
        if row.get("completion_state") != "completed" or row.get("exit_code") != 0:
            errors.append(
                f"{label} cannot be scored unless completion_state is completed and exit_code is 0"
            )
            continue
        if not isinstance(scores, dict):
            errors.append(f"{label}.scores must be an object")
            continue
        missing = set(METRICS) - set(scores)
        extra = set(scores) - set(METRICS)
        if missing:
            errors.append(f"{label}.scores is missing metrics: {sorted(missing)}")
        if extra:
            errors.append(f"{label}.scores has unsupported metrics: {sorted(extra)}")
        normalized: dict[str, float] = {}
        for metric in METRICS:
            value = scores.get(metric)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                errors.append(f"{label}.scores.{metric} must be a number from 0 to 4")
                continue
            numeric = float(value)
            if not math.isfinite(numeric) or not 0 <= numeric <= 4:
                errors.append(f"{label}.scores.{metric} must be a number from 0 to 4")
                continue
            normalized[metric] = numeric
        if len(normalized) != len(METRICS) or missing or extra:
            continue
        paired[case_id][condition] = normalized
    for case_id, pair in comparison_settings.items():
        if CONDITIONS <= set(pair) and len(set(pair.values())) != 1:
            errors.append(f"experiment settings differ for paired case {case_id!r}")
    return paired, errors, unscored


def main() -> int:
    args = parse_args()
    try:
        payload = json.loads(args.scores.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    rows = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        print("scores JSON must contain a results array", file=sys.stderr)
        return 2
    paired, errors, unscored = collect_scores(rows)
    if errors:
        print("Invalid behavior score data:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2
    complete_pairs = {
        case_id: pair
        for case_id, pair in paired.items()
        if CONDITIONS <= set(pair)
    }
    incomplete = sorted(case_id for case_id, pair in paired.items() if CONDITIONS > set(pair))
    print(f"Scored paired cases: {len(complete_pairs)}")
    print(
        "Unscored raw rows: "
        f"baseline={unscored['baseline']}, treatment={unscored['treatment']}"
    )
    if incomplete:
        print(f"Incomplete scored pairs (excluded): {', '.join(incomplete)}")
    for metric in METRICS:
        deltas: list[float] = []
        wins = losses = ties = 0
        for pair in complete_pairs.values():
            delta = pair["treatment"][metric] - pair["baseline"][metric]
            deltas.append(delta)
            if delta > 0:
                wins += 1
            elif delta < 0:
                losses += 1
            else:
                ties += 1
        if not deltas:
            print(f"{metric}: no complete scores")
            continue
        print(
            f"{metric}: mean_delta={statistics.mean(deltas):+.2f}, "
            f"median_delta={statistics.median(deltas):+.2f}, wins={wins}, ties={ties}, losses={losses}, "
            f"two_sided_sign_p={two_sided_sign_p(wins, losses)}"
        )
    print("Interpretation: descriptive paired evidence only; do not generalize from a small or model-dependent sample.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
