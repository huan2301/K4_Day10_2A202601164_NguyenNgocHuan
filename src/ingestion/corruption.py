from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from collections.abc import Collection
from typing import Any

import pandas as pd

from core.utils import write_json
from ingestion.cleaning import build_embedding_text


def _rebuild_embedding_text(df: pd.DataFrame) -> None:
    df["summary_chars"] = df["summary"].fillna("").astype(str).str.len()
    df["text_for_embedding"] = df.apply(
        lambda row: build_embedding_text(
            row["title"],
            row["authors_joined"],
            row["categories_joined"],
            row["published"],
            row["summary"],
        ),
        axis=1,
    )


def _event(
    kind: str,
    paper_ids: list[str],
    before_row_count: int,
    after_row_count: int,
    **details: Any,
) -> dict[str, Any]:
    return {
        "type": kind,
        "paper_ids": paper_ids,
        "before_row_count": before_row_count,
        "after_row_count": after_row_count,
        **details,
    }


def _target_indices(df: pd.DataFrame, target_paper_ids: Collection[str] | None) -> list[int]:
    if not target_paper_ids:
        return list(range(len(df)))
    targets = {str(paper_id).strip().lower() for paper_id in target_paper_ids if str(paper_id).strip()}
    indices = [index for index, paper_id in enumerate(df["paper_id"].astype(str)) if paper_id.lower() in targets]
    if not indices:
        raise ValueError("None of the frozen test-set document IDs occur in the clean dataset.")
    return indices


def corrupt_clean_dataframe(
    df: pd.DataFrame,
    output_log_path: Path,
    target_paper_ids: Collection[str] | None = None,
) -> pd.DataFrame:
    """Create deterministic, traceable data defects without mutating the baseline dataframe."""
    required = {"paper_id", "title", "summary", "published", "authors_joined", "categories_joined"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Cannot corrupt a clean dataset missing columns: {', '.join(missing)}")
    if df.empty:
        raise ValueError("Cannot corrupt an empty clean dataset.")

    working = df.copy(deep=True).reset_index(drop=True)
    working["_published_sort"] = pd.to_datetime(working["published"], errors="coerce", utc=True)
    working = working.sort_values(["_published_sort", "paper_id"], ascending=[False, True], na_position="last", kind="stable").reset_index(drop=True)
    events: list[dict[str, Any]] = []
    before_count = len(working)
    targets = _target_indices(working, target_paper_ids)

    if len(working) >= 3 and targets:
        drop_index = targets[0]
        dropped_id = str(working.at[drop_index, "paper_id"])
        event_before = len(working)
        working = working.drop(index=drop_index).reset_index(drop=True)
        events.append(_event(
            "drop_frozen_test_record", [dropped_id], event_before, len(working),
            count=1, targeted_frozen_test_set=True,
        ))
        targets = _target_indices(working, target_paper_ids)

    if targets:
        blank_index = targets[0]
        paper_id = str(working.at[blank_index, "paper_id"])
        original_length = len(str(working.at[blank_index, "summary"]))
        working.at[blank_index, "summary"] = ""
        events.append(_event(
            "blank_summary", [paper_id], len(working), len(working),
            before_summary_chars=original_length, after_summary_chars=0,
            targeted_frozen_test_set=True,
        ))

    if len(targets) >= 2:
        noise_index = targets[1]
        paper_id = str(working.at[noise_index, "paper_id"])
        noise = " [CORRUPTED NOISE: irrelevant tokens ### 0000]"
        working.at[noise_index, "_embedding_noise"] = noise
        events.append(_event(
            "inject_embedding_noise", [paper_id], len(working), len(working),
            noise=noise.strip(), targeted_frozen_test_set=True,
        ))

    if len(targets) >= 3:
        truncate_index = targets[2]
        paper_id = str(working.at[truncate_index, "paper_id"])
        original = str(working.at[truncate_index, "title"])
        working.at[truncate_index, "title"] = original[: max(1, min(24, len(original) // 2))]
        events.append(_event(
            "truncate_title", [paper_id], len(working), len(working),
            before=original, after=str(working.at[truncate_index, "title"]),
            targeted_frozen_test_set=True,
        ))

    if targets:
        stale_index = targets[-1]
        paper_id = str(working.at[stale_index, "paper_id"])
        original_date = str(working.at[stale_index, "published"])
        stale_date = "2000-01-01"
        working.at[stale_index, "published"] = stale_date
        working.at[stale_index, "age_days"] = (datetime.now(UTC).date() - datetime(2000, 1, 1).date()).days
        events.append(_event(
            "stale_publication_date", [paper_id], len(working), len(working),
            before_published=original_date, after_published=stale_date,
            age_days=int(working.at[stale_index, "age_days"]),
            targeted_frozen_test_set=True,
        ))

    if targets:
        duplicate = working.iloc[[targets[0]]].copy()
        duplicate_id = str(duplicate.iloc[0]["paper_id"])
        event_before = len(working)
        working = pd.concat([working, duplicate], ignore_index=True)
        events.append(_event(
            "duplicate_row", [duplicate_id], event_before, len(working),
            count=1, targeted_frozen_test_set=True,
        ))

    working = working.drop(columns=["_published_sort"], errors="ignore")
    _rebuild_embedding_text(working)
    if "_embedding_noise" in working.columns:
        working["text_for_embedding"] = working["text_for_embedding"] + working["_embedding_noise"].fillna("")
        working = working.drop(columns=["_embedding_noise"])
    log = {
        "generated_at": datetime.now(UTC).isoformat(),
        "before_row_count": before_count,
        "after_row_count": int(len(working)),
        "events": events,
    }
    write_json(Path(output_log_path), log)
    return working.reset_index(drop=True)
