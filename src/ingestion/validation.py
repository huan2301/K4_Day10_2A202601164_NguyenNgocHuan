from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from core.config import load_settings
from core.utils import read_json, write_json
from ingestion.cleaning import build_and_save_clean_dataset
from ingestion.crossref import load_raw_records, parse_crossref_payload


SAMPLE_RUN_DATE = datetime(2026, 8, 6, tzinfo=UTC)


def validate_raw_to_clean(
    sample_payload_path: Path,
    parsed_output_path: Path,
    clean_json_path: Path,
    clean_csv_path: Path,
    cleaning_report_path: Path,
) -> dict[str, int]:
    """Run the deterministic CP1 sample from a Crossref payload to clean artifacts."""
    records = parse_crossref_payload(read_json(sample_payload_path))
    write_json(parsed_output_path, [asdict(record) for record in records])

    # Reload the serialized boundary as a recovery-path contract check.
    reloaded = load_raw_records(parsed_output_path)
    clean_df = build_and_save_clean_dataset(
        reloaded,
        SAMPLE_RUN_DATE,
        csv_path=clean_csv_path,
        json_path=clean_json_path,
        report_path=cleaning_report_path,
    )

    assert len(records) == 3, "Parser must deduplicate the repeated DOI."
    assert len(clean_df) == 2, "Cleaner must reject the missing-abstract record."
    assert clean_df["paper_id"].is_unique
    assert clean_df["paper_id"].notna().all()
    assert clean_df["published"].notna().all()
    assert clean_df["text_for_embedding"].str.len().gt(0).all()
    assert clean_df["age_days"].ge(0).all()

    return {"parsed_records": len(records), "clean_records": len(clean_df)}


def main() -> None:
    paths = load_settings().paths
    result = validate_raw_to_clean(
        sample_payload_path=paths.project_dir / "data" / "raw" / "crossref_sample.json",
        parsed_output_path=paths.project_dir / "data" / "raw" / "crossref_sample_records.json",
        clean_json_path=paths.project_dir / "data" / "clean" / "papers_clean_sample.json",
        clean_csv_path=paths.project_dir / "data" / "clean" / "papers_clean_sample.csv",
        cleaning_report_path=paths.project_dir / "data" / "clean" / "cleaning_report_sample.json",
    )
    print(f"CP1 raw -> clean validation passed: {result}")


if __name__ == "__main__":
    main()
