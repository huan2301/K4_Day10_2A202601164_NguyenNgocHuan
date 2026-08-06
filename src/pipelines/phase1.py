from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import PaperRecord, fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


LOGGER = logging.getLogger(__name__)


def _dataframe_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a dataframe to JSON-safe records without losing ISO date values."""
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _save_clean_dataset(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    write_csv(df, csv_path)
    write_json(json_path, _dataframe_records(df))


def _load_or_fetch_records(settings: Settings) -> list[PaperRecord]:
    if settings.paths.raw_records_json.exists() and not settings.refresh_source:
        LOGGER.info("Loading raw-record snapshot from %s", settings.paths.raw_records_json)
        return load_raw_records(settings.paths.raw_records_json)
    LOGGER.info("Fetching a fresh Crossref snapshot")
    return fetch_source_records(settings)


def _source_summary(settings: Settings, records: list[PaperRecord], clean_df: pd.DataFrame) -> dict[str, Any]:
    return {
        "source": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "requested_max_results": settings.max_results,
        "raw_record_count": len(records),
        "clean_record_count": int(len(clean_df)),
        "raw_response_path": str(settings.paths.raw_api_response),
        "raw_records_path": str(settings.paths.raw_records_json),
    }


def _write_demo_answers(df: pd.DataFrame, settings: Settings, index: LocalEmbeddingIndex) -> None:
    """Persist deterministic, no-LLM retrieval demos for release verification."""
    if df.empty or "title" not in df.columns:
        write_json(settings.paths.demo_answers, [])
        return

    questions = [f"What is the main contribution of '{str(title)}'?" for title in df["title"].head(2)]
    demos: list[dict[str, Any]] = []
    for question in questions:
        result = answer_question(question, settings=settings, index=index)
        demos.append(
            {
                "question": result.question,
                "answer": result.answer,
                "retrieved_doc_ids": result.retrieved_doc_ids,
                "retrieved_titles": result.retrieved_titles,
            }
        )
    write_json(settings.paths.demo_answers, demos)


def main() -> None:
    """Run the reproducible baseline flow from raw snapshot to evidence report."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    records = _load_or_fetch_records(settings)
    if not records:
        raise RuntimeError("Ingestion returned no raw records; refusing to build an empty baseline.")

    clean_df = build_clean_dataframe(records, run_date=now_utc())
    if clean_df.empty:
        raise RuntimeError("Cleaning removed every raw record; refusing to build an empty baseline.")
    _save_clean_dataset(clean_df, settings.paths.clean_csv, settings.paths.clean_json)

    index = LocalEmbeddingIndex.build(clean_df, settings=settings)
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        build_test_set(clean_df, settings.paths.eval_testset)
    else:
        LOGGER.info("Reusing frozen evaluation set from %s", settings.paths.eval_testset)

    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    quality = run_data_quality_checks(clean_df, settings, report_name="baseline_quality")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary=_source_summary(settings, records, clean_df),
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )
    _write_demo_answers(clean_df, settings, index)
    LOGGER.info("Baseline pipeline completed. Report: %s", settings.paths.baseline_report)
