from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def _records_for_json(df: pd.DataFrame) -> list[dict]:
    """Chuyển DataFrame sang dữ liệu JSON an toàn."""
    safe_df = df.copy()

    for column in safe_df.columns:
        if pd.api.types.is_datetime64_any_dtype(safe_df[column]):
            safe_df[column] = safe_df[column].dt.strftime("%Y-%m-%d")

    safe_df = safe_df.where(pd.notna(safe_df), None)
    return safe_df.to_dict(orient="records")


def main() -> None:
    settings = load_settings()
    paths = settings.paths

    print("=== Phase 1: Baseline pipeline ===")

    # 1. Dùng raw snapshot cũ để tái lập kết quả.
    # Chỉ fetch lại Crossref nếu chưa có snapshot hoặc REFRESH_SOURCE=true.
    if settings.refresh_source or not paths.raw_records_json.exists():
        print("Fetching records from Crossref...")
        records = fetch_source_records(settings)
    else:
        print(f"Loading raw snapshot: {paths.raw_records_json}")
        records = load_raw_records(paths.raw_records_json)

    if not records:
        raise RuntimeError("No raw records available; cannot run baseline pipeline.")

    print(f"Raw record count: {len(records)}")

    # 2. Clean và lưu dataset.
    clean_df = build_clean_dataframe(records, run_date=now_utc())

    if clean_df.empty:
        raise RuntimeError("Clean dataset is empty; stop before indexing.")

    required_columns = {
        "paper_id",
        "title",
        "summary",
        "published",
        "age_days",
        "authors_joined",
        "categories_joined",
        "text_for_embedding",
    }
    missing_columns = required_columns - set(clean_df.columns)
    if missing_columns:
        raise RuntimeError(
            f"Clean dataframe is missing required columns: {sorted(missing_columns)}"
        )

    if clean_df["paper_id"].duplicated().any():
        raise RuntimeError("Clean dataframe has duplicate paper_id values.")

    if clean_df["text_for_embedding"].fillna("").str.strip().eq("").any():
        raise RuntimeError("Clean dataframe has empty text_for_embedding values.")

    write_csv(clean_df, paths.clean_csv)
    write_json(paths.clean_json, _records_for_json(clean_df))

    print(f"Clean record count: {len(clean_df)}")
    print(f"Saved clean data: {paths.clean_csv}")

    # 3. Tạo Chroma collection baseline + embedding manifest.
    print("Building baseline embedding index...")
    index = LocalEmbeddingIndex.build(
        df=clean_df,
        settings=settings,
        embeddings_output_path=paths.embeddings_json,
    )

    # 4. Test set được khóa sau lần tạo đầu tiên.
    # Nó không nên bị tạo mới trong corruption/repaired flow.
    if settings.refresh_test_set or not paths.eval_testset.exists():
        print("Building evaluation test set...")
        test_set = build_test_set(clean_df, paths.eval_testset)
    else:
        print(f"Loading existing test set: {paths.eval_testset}")
        test_set = read_json(paths.eval_testset)

    if not test_set:
        raise RuntimeError("Evaluation test set is empty.")

    # 5. Evaluate baseline.
    print("Evaluating baseline...")
    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.baseline_metrics,
        answers_output_path=paths.baseline_answers,
    )

    # 6. Quality và freshness.
    quality = run_data_quality_checks(
        df=clean_df,
        settings=settings,
        report_name="baseline_quality",
    )
    freshness = build_freshness_report(
        df=clean_df,
        settings=settings,
        report_path=paths.freshness_report,
    )

    # 7. Lưu vài câu trả lời để dùng khi demo.
    demo_answers = []
    for item in test_set[:3]:
        result = answer_question(
            question=item["question"],
            settings=settings,
            index=index,
        )
        demo_answers.append(
            {
                "question": item["question"],
                "ground_truth": item["ground_truth"],
                "answer": result.answer,
                "retrieved_doc_ids": result.retrieved_doc_ids,
                "retrieved_titles": result.retrieved_titles,
            }
        )

    write_json(paths.demo_answers, demo_answers)

    # 8. Tạo report.
    source_summary = {
        "source_api": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "max_results_requested": settings.max_results,
        "raw_record_count": len(records),
        "clean_record_count": len(clean_df),
        "raw_records_path": str(paths.raw_records_json),
        "clean_csv_path": str(paths.clean_csv),
        "embedding_manifest_path": str(paths.embeddings_json),
        "test_set_path": str(paths.eval_testset),
    }

    generate_phase1_report(
        report_path=paths.baseline_report,
        source_summary=source_summary,
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )

    print("\n=== Baseline completed ===")
    print(f"Metrics: {paths.baseline_metrics}")
    print(f"Report:  {paths.baseline_report}")
    print(f"Demo:    {paths.demo_answers}")


if __name__ == "__main__":
    main()