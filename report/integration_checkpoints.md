# Integration Checkpoint Log

This log records only results verified from repository artifacts. It is shared checkpoint evidence for the team; final narrative belongs in report/group_report.md.

## CP1 — Raw to clean contract

- **Status:** Pass
- **Evidence:** data/clean/cleaning_report.json
- **Input records:** 24
- **Clean records:** 24
- **Filtered records:** 0
- **Duplicate key:** paper_id
- **Required source fields:** paper_id, title, summary, published
- **Clean artifact:** data/clean/papers_clean.csv and data/clean/papers_clean.json

## CP2 — Clean to test set/index

- **Status:** Pass
- **Clean rows:** 24
- **Duplicate paper_id:** 0
- **Empty text_for_embedding:** 0
- **Evaluation samples:** 18
- **Evaluation schema:** id, question_type, question, ground_truth, ground_truth_doc_ids
- **Ground-truth IDs:** all IDs in data/eval/test_set.json exist in the clean dataset
- **Embedding model:** sentence-transformers/all-MiniLM-L6-v2
- **Baseline collection:** papers-baseline
- **Indexed documents:** 24
- **Embedding manifest:** data/embeddings/papers_embeddings.json
- **Persistence path policy:** the manifest stores data\\chroma relative to the project root so it can be loaded after another team member pulls the repository.

## CP3 — Baseline end-to-end release

- **Status:** Pass
- **Command:** `python script/run_phase1.py`
- **Artifacts verified:**
  - `data/results/baseline_metrics.json`
  - `data/results/baseline_answers.json`
  - `data/quality/freshness_report.json`
  - `data/reports/phase1_report.md`
- **Baseline collection:** `papers-baseline`
- **Test set:** `data/eval/test_set.json` (giữ cố định cho Phase 2)
- **Metrics:** xem `data/results/baseline_metrics.json`
- **Freshness/quality evidence:** xem `data/quality/`

## CP4 — Break checklist

- **Baseline status:** Completed and artifacts verified.
- **Remaining blocker:** `src/ingestion/corruption.py` còn `NotImplementedError`; Phase 2 chưa thể chạy cho đến khi module corruption được hoàn thiện.
- **Next step after break:** dùng lại clean dataset, baseline test set và raw snapshot để chạy corruption → evaluate → repair → comparison.

## CP5 — Corruption and repair integration

- **Status:** Pass
- **Corruption log:** `data/results/corruption_log.json`
- **Corrupted collection:** `papers-corrupted`
- **Repaired collection:** `papers-repaired`
- **Shared test set:** `data/eval/test_set.json`
- **Baseline preserved:** Yes; baseline hashes unchanged.
- **Artifacts:** corrupted/repaired clean datasets, manifests, answers, metrics,
  freshness reports và comparison report đã tồn tại.

## Open blocker

- **Phase 2 blocker:** src/ingestion/corruption.py still raises NotImplementedError; corruption and repair flow cannot be verified until its owner completes the module.
