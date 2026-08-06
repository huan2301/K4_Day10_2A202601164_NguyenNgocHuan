from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import safe_slug, write_json


def _series_or_empty(df: pd.DataFrame, name: str) -> pd.Series:
    return df[name] if name in df.columns else pd.Series(index=df.index, dtype="object")


def _nonempty(series: pd.Series) -> pd.Series:
    return series.notna() & series.astype(str).str.strip().ne("")


def _check(passed: bool, observed: Any, expected: str) -> dict[str, Any]:
    return {"passed": bool(passed), "observed": observed, "expected": expected}


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run auditable quality checks and persist their JSON report under ``quality_dir``."""
    paper_ids = _series_or_empty(df, "paper_id")
    titles = _series_or_empty(df, "title")
    summaries = _series_or_empty(df, "summary")
    ages = pd.to_numeric(_series_or_empty(df, "age_days"), errors="coerce")

    nonempty_ids = _nonempty(paper_ids)
    duplicate_ids = int(paper_ids[nonempty_ids].astype(str).duplicated(keep=False).sum())
    nonempty_titles = _nonempty(titles)
    summary_lengths = summaries.fillna("").astype(str).str.strip().str.len()
    valid_summary = summary_lengths.ge(20)
    valid_ages = ages.notna() & ages.ge(0)
    stale_rows = int(ages.gt(settings.freshness_threshold_days).sum())

    checks = {
        "row_count": _check(len(df) > 0, int(len(df)), "at least one record"),
        "required_columns": _check(
            {"paper_id", "title", "summary", "published", "age_days"}.issubset(df.columns),
            sorted(df.columns.tolist()),
            "paper_id, title, summary, published, and age_days are present",
        ),
        "paper_id_not_null": _check(
            bool(nonempty_ids.all()), int((~nonempty_ids).sum()), "zero null or blank paper_id values"
        ),
        "paper_id_unique": _check(duplicate_ids == 0, duplicate_ids, "zero duplicate nonblank paper_id values"),
        "title_not_null": _check(
            bool(nonempty_titles.all()), int((~nonempty_titles).sum()), "zero null or blank title values"
        ),
        "summary_min_length": _check(
            bool(valid_summary.all()), int((~valid_summary).sum()), "every summary has at least 20 characters"
        ),
        "age_days_valid": _check(
            bool(valid_ages.all()), int((~valid_ages).sum()), "every age_days value is a non-negative number"
        ),
        "freshness_threshold": _check(
            stale_rows == 0,
            {"stale_rows": stale_rows, "threshold_days": settings.freshness_threshold_days},
            "zero records older than the configured freshness threshold",
        ),
    }
    result = {
        "report_name": report_name,
        "generated_at": datetime.now(UTC).isoformat(),
        "total_rows": int(len(df)),
        "passed": all(check["passed"] for check in checks.values()),
        "checks": checks,
    }
    output_name = f"{safe_slug(Path(report_name).stem)}.json"
    write_json(settings.paths.quality_dir / output_name, result)
    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path) -> dict[str, Any]:
    """Summarize dataset publication freshness, then write the supplied JSON path."""
    published = pd.to_datetime(_series_or_empty(df, "published"), errors="coerce", utc=True)
    ages = pd.to_numeric(_series_or_empty(df, "age_days"), errors="coerce")
    valid_dates = published.dropna()
    valid_ages = ages.dropna()
    stale_rows = int(ages.gt(settings.freshness_threshold_days).sum())
    invalid_age_rows = int((ages.isna() | ages.lt(0)).sum())

    result = {
        "generated_at": datetime.now(UTC).isoformat(),
        "freshness_threshold_days": settings.freshness_threshold_days,
        "total_rows": int(len(df)),
        "valid_published_rows": int(valid_dates.size),
        "invalid_published_rows": int(len(df) - valid_dates.size),
        "latest_published": valid_dates.max().date().isoformat() if not valid_dates.empty else None,
        "oldest_published": valid_dates.min().date().isoformat() if not valid_dates.empty else None,
        "stale_rows": stale_rows,
        "invalid_age_rows": invalid_age_rows,
        "max_age_days": int(valid_ages.max()) if not valid_ages.empty else None,
        "min_age_days": int(valid_ages.min()) if not valid_ages.empty else None,
        "is_fresh": bool(len(df) > 0 and not valid_dates.empty and invalid_age_rows == 0 and stale_rows == 0),
    }
    write_json(Path(report_path), result)
    return result
