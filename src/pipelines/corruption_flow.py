from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex

def _records_for_json(df: pd.DataFrame) -> list[dict]:
    """Chuyển DataFrame sang dữ liệu JSON an toàn."""
    safe_df = df.copy()

    for column in safe_df.columns:
        if pd.api.types.is_datetime64_any_dtype(safe_df[column]):
            safe_df[column] = safe_df[column].dt.strftime("%Y-%m-%d")

    safe_df = safe_df.where(pd.notna(safe_df), None)
    return safe_df.to_dict(orient="records")


def _require_baseline_artifacts(paths) -> None:
    required_paths = [
        paths.raw_records_json,
        paths.clean_csv,
        paths.eval_testset,
        paths.baseline_metrics,
    ]

    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise RuntimeError(
            "Baseline artifacts are missing. Run script/run_phase1.py first.\n"
            + "\n".join(f"- {path}" for path in missing)
        )


def main() -> None:
    settings = load_settings()
    paths = settings.paths

    print("=== Phase 2: Corruption, repair, and comparison ===")

    # 1. Không được chạy nếu baseline chưa hoàn chỉnh.
    _require_baseline_artifacts(paths)

    baseline_df = pd.read_csv(paths.clean_csv)
    baseline_metrics = read_json(paths.baseline_metrics)

    if baseline_df.empty:
        raise RuntimeError("Baseline clean dataset is empty.")

    print(f"Baseline clean rows: {len(baseline_df)}")

    # 2. Corrupt baseline clean data.
    # Hàm này do owner ingestion/cleaning implement.
    corrupted_df = corrupt_clean_dataframe(
        df=baseline_df,
        output_log_path=paths.corruption_log,
    )

    if corrupted_df.empty:
        raise RuntimeError("Corrupted dataset is empty; corruption is too destructive.")

    write_csv(corrupted_df, paths.corrupted_clean_csv)
    write_json(paths.corrupted_clean_json, _records_for_json(corrupted_df))

    # 3. Collection riêng: papers-corrupted.
    print("Building corrupted embedding index...")
    corrupted_index = LocalEmbeddingIndex.build(
        df=corrupted_df,
        settings=settings,
        embeddings_output_path=paths.corrupted_embeddings_json,
    )

    # 4. Dùng nguyên test set baseline, không tạo lại.
    print("Evaluating corrupted dataset with the baseline test set...")
    corrupted_evaluation = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.corrupted_metrics,
        answers_output_path=paths.corrupted_answers,
    )

    corrupted_quality = run_data_quality_checks(
        df=corrupted_df,
        settings=settings,
        report_name="corrupted_quality",
    )
    corrupted_freshness = build_freshness_report(
        df=corrupted_df,
        settings=settings,
        report_path=paths.quality_dir / "freshness_corrupted.json",
    )

    # 5. Repair từ raw snapshot của baseline.
    # Không fetch Crossref lần mới, vì dữ liệu nguồn mới làm comparison mất công bằng.
    print("Repairing from baseline raw snapshot...")
    raw_records = load_raw_records(paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, run_date=now_utc())

    if repaired_df.empty:
        raise RuntimeError("Repaired dataset is empty.")

    write_csv(repaired_df, paths.repaired_clean_csv)
    write_json(paths.repaired_clean_json, _records_for_json(repaired_df))

    # 6. Collection riêng: papers-repaired.
    print("Building repaired embedding index...")
    repaired_index = LocalEmbeddingIndex.build(
        df=repaired_df,
        settings=settings,
        embeddings_output_path=paths.repaired_embeddings_json,
    )

    # 7. Dùng lại chính test set baseline.
    print("Evaluating repaired dataset with the baseline test set...")
    repaired_evaluation = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.repaired_metrics,
        answers_output_path=paths.repaired_answers,
    )

    repaired_quality = run_data_quality_checks(
        df=repaired_df,
        settings=settings,
        report_name="repaired_quality",
    )
    repaired_freshness = build_freshness_report(
        df=repaired_df,
        settings=settings,
        report_path=paths.quality_dir / "freshness_repaired.json",
    )

    # 8. Comparison report.
    generate_corruption_report(
        report_path=paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_evaluation.summary,
        repaired_metrics=repaired_evaluation.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,

    )

    print("\n=== Corruption flow completed ===")
    print(f"Corruption log: {paths.corruption_log}")
    print(f"Comparison:     {paths.comparison_report}")


if __name__ == "__main__":
    main()
