from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import write_text


_METRIC_KEYS = ("samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")


def _markdown_cell(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _quality_status(quality: dict[str, Any]) -> str:
    return "PASS" if quality.get("passed") else "FAIL"


def _quality_failures(quality: dict[str, Any]) -> str:
    checks = quality.get("checks", {})
    if not isinstance(checks, dict):
        return "No structured checks available."
    failed = [name for name, check in checks.items() if isinstance(check, dict) and not check.get("passed")]
    return ", ".join(failed) if failed else "None"


def _metric_table(metrics_by_state: dict[str, dict[str, Any]]) -> list[str]:
    lines = ["| Metric | " + " | ".join(metrics_by_state) + " |", "|---|" + "|".join("---:" for _ in metrics_by_state) + "|"]
    for key in _METRIC_KEYS:
        lines.append("| " + key + " | " + " | ".join(_markdown_cell(metrics.get(key)) for metrics in metrics_by_state.values()) + " |")
    return lines

def generate_phase1_report(
    report_path: Path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write a baseline report whose values are derived entirely from artifacts."""
    source_lines = [f"- **{_markdown_cell(key)}:** {_markdown_cell(value)}" for key, value in source_summary.items()]
    lines = [
        "# Phase 1 Baseline Report",
        "",
        "## Source",
        *(source_lines or ["- No source summary was supplied."]),
        "",
        "## Evaluation metrics",
        *_metric_table({"Baseline": metrics}),
        "",
        "## Data quality",
        f"- **Status:** {_quality_status(quality)}",
        f"- **Failed checks:** {_quality_failures(quality)}",
        f"- **Rows checked:** {_markdown_cell(quality.get('total_rows'))}",
        "",
        "## Freshness",
        f"- **Status:** {'FRESH' if freshness.get('is_fresh') else 'STALE OR INCOMPLETE'}",
        f"- **Latest published:** {_markdown_cell(freshness.get('latest_published'))}",
        f"- **Oldest published:** {_markdown_cell(freshness.get('oldest_published'))}",
        f"- **Stale rows:** {_markdown_cell(freshness.get('stale_rows'))}",
        f"- **Threshold (days):** {_markdown_cell(freshness.get('freshness_threshold_days'))}",
        "",
    ]
    write_text(Path(report_path), "\n".join(lines))


def generate_corruption_report(
    report_path: Path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    baseline_quality: dict[str, Any] | None = None,
    baseline_freshness: dict[str, Any] | None = None,
) -> None:
    """Write an evidence-based baseline/corrupted/repaired comparison report."""
    metric_states = {"Baseline": baseline_metrics, "Corrupted": corrupted_metrics, "Repaired": repaired_metrics}
    quality_states = {"Baseline": baseline_quality or {}, "Corrupted": corrupted_quality, "Repaired": repaired_quality}
    freshness_states = {"Baseline": baseline_freshness or {}, "Corrupted": corrupted_freshness, "Repaired": repaired_freshness}
    lines = [
        "# Corruption and Recovery Report",
        "",
        "## Evaluation comparison",
        *_metric_table(metric_states),
        "",
        "## Data-quality comparison",
        "| Signal | Baseline | Corrupted | Repaired |",
        "|---|---|---|---|",
        "| Status | " + " | ".join(_quality_status(value) for value in quality_states.values()) + " |",
        "| Failed checks | " + " | ".join(_quality_failures(value) for value in quality_states.values()) + " |",
        "| Rows checked | " + " | ".join(_markdown_cell(value.get('total_rows')) for value in quality_states.values()) + " |",
        "",
        "## Freshness comparison",
        "| Signal | Baseline | Corrupted | Repaired |",
        "|---|---|---|---|",
        "| Fresh | " + " | ".join('Yes' if value.get('is_fresh') else 'No' for value in freshness_states.values()) + " |",
        "| Latest published | " + " | ".join(_markdown_cell(value.get('latest_published')) for value in freshness_states.values()) + " |",
        "| Stale rows | " + " | ".join(_markdown_cell(value.get('stale_rows')) for value in freshness_states.values()) + " |",
        "",
        "## Interpretation",
        "Metrics and quality states above are copied from the corresponding generated artifacts. "
        "Treat recovery as complete only when the repaired evidence supports that conclusion.",
        "",
    ]
    write_text(Path(report_path), "\n".join(lines))
