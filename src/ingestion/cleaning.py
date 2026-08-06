from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import normalize_whitespace, write_csv, write_json
from ingestion.crossref import PaperRecord


def build_clean_dataframe(
    records: list[PaperRecord],
    run_date: datetime,
    report_path: Path | None = None,
) -> pd.DataFrame:
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
    rejected: list[dict[str, Any]] = []
    accepted_ids: set[str] = set()
    reason_counts: Counter[str] = Counter()
    run_timestamp = pd.Timestamp(run_date)
    if run_timestamp.tzinfo is None:
        run_timestamp = run_timestamp.tz_localize("UTC")
    else:
        run_timestamp = run_timestamp.tz_convert("UTC")
    def reject(source_index: int, paper_id: str, reason: str) -> None:
        reason_counts[reason] += 1
        rejected.append(
            {
                "source_index": source_index,
                "paper_id": paper_id or None,
                "reason": reason,
            }
        )

    for source_index, record in enumerate(records):
        title = normalize_whitespace(str(record.title or ""))
        summary = normalize_whitespace(str(record.summary or ""))
        paper_id = normalize_whitespace(str(record.paper_id or "")).lower()
        # Required fields: stable DOI, title, abstract and a valid publication date.
        if not paper_id:
            reject(source_index, paper_id, "missing_paper_id")
            continue
        if not title:
            reject(source_index, paper_id, "missing_title")
            continue
        if not summary:
            reject(source_index, paper_id, "missing_summary")
            continue
        published = pd.to_datetime(record.published, errors="coerce", utc=True)
        updated = pd.to_datetime(record.updated, errors="coerce", utc=True)
        if pd.isna(published):
            reject(source_index, paper_id, "invalid_published")
            continue
        if paper_id in accepted_ids:
            reject(source_index, paper_id, "duplicate_paper_id")
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
            "primary_category": normalize_whitespace(str(record.primary_category or "")) or categories_joined.split(", ")[0],
            "published": published_date,
            "updated": updated.date().isoformat() if not pd.isna(updated) else published_date,
            "age_days": max(0, (run_timestamp.normalize() - published.normalize()).days),
            "authors_joined": authors_joined,
            "categories_joined": categories_joined,
            "summary_chars": len(summary),
            "text_for_embedding": text_for_embedding,
            "abs_url": normalize_whitespace(str(record.abs_url or "")),
            "pdf_url": normalize_whitespace(str(record.pdf_url or "")),
            "comment": normalize_whitespace(str(record.comment or "")),
        })
        accepted_ids.add(paper_id)
    columns = [
        "paper_id", "title", "summary", "authors", "categories",
        "primary_category", "published", "updated", "age_days",
        "authors_joined", "categories_joined", "summary_chars",
        "text_for_embedding", "abs_url", "pdf_url", "comment",
    ]
    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        raise ValueError("No valid records remain after cleaning.")
    df = df.sort_values(
        ["published", "paper_id"], ascending=[False, True]
    ).reset_index(drop=True)
    report = {
        "input_records": len(records),
        "output_records": len(df),
        "filtered_records": len(rejected),
        "reason_counts": dict(sorted(reason_counts.items())),
        "rejected_records": rejected,
        "run_date_utc": run_timestamp.isoformat(),
        "required_fields": ["paper_id", "title", "summary", "published"],
        "dedupe_key": "paper_id",
    }
    df.attrs["cleaning_report"] = report
    if report_path is not None:
        write_json(report_path, report)
    return df


def build_and_save_clean_dataset(
    records: list[PaperRecord],
    run_date: datetime,
    csv_path: Path,
    json_path: Path,
    report_path: Path,
) -> pd.DataFrame:
    """Build the canonical dataframe and persist its CSV, JSON and audit report."""
    df = build_clean_dataframe(records, run_date, report_path=report_path)
    write_csv(df, csv_path)
    write_json(json_path, df.to_dict(orient="records"))
    return df
