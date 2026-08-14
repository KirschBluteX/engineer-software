#!/usr/bin/env python3
"""Compute paired descriptive statistics from reviewed behavior scores."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime
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
    parser.add_argument(
        "--max-median-slowdown-percent",
        type=float,
        help="optionally fail when treatment median wall time exceeds baseline by this percent",
    )
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


def collect_durations(rows: list[Any]) -> tuple[dict[str, dict[str, float]], list[str]]:
    """Collect completed wall times without treating missing timing as a score failure."""

    durations: dict[str, dict[str, float]] = defaultdict(dict)
    errors: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("completion_state") != "completed" or row.get("exit_code") != 0:
            continue
        started = row.get("started_at")
        finished = row.get("finished_at")
        if started is None and finished is None:
            continue
        label = f"results[{index}]"
        if not isinstance(started, str) or not isinstance(finished, str):
            errors.append(f"{label} must have ISO started_at and finished_at strings")
            continue
        try:
            elapsed = (datetime.fromisoformat(finished) - datetime.fromisoformat(started)).total_seconds()
        except (TypeError, ValueError):
            errors.append(f"{label} has invalid ISO timing")
            continue
        if elapsed < 0:
            errors.append(f"{label} has negative elapsed time")
            continue
        case_id = row.get("id")
        condition = row.get("condition")
        if isinstance(case_id, str) and condition in CONDITIONS:
            durations[case_id][condition] = elapsed
    return durations, errors


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
    durations, timing_errors = collect_durations(rows)
    errors.extend(timing_errors)
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
    timed_pairs = {
        case_id: pair for case_id, pair in durations.items() if CONDITIONS <= set(pair)
    }
    if timed_pairs:
        baseline_times = [pair["baseline"] for pair in timed_pairs.values()]
        treatment_times = [pair["treatment"] for pair in timed_pairs.values()]
        baseline_median = statistics.median(baseline_times)
        treatment_median = statistics.median(treatment_times)
        median_delta = treatment_median - baseline_median
        median_percent = (median_delta / baseline_median * 100) if baseline_median else None
        median_percent_text = f"{median_percent:+.1f}%" if median_percent is not None else "n/a"
        print(
            f"Timed paired cases: {len(timed_pairs)}; "
            f"baseline_total={sum(baseline_times):.1f}s, treatment_total={sum(treatment_times):.1f}s"
        )
        print(
            f"Median wall time: baseline={baseline_median:.1f}s, treatment={treatment_median:.1f}s, "
            f"delta={median_delta:+.1f}s "
            f"({median_percent_text})"
        )
        for case_id in sorted(timed_pairs):
            pair = timed_pairs[case_id]
            print(
                f"- {case_id}: baseline={pair['baseline']:.1f}s, "
                f"treatment={pair['treatment']:.1f}s, "
                f"delta={pair['treatment'] - pair['baseline']:+.1f}s"
            )
    if args.max_median_slowdown_percent is not None:
        threshold = args.max_median_slowdown_percent
        if not math.isfinite(threshold) or threshold < 0:
            print("--max-median-slowdown-percent must be a finite non-negative number", file=sys.stderr)
            return 2
        if not timed_pairs:
            print("latency gate requires at least one complete timed pair", file=sys.stderr)
            return 2
        if baseline_median == 0:
            print("latency gate cannot use a zero baseline median", file=sys.stderr)
            return 2
        if median_percent > threshold:
            print(
                f"Latency gate failed: median slowdown {median_percent:.1f}% exceeds {threshold:.1f}%",
                file=sys.stderr,
            )
            return 1
        print(f"Latency gate passed: median slowdown {median_percent:.1f}% <= {threshold:.1f}%")
    print("Interpretation: descriptive paired evidence only; do not generalize from a small or model-dependent sample.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
