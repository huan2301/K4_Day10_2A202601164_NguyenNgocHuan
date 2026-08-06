from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize raw records into the canonical embedding-ready dataframe.

    Pseudo-code:
    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates va filter row xau.
    6. Sort dataframe va return.
    """
    rows: list[dict] = []
    run_timestamp = pd.Timestamp(run_date)
    if run_timestamp.tzinfo is None:
        run_timestamp = run_timestamp.tz_localize("UTC")
    else:
        run_timestamp = run_timestamp.tz_convert("UTC")
    for record in records:
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        paper_id = normalize_whitespace(record.paper_id).lower()
        # Required fields: stable DOI, title, abstract and a valid publication date.
        if not paper_id or not title or not summary:
            continue
        published = pd.to_datetime(record.published, errors="coerce", utc=True)
        updated = pd.to_datetime(record.updated, errors="coerce", utc=True)
        if pd.isna(published):
            continue
        authors = list(
            dict.fromkeys(
                normalize_whitespace(str(value))
                for value in record.authors
                if normalize_whitespace(str(value))
            )
        )
        categories = list(
            dict.fromkeys(
                normalize_whitespace(str(value))
                for value in record.categories
                if normalize_whitespace(str(value))
            )
        )
        authors_joined = ", ".join(authors) or "Unknown"
        categories_joined = ", ".join(categories) or "Uncategorized"
        published_date = published.date().isoformat()
        text_for_embedding = "\n".join(
            (
                f"Title: {title}",
                f"Authors: {authors_joined}",
                f"Categories: {categories_joined}",
                f"Published: {published_date}",
                f"Abstract: {summary}",
            )
        )
        rows.append({
            "paper_id": paper_id,
            "title": title,
            "summary": summary,
            "authors": authors,
            "categories": categories,
            "primary_category": normalize_whitespace(record.primary_category) or categories_joined.split(", ")[0],
            "published": published_date,
            "updated": updated.date().isoformat() if not pd.isna(updated) else published_date,
            "age_days": max(0, (run_timestamp.normalize() - published.normalize()).days),
            "authors_joined": authors_joined,
            "categories_joined": categories_joined,
            "summary_chars": len(summary),
            "text_for_embedding": text_for_embedding,
            "abs_url": normalize_whitespace(record.abs_url),
            "pdf_url": normalize_whitespace(record.pdf_url),
            "comment": normalize_whitespace(record.comment),
        })
    columns = [
        "paper_id", "title", "summary", "authors", "categories",
        "primary_category", "published", "updated", "age_days",
        "authors_joined", "categories_joined", "summary_chars",
        "text_for_embedding", "abs_url", "pdf_url", "comment",
    ]
    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        raise ValueError("No valid records remain after cleaning.")
    return df.drop_duplicates(subset=["paper_id"], keep="first").sort_values(
        ["published", "paper_id"], ascending=[False, True]
    ).reset_index(drop=True)
