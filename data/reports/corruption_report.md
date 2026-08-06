# Corruption and Recovery Report

## Evaluation comparison
| Metric | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| samples | 24 | 24 | 24 |
| retrieval_hit_rate | 1.0000 | 0.8333 | 1.0000 |
| mean_token_f1 | 1.0000 | 0.7917 | 1.0000 |
| judge_accuracy | 1.0000 | 0.7917 | 1.0000 |
| mean_judge_score | 5 | 4.1667 | 5 |

## Data-quality comparison
| Signal | Baseline | Corrupted | Repaired |
|---|---|---|---|
| Status | PASS | FAIL | PASS |
| Failed checks | None | paper_id_unique, summary_min_length, freshness_threshold | None |
| Rows checked | 24 | 24 | 24 |

## Freshness comparison
| Signal | Baseline | Corrupted | Repaired |
|---|---|---|---|
| Fresh | Yes | No | Yes |
| Latest published | 2026-08-01 | 2026-07-13 | 2026-08-01 |
| Stale rows | 0 | 1 | 0 |

## Interpretation
Metrics and quality states above are copied from the corresponding generated artifacts. Treat recovery as complete only when the repaired evidence supports that conclusion.
