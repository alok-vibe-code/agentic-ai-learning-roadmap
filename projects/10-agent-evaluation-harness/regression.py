"""Versioned metric-floor regression checks."""

from __future__ import annotations
import json
from pathlib import Path

DEFAULT_BASELINE_PATH = Path(__file__).resolve().parent / "data" / "baseline.json"


def load_baseline(path: str | Path | None = None) -> dict:
    baseline_path = Path(path) if path else DEFAULT_BASELINE_PATH
    data = json.loads(baseline_path.read_text(encoding="utf-8"))

    if "metric_floors" not in data or "metric_ceilings" not in data:
        raise ValueError("Baseline requires metric_floors and metric_ceilings.")
    return data


def check_regression(metrics: dict[str, float], baseline: dict) -> tuple[bool, tuple[str, ...]]:
    failures: list[str] = []

    for name, floor in baseline.get("metric_floors", {}).items():
        observed = metrics.get(name)
        if observed is None:
            failures.append(f"missing metric: {name}")
        elif observed < float(floor):
            failures.append(
                f"{name}: observed {observed} < required floor {floor}"
            )

    for name, ceiling in baseline.get("metric_ceilings", {}).items():
        observed = metrics.get(name)
        if observed is None:
            failures.append(f"missing metric: {name}")
        elif observed > float(ceiling):
            failures.append(
                f"{name}: observed {observed} > allowed ceiling {ceiling}"
            )

    return not failures, tuple(failures)
