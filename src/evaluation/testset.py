from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json


_REQUIRED_COLUMNS = {
    "paper_id",
    "title",
    "summary",
    "authors_joined",
    "categories_joined",
    "published",
}


def _as_text(value: Any) -> str:
    """Return a normalized string while treating pandas missing values as empty."""
    if value is None or pd.isna(value):
        return ""
    return normalize_whitespace(str(value))


def _validate_input(df: pd.DataFrame) -> None:
    missing = sorted(_REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(f"Clean dataset is missing required test-set columns: {', '.join(missing)}.")
    if df.empty:
        raise ValueError("Cannot build an evaluation test set from an empty clean dataset.")


def _append_sample(
    samples: list[dict[str, Any]],
    *,
    paper_id: str,
    question_type: str,
    question: str,
    ground_truth: str,
) -> None:
    if not ground_truth:
        return
    samples.append(
        {
            "id": f"{paper_id}::{question_type}",
            "question_type": question_type,
            "question": question,
            "ground_truth": ground_truth,
            "ground_truth_doc_ids": [paper_id],
        }
    )


def build_test_set(df: pd.DataFrame, output_path: Path) -> list[dict[str, Any]]:
    """Build a deterministic, corpus-grounded evaluation set and save it as JSON.

    Each question quotes its source title so the exact-title lookup path can be
    evaluated independently of semantic retrieval.  The selected documents are
    deterministic: publication date (then paper ID) provides a stable ordering.
    """
    _validate_input(df)

    candidates = df.copy()
    candidates["_paper_id"] = candidates["paper_id"].map(_as_text)
    candidates["_title"] = candidates["title"].map(_as_text)
    candidates["_summary"] = candidates["summary"].map(_as_text)
    candidates = candidates[(candidates["_paper_id"] != "") & (candidates["_title"] != "")]
    candidates = candidates.drop_duplicates(subset="_paper_id", keep="first")
    if candidates.empty:
        raise ValueError("No clean records with both paper_id and title are available for evaluation.")

    candidates["_published"] = pd.to_datetime(candidates["published"], errors="coerce", utc=True)
    candidates = candidates.sort_values(
        ["_published", "_paper_id"], ascending=[False, True], na_position="last", kind="stable"
    ).head(6)

    samples: list[dict[str, Any]] = []
    for row in candidates.to_dict(orient="records"):
        paper_id = row["_paper_id"]
        title = row["_title"]
        summary = row["_summary"]
        authors = _as_text(row["authors_joined"])
        published = _as_text(row["published"])
        categories = _as_text(row["categories_joined"])

        _append_sample(
            samples,
            paper_id=paper_id,
            question_type="summary",
            question=f"What is the main contribution of '{title}'?",
            ground_truth=first_sentence(summary),
        )
        _append_sample(
            samples,
            paper_id=paper_id,
            question_type="authors",
            question=f"Who authored '{title}'?",
            ground_truth=authors,
        )
        _append_sample(
            samples,
            paper_id=paper_id,
            question_type="date",
            question=f"When was '{title}' published?",
            ground_truth=published,
        )
        _append_sample(
            samples,
            paper_id=paper_id,
            question_type="categories",
            question=f"What categories are assigned to '{title}'?",
            ground_truth=categories,
        )

    if not samples:
        raise ValueError("No answerable evaluation samples could be derived from the clean dataset.")
    write_json(Path(output_path), samples)
    return samples
