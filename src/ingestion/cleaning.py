from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def _text(value: Any) -> str:
    return normalize_whitespace(value) if isinstance(value, str) else ""


def _unique_texts(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        normalized = _text(value)
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _date(value: str) -> str | None:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return parsed.date().isoformat() if not pd.isna(parsed) else None


def _embedding_text(title: str, summary: str, authors: str, categories: str) -> str:
    segments = [f"Title: {title}", f"Abstract: {summary}"]
    if authors:
        segments.append(f"Authors: {authors}")
    if categories:
        segments.append(f"Categories: {categories}")
    return "\n".join(segments)


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize raw Crossref records into the schema consumed by retrieval and quality checks."""
    if run_date.tzinfo is None:
        raise ValueError("run_date must be timezone-aware so age_days is reproducible.")
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    run_day = run_date.date()

    for record in records:
        paper_id = _text(record.paper_id).lower()
        title = _text(record.title)
        summary = _text(record.summary)
        published = _date(record.published)
        if not paper_id or not title or len(summary) < 20 or not published or paper_id in seen_ids:
            continue
        authors = _unique_texts(record.authors)
        categories = _unique_texts(record.categories)
        published_day = pd.Timestamp(published).date()
        age_days = max(0, (run_day - published_day).days)
        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": _text(record.primary_category) or (categories[0] if categories else ""),
                "published": published,
                "updated": _date(record.updated) or "",
                "abs_url": _text(record.abs_url),
                "pdf_url": _text(record.pdf_url),
                "comment": _text(record.comment),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "text_for_embedding": _embedding_text(title, summary, authors_joined, categories_joined),
                "age_days": age_days,
            }
        )
        seen_ids.add(paper_id)

    columns = [
        "paper_id", "title", "summary", "authors", "categories", "primary_category", "published", "updated", "abs_url",
        "pdf_url", "comment", "authors_joined", "categories_joined", "summary_chars", "text_for_embedding", "age_days",
    ]
    frame = pd.DataFrame(rows, columns=columns)
    if frame.empty:
        return frame
    return frame.sort_values(["published", "paper_id"], ascending=[False, True], kind="stable").reset_index(drop=True)
