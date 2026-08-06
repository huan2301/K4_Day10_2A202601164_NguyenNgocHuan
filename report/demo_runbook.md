# Day 10 Demo Runbook

## Preconditions

- Use the project root as the working directory.
- Keep the frozen test set at data/eval/test_set.json unchanged.
- For the reproducible offline evaluation used by this run, set RUN_RAGAS=0 and SKIP_LLM_JUDGE=1.
- Never show or commit .env values or API keys.

## Demo sequence

1. Show raw-to-clean lineage:
   - data/raw/crossref_records.json
   - data/clean/papers_clean.csv
   - data/clean/cleaning_report.json

2. Show baseline evidence:
   - data/results/baseline_metrics.json
   - data/quality/baseline-quality.json
   - data/quality/freshness_report.json
   - data/reports/phase1_report.md

3. Show controlled corruption:
   - data/results/corruption_log.json
   - Six logged defects target documents referenced by the frozen test set.

4. Show measurable impact:

   | Metric | Baseline | Corrupted |
   | --- | ---: | ---: |
   | retrieval_hit_rate | 1.0000 | 0.8333 |
   | mean_token_f1 | 1.0000 | 0.7917 |
   | judge_accuracy | 1.0000 | 0.7917 |
   | mean_judge_score | 5.0000 | 4.1667 |

5. Show repair and recovery:
   - data/clean/papers_clean_repaired.csv
   - data/results/recovery_log.json
   - data/results/repaired_metrics.json
   - data/reports/corruption_report.md

   Recovery evidence records all_checks_passed=true. Repaired metrics, quality and freshness return to baseline values.

## Re-run commands

    $env:RUN_RAGAS="0"
    $env:SKIP_LLM_JUDGE="1"
    python script\run_phase1.py
    python script\run_corruption_flow.py

## Acceptance checklist

- Baseline, corrupted and repaired use separate embedding manifests and collections.
- The same test set is used for all three states.
- Baseline artifacts are not manually edited during corruption or repair.
- Comparison claims match the JSON artifacts and Markdown reports.
