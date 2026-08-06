# Integration Checkpoint Log

This log records only results verified from committed project artifacts. The final narrative belongs in report/group_report.md.

## CP1 — Raw to clean contract

- **Status:** Pass
- **Evidence:** data/clean/cleaning_report.json
- **Input / clean records:** 24 / 24
- **Filtered records:** 0
- **Duplicate key:** paper_id
- **Clean artifacts:** data/clean/papers_clean.csv and data/clean/papers_clean.json

## CP2 — Clean to test set/index

- **Status:** Pass
- **Clean rows:** 24
- **Duplicate paper_id / empty text_for_embedding:** 0 / 0
- **Evaluation samples:** 24
- **Evaluation schema:** id, question_type, question, ground_truth, ground_truth_doc_ids
- **Ground-truth IDs:** every ground-truth ID occurs in the clean dataset.
- **Embedding model:** sentence-transformers/all-MiniLM-L6-v2
- **Baseline collection:** papers-baseline, with 24 documents.
- **Manifest policy:** embedding manifests use data\\chroma relative to the project root.

## CP3 — Baseline end-to-end release

- **Status:** Pass
- **Command:** python script/run_phase1.py
- **Artifacts:** baseline metrics/answers, baseline quality/freshness, Phase 1 report and demo answers all exist.
- **Metrics:** retrieval_hit_rate=1.0000; mean_token_f1=1.0000; judge_accuracy=1.0000; mean_judge_score=5.0000.
- **Quality / freshness:** PASS / FRESH.
- **Test set:** data/eval/test_set.json is frozen for Phase 2.

## CP4 — Baseline break checklist

- **Baseline status:** completed and artifacts verified.
- **Phase 2 readiness:** corruption implementation, raw snapshot, frozen test set and separate output paths are available.
- **Scope decision:** do not edit metrics or answers manually; repair must rebuild from the raw snapshot.

## CP5 — Corruption and repair integration

- **Status:** Pass
- **Command:** python script/run_corruption_flow.py
- **Corruption log:** data/results/corruption_log.json records six deterministic, test-set-targeted defects.
- **Collections:** papers-baseline, papers-corrupted and papers-repaired are separate.
- **Recovery evidence:** data/results/recovery_log.json has all_checks_passed=true.

| Metric/signal | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| retrieval_hit_rate | 1.0000 | 0.8333 | 1.0000 |
| mean_token_f1 | 1.0000 | 0.7917 | 1.0000 |
| judge_accuracy | 1.0000 | 0.7917 | 1.0000 |
| mean_judge_score | 5.0000 | 4.1667 | 5.0000 |
| Data quality | PASS | FAIL | PASS |
| Freshness | FRESH | STALE | FRESH |

## CP6 — Release and demo readiness

- **Status:** Pass, pending team commit and push.
- **Comparison report:** data/reports/corruption_report.md.
- **Release evidence:** all baseline, corrupted and repaired clean datasets, manifests, answers, metrics, quality/freshness reports and Markdown reports exist.
- **Demo claim:** corruption reduces both retrieval and answer metrics; repair from the raw snapshot restores the baseline values and passes recovery evidence.
- **Evaluation limitation:** RUN_RAGAS=0 and SKIP_LLM_JUDGE=1 were used for all three states after Gemini timeouts. RAGAS is recorded as skipped and every answer artifact records the heuristic judge reason, so the comparison remains consistent and auditable.

## Final release checks

- Commit code, data artifacts and this checkpoint log together.
- Do not commit .env, credentials or secrets.
- Keep the frozen test set unchanged when demonstrating or re-running the three states.
