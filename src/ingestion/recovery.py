from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import read_json, write_json
from ingestion.cleaning import build_and_save_clean_dataset
from ingestion.crossref import load_raw_records


def repair_clean_dataset_from_raw(
    raw_records_path: Path,
    run_date: datetime,
    csv_path: Path,
    json_path: Path,
    cleaning_report_path: Path,
) -> pd.DataFrame:
    """Rebuild repaired clean artifacts only from the trusted raw snapshot."""
    records = load_raw_records(raw_records_path)
    return build_and_save_clean_dataset(
        records,
        run_date,
        csv_path=csv_path,
        json_path=json_path,
        report_path=cleaning_report_path,
    )


def build_recovery_evidence(
    raw_records_path: Path,
    repaired_json_path: Path,
    corruption_log_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Prove that each logged corruption target was restored from raw data."""
    raw_records = read_json(raw_records_path)
    repaired_records = read_json(repaired_json_path)
    corruption_log = read_json(corruption_log_path)
    raw_by_id = {row["paper_id"]: row for row in raw_records}
    repaired_by_id: dict[str, list[dict[str, Any]]] = {}
    for row in repaired_records:
        repaired_by_id.setdefault(row["paper_id"], []).append(row)

    checks: list[dict[str, Any]] = []
    for event in corruption_log.get("events", []):
        kind = event["type"]
        for paper_id in event.get("paper_ids", []):
            raw = raw_by_id.get(paper_id)
            repaired_rows = repaired_by_id.get(paper_id, [])
            repaired = repaired_rows[0] if repaired_rows else None
            passed = raw is not None and repaired is not None and len(repaired_rows) == 1
            details: dict[str, Any] = {"repaired_row_count": len(repaired_rows)}
            if passed and kind == "blank_summary":
                passed = bool(str(repaired["summary"]).strip())
                details["summary_chars"] = len(str(repaired["summary"]))
            elif passed and kind == "inject_embedding_noise":
                passed = "CORRUPTED NOISE" not in str(repaired["text_for_embedding"])
                details["noise_removed"] = passed
            elif passed and kind == "truncate_title":
                passed = repaired["title"] == raw["title"]
                details["title_matches_raw"] = passed
            elif passed and kind == "stale_publication_date":
                passed = repaired["published"] == raw["published"]
                details["published_matches_raw"] = passed
            elif passed and kind == "duplicate_row":
                details["duplicate_removed"] = len(repaired_rows) == 1
            elif passed and kind == "drop_frozen_test_record":
                details["dropped_record_restored"] = True
            checks.append(
                {
                    "corruption_type": kind,
                    "paper_id": paper_id,
                    "passed": passed,
                    **details,
                }
            )

    try:
        recovery_source = str(raw_records_path.resolve().relative_to(Path(output_path).resolve().parents[2]))
    except ValueError:
        recovery_source = raw_records_path.name

    payload = {
        "recovery_source": recovery_source,
        "recovery_source_sha256": hashlib.sha256(raw_records_path.read_bytes()).hexdigest(),
        "raw_record_count": len(raw_records),
        "repaired_record_count": len(repaired_records),
        "all_checks_passed": bool(checks) and all(check["passed"] for check in checks),
        "checks": checks,
    }
    write_json(output_path, payload)
    return payload
