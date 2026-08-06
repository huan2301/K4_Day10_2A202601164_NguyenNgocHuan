from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


LOGGER = logging.getLogger(__name__)


def _dataframe_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _save_dataset(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    write_csv(df, csv_path)
    write_json(json_path, _dataframe_records(df))


def _load_clean_dataframe(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Baseline clean artifact is required before corruption: {path}")
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Clean artifact must contain a JSON list of records: {path}")
    frame = pd.DataFrame(payload)
    if frame.empty:
        raise ValueError(f"Baseline clean artifact contains no records: {path}")
    return frame


def _require_baseline(settings: Settings) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not settings.paths.baseline_metrics.exists():
        raise FileNotFoundError(
            f"Baseline metrics are required before corruption. Run phase 1 first: {settings.paths.baseline_metrics}"
        )
    if not settings.paths.eval_testset.exists():
        raise FileNotFoundError(
            f"The frozen baseline test set is required before corruption: {settings.paths.eval_testset}"
        )
    metrics = read_json(settings.paths.baseline_metrics)
    if not isinstance(metrics, dict):
        raise ValueError(f"Baseline metrics must be a JSON object: {settings.paths.baseline_metrics}")
    return _load_clean_dataframe(settings.paths.clean_json), metrics


def _frozen_test_document_ids(path: Path) -> set[str]:
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Frozen test set must be a JSON list: {path}")
    document_ids = {
        str(document_id)
        for sample in payload
        if isinstance(sample, dict)
        for document_id in sample.get("ground_truth_doc_ids", [])
        if isinstance(document_id, str) and document_id.strip()
    }
    if not document_ids:
        raise ValueError(f"Frozen test set has no ground_truth_doc_ids to target: {path}")
    return document_ids


def main() -> None:
    """Run corruption, evaluation, raw-snapshot repair, and evidence comparison."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    baseline_df, baseline_metrics = _require_baseline(settings)
    frozen_document_ids = _frozen_test_document_ids(settings.paths.eval_testset)

    corrupted_df = corrupt_clean_dataframe(
        baseline_df,
        settings.paths.corruption_log,
        target_paper_ids=frozen_document_ids,
    )
    if corrupted_df.empty:
        raise RuntimeError("Corruption produced an empty dataset; refusing to evaluate a meaningless comparison.")
    _save_dataset(corrupted_df, settings.paths.corrupted_clean_csv, settings.paths.corrupted_clean_json)
    corrupted_df = pd.read_csv(settings.paths.corrupted_clean_csv)
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings=settings, embeddings_output_path=settings.paths.corrupted_embeddings_json
    )
    corrupted_evaluation = evaluate_pipeline(
        settings,
        corrupted_index,
        settings.paths.eval_testset,
        settings.paths.corrupted_metrics,
        settings.paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, report_name="corrupted_quality")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, settings.paths.quality_dir / "freshness_corrupted.json"
    )

    if not settings.paths.raw_records_json.exists():
        raise FileNotFoundError(f"Raw snapshot required for repair is missing: {settings.paths.raw_records_json}")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, run_date=now_utc())
    if repaired_df.empty:
        raise RuntimeError("Repair cleaning produced an empty dataset.")
    _save_dataset(repaired_df, settings.paths.repaired_clean_csv, settings.paths.repaired_clean_json)
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings=settings, embeddings_output_path=settings.paths.repaired_embeddings_json
    )
    repaired_evaluation = evaluate_pipeline(
        settings,
        repaired_index,
        settings.paths.eval_testset,
        settings.paths.repaired_metrics,
        settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, report_name="repaired_quality")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, settings.paths.quality_dir / "freshness_repaired.json"
    )
    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_evaluation.summary,
        repaired_metrics=repaired_evaluation.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
        baseline_quality=run_data_quality_checks(baseline_df, settings, report_name="baseline_quality"),
        baseline_freshness=build_freshness_report(baseline_df, settings, settings.paths.freshness_report),
    )
    LOGGER.info("Corruption and repair flow completed. Report: %s", settings.paths.comparison_report)
