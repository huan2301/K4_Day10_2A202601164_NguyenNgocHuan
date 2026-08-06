# Phase 1 Baseline Report

## Source
- **source_api:** Crossref REST API
- **query:** agentic retrieval augmented generation large language model
- **filter:** from-pub-date:2026-02-07,has-abstract:true
- **max_results_requested:** 24
- **raw_record_count:** 24
- **clean_record_count:** 24
- **raw_records_path:** /home/linux-mint-cb303/Desktop/AI_Thuc_Chien/Lab/K4_Day10_Nemo_Pipeline_Observability/data/raw/crossref_records.json
- **clean_csv_path:** /home/linux-mint-cb303/Desktop/AI_Thuc_Chien/Lab/K4_Day10_Nemo_Pipeline_Observability/data/clean/papers_clean.csv
- **embedding_manifest_path:** /home/linux-mint-cb303/Desktop/AI_Thuc_Chien/Lab/K4_Day10_Nemo_Pipeline_Observability/data/embeddings/papers_embeddings.json
- **test_set_path:** /home/linux-mint-cb303/Desktop/AI_Thuc_Chien/Lab/K4_Day10_Nemo_Pipeline_Observability/data/eval/test_set.json

## Evaluation metrics
| Metric | Baseline |
|---|---:|
| samples | 24 |
| retrieval_hit_rate | 1.0000 |
| mean_token_f1 | 1.0000 |
| judge_accuracy | 1.0000 |
| mean_judge_score | 5 |

## Data quality
- **Status:** PASS
- **Failed checks:** None
- **Rows checked:** 24

## Freshness
- **Status:** FRESH
- **Latest published:** 2026-08-01
- **Oldest published:** 2026-02-12
- **Stale rows:** 0
- **Threshold (days):** 180
