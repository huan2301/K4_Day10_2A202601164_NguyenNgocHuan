# Group Report — Day 10: Data Pipeline & Data Observability

> Dùng mẫu này cho báo cáo chung của nhóm 3–5 thành viên. Thay toàn bộ nội dung trong dấu `[ ]` bằng thông tin và kết quả thực tế. Xóa các dòng hướng dẫn không còn cần thiết trước khi nộp.

## 1. Thông tin bài nộp

| Thông tin       | Nội dung                                                          |
| --------------- | ----------------------------------------------------------------- |
| Khóa/Lớp        | K4                                                                |
| Tên nhóm        | NEMO                                                              |
| Repository      | https://github.com/huan2301/K4_Day10_2A202601164_NguyenNgocHuan   |
| Ngày hoàn thành | 2026-08-06                                                        |

### Thành viên và phân công

| STT | Họ và tên        | MSSV        | Vai trò chính              | Module/deliverable sở hữu                                                                                                                                                                                                                      |
| --: | ---------------- | ----------- | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|   1 | Nguyễn Ngọc Huân | 2A202601164 | Evaluation & observability | [src/evaluation/testset.py](src/evaluation/testset.py), [src/evaluation/metrics.py](src/evaluation/metrics.py), [src/observability/quality.py](src/observability/quality.py), [src/observability/reporting.py](src/observability/reporting.py) |
|   2 | Lê Đình Việt     | 2A202601528 | Ingestion & cleaning       | [src/ingestion/crossref.py](src/ingestion/crossref.py), [src/ingestion/cleaning.py](src/ingestion/cleaning.py), [src/ingestion/corruption.py](src/ingestion/corruption.py)                                                                     |
|   3 | Quách Thành Hưng | 2A202601532 | Retrieval & agent          | [src/retrieval/index.py](src/retrieval/index.py), [src/retrieval/embeddings.py](src/retrieval/embeddings.py), [src/retrieval/qa.py](src/retrieval/qa.py)                                                                                       |
|   4 | Vương Đức Thoại  | 2A202601770 | Pipeline orchestration     | [src/pipelines/phase1.py](src/pipelines/phase1.py), [src/pipelines/corruption_flow.py](src/pipelines/corruption_flow.py), [script/run_phase1.py](script/run_phase1.py), [script/run_corruption_flow.py](script/run_corruption_flow.py)         |

## 2. Tóm tắt kết quả

Viết từ 150–250 từ, trả lời ngắn gọn:

- Nhóm đã hoàn thành những phần nào?
- Baseline pipeline đã tạo ra các artifact nào?
- Corruption nào ảnh hưởng rõ nhất đến data quality hoặc agent?
- Repair đã phục hồi được chỉ số nào?
- Blocker hoặc giới hạn quan trọng nhất còn lại là gì?

**Tóm tắt của nhóm:**

Nhóm đã hoàn thành một pipeline RAG end-to-end từ ingestion raw data đến evaluation và observability. Baseline pipeline đã tạo ra các artifact thực tế gồm raw records, clean CSV/JSON, embeddings, evaluation set, baseline metrics, quality/freshness JSON và phase 1 report. Trong phần corruption, nhóm tạo 6 sự kiện nhiễu có kiểm soát: drop một record, blank summary, inject noise vào embedding text, truncate title, đổi published date thành 2000-01-01 và thêm duplicate row. Trong số đó, corruption gây suy giảm rõ rệt ở quality/freshness và làm các metric agent giảm từ 1.0 xuống 0.8333/0.8370/0.8333; repair từ raw snapshot đã phục hồi hoàn toàn các metric về 1.0 và đưa quality/freshness trở lại pass. Blocker còn lại là việc chạy evaluator phụ thuộc vào môi trường LLM và các artifact repaired cần được xác nhận lại trong các lần chạy tiếp theo nếu cần tái lập từ đầu.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

Điều chỉnh sơ đồ dưới đây nếu cách triển khai thực tế của nhóm khác starter:

```text
Crossref API
    -> raw response/raw records
    -> cleaning và data modeling
    -> embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> corruption
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối              | Input                                 | Xử lý chính                                                                    | Output/artifact                                                                                                                              | Owner                          |
| ----------------- | ------------------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| Ingestion         | Crossref API response và raw snapshot | Fetch, parse và lưu raw response/raw records                                   | [data/raw](data/raw)                                                                                                                         | Lê Đình Việt                   |
| Cleaning          | Raw records                           | Normalize title/summary/authors/categories, build text_for_embedding, age_days | [data/clean](data/clean)                                                                                                                     | Lê Đình Việt                   |
| Embedding/index   | Clean dataframe                       | Build MiniLM embeddings và Chroma collection                                   | [data/embeddings](data/embeddings), [data/chroma](data/chroma)                                                                               | Quách Thành Hưng               |
| Evaluation        | Clean data + index + test set         | Tạo test set, run retrieval và judge metrics                                   | [data/eval/test_set.json](data/eval/test_set.json), [data/results](data/results)                                                             | Nguyễn Ngọc Huân               |
| Observability     | Clean dataframe                       | Run quality và freshness checks, sinh report                                   | [data/quality](data/quality), [data/reports/phase1_report.md](data/reports/phase1_report.md)                                                 | Nguyễn Ngọc Huân               |
| Corruption/repair | Clean data và raw snapshot            | Corrupt data có kiểm soát, repair từ raw snapshot                              | [data/results/corruption_log.json](data/results/corruption_log.json), [data/reports/corruption_report.md](data/reports/corruption_report.md) | Lê Đình Việt + Vương Đức Thoại |
| Orchestration     | Settings và artifact                  | Chạy baseline và corruption flow theo đúng thứ tự                              | [script/run_phase1.py](script/run_phase1.py), [script/run_corruption_flow.py](script/run_corruption_flow.py)                                 | Vương Đức Thoại                |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng                                 |
| ------------------------- | ----------------------------------------------- |
| LLM_PROVIDER              | gemini                                          |
| LLM_MODEL                 | gemini-2.5-flash                                |
| Embedding model           | sentence-transformers/all-MiniLM-L6-v2          |
| Số lượng Crossref records | 24                                              |
| Retrieval top_k           | 4                                               |
| Freshness threshold       | 180 ngày                                        |
| Random seed, nếu có       | Không dùng seed cố định trong pipeline hiện tại |

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

Chỉ giữ lại cách nhóm đã dùng.

```bash
uv sync
```

Hoặc:

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh              | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng                                                                                                                                                                                                                   |
| ----------------- | ---------- | ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Baseline pipeline | Thành công | 2026-08-06 16:51        | [data/results/baseline_metrics.json](data/results/baseline_metrics.json), [data/reports/phase1_report.md](data/reports/phase1_report.md)                                                                                     |
| Corruption flow   | Thành công | 2026-08-06 17:06        | [data/results/corrupted_metrics.json](data/results/corrupted_metrics.json), [data/results/repaired_metrics.json](data/results/repaired_metrics.json), [data/reports/corruption_report.md](data/reports/corruption_report.md) |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính            | Giá trị                                                                                                                        |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Source                | Crossref REST API                                                                                                              |
| Query/filter          | query=agentic retrieval augmented generation large language model, from-pub-date:2026-02-12, has-abstract:true                 |
| Thời điểm lấy dữ liệu | 2026-08-06                                                                                                                     |
| Số record nhận được   | 24 records trong clean dataset                                                                                                 |
| Cơ chế retry/backoff  | Pipeline sử dụng raw snapshot và không có retry/backoff cụ thể trong repo hiện tại; dữ liệu được lưu lại từ lần fetch đầu tiên |

### Raw và clean schema

| Trường             | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa                           | Xử lý khi thiếu/sai                                       |
| ------------------ | ------------ | --------- | --------------------------------- | --------------------------------------------------------- |
| paper_id           | string       | Có        | ID ổn định cho mỗi paper          | Nếu thiếu thì record không dùng cho evaluation            |
| title              | string       | Có        | Tên bài báo                       | Bỏ qua hoặc giữ nhưng không dùng cho test set nếu trống   |
| summary            | string       | Có        | Tóm tắt để sinh câu hỏi           | Nếu ngắn dưới 20 ký tự thì bị phát hiện bởi quality check |
| published          | string/date  | Có        | Ngày xuất bản                     | Được parse sang date và dùng cho freshness/age_days       |
| age_days           | number       | Có        | Số ngày từ published đến run date | Dùng cho freshness threshold                              |
| text_for_embedding | string       | Có        | Chuỗi dùng cho embedding          | Build từ title + summary + authors + categories           |

### Quy tắc cleaning

| Quy tắc                                                           | Quality dimension liên quan |   Số record bị tác động | Cách xác minh                                                                                                                                             |
| ----------------------------------------------------------------- | --------------------------- | ----------------------: | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Normalize text fields và ghép authors/categories thành chuỗi join | Completeness/Consistency    |                      24 | Đọc file clean CSV/JSON và các cột authors_joined/categories_joined                                                                                       |
| Tạo text_for_embedding từ title, summary, authors, categories     | Relevance/Usability         |                      24 | So sánh dữ liệu clean với output embeddings                                                                                                               |
| Tính age_days từ published                                        | Validity/Freshness          |                      24 | Dùng [data/quality/baseline-quality.json](data/quality/baseline-quality.json) và [data/quality/freshness_report.json](data/quality/freshness_report.json) |
| Bỏ hoặc đánh dấu record có summary quá ngắn/thô                   | Completeness                | 2 trong corrupted state | Dựa trên [data/quality/corrupted-quality.json](data/quality/corrupted-quality.json)                                                                       |

Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:

`text_for_embedding` được tạo từ các trường title, summary, authors và categories để giữ đủ ngữ nghĩa cho retrieval. Document ID dùng `paper_id` ổn định từ raw/clean record và được giữ nguyên trong evaluation set để chắc chắn mỗi câu hỏi trỏ tới đúng paper. `age_days` được tính từ ngày xuất bản đến ngày chạy pipeline, rồi dùng cho freshness threshold và quality checks.

## 6. Evaluation setup

| Thành phần                            | Cấu hình thực tế                                                        |
| ------------------------------------- | ----------------------------------------------------------------------- |
| Số câu hỏi                            | 24                                                                      |
| Các question_type                     | summary, authors, date, categories                                      |
| Ground-truth document ID              | Mỗi sample dùng paper_id gốc của clean record làm ground_truth_doc_ids  |
| Embedding model                       | sentence-transformers/all-MiniLM-L6-v2                                  |
| Vector store/collection               | ChromaDB collections papers-baseline, papers-corrupted, papers-repaired |
| Retrieval top_k                       | 4                                                                       |
| LLM provider/model                    | gemini / gemini-2.5-flash                                               |
| Test set dùng chung cho ba trạng thái | [data/eval/test_set.json](data/eval/test_set.json)                      |

Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:

Test set được giữ nguyên để đảm bảo mọi thay đổi trong metric phản ánh đúng tác động của dữ liệu bị corrupt và repair, chứ không phải do câu hỏi hoặc ground truth thay đổi. Điều này giúp nhóm kết luận có căn cứ về mối nhân quả giữa corruption và quality/metric.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                                                        | Trạng thái | Ghi chú                                                      |
| ------------------------ | ------------------------------------------------------------------------ | ---------- | ------------------------------------------------------------ |
| Raw response/records     | [data/raw](data/raw)                                                     | Có         | Có raw response và raw records JSON                          |
| Cleaned dataset          | [data/clean](data/clean)                                                 | Có         | Có papers_clean.csv/json và các phiên bản repaired/corrupted |
| Embedding manifest/index | [data/embeddings](data/embeddings), [data/chroma](data/chroma)           | Có         | Có embedding JSON và Chroma persisted store                  |
| Evaluation set           | [data/eval/test_set.json](data/eval/test_set.json)                       | Có         | 24 câu hỏi dùng cho baseline/corrupted/repaired              |
| Baseline metrics         | [data/results/baseline_metrics.json](data/results/baseline_metrics.json) | Có         | retrieval_hit_rate = 1.0, mean_token_f1 = 1.0                |
| Quality/freshness        | [data/quality](data/quality)                                             | Có         | baseline-quality, corrupted-quality, freshness_report        |
| Baseline report          | [data/reports/phase1_report.md](data/reports/phase1_report.md)           | Có         | Báo cáo phase 1 từ artifact thật                             |

### Baseline metrics

| Metric             |       Giá trị | Diễn giải                                            |
| ------------------ | ------------: | ---------------------------------------------------- |
| retrieval_hit_rate |        1.0000 | Tất cả 24 câu hỏi đều hit đúng ground-truth document |
| mean_token_f1      |        1.0000 | Câu trả lời khớp rất cao với ground truth            |
| judge_accuracy     |        1.0000 | Judge xác nhận 100% câu đúng                         |
| mean_judge_score   |        5.0000 | Điểm trung bình của judge là 5                       |
| Ragas              | N/A (skipped) | Chưa bật RUN_RAGAS nên phần Ragas không chạy         |

## 8. Data quality và freshness

### Quality checks

| Check               | Quality dimension | Ngưỡng/kỳ vọng                   | Kết quả baseline | Bằng chứng                                                               |
| ------------------- | ----------------- | -------------------------------- | ---------------- | ------------------------------------------------------------------------ |
| paper_id_unique     | Validity          | 0 duplicate                      | Pass             | [data/quality/baseline-quality.json](data/quality/baseline-quality.json) |
| summary_min_length  | Completeness      | 0 summary dưới 20 ký tự          | Pass             | [data/quality/baseline-quality.json](data/quality/baseline-quality.json) |
| freshness_threshold | Freshness         | 0 stale rows với ngưỡng 180 ngày | Pass             | [data/quality/freshness_report.json](data/quality/freshness_report.json) |

### Freshness

| Thuộc tính            | Giá trị                                                                     |
| --------------------- | --------------------------------------------------------------------------- |
| Freshness được đo tại | [data/quality/freshness_report.json](data/quality/freshness_report.json)    |
| Timestamp mới nhất    | 2026-08-01                                                                  |
| Ngưỡng freshness      | 180 ngày                                                                    |
| Trạng thái baseline   | Fresh                                                                       |
| Lý do                 | 24 rows có published hợp lệ, 0 stale rows, max_age_days=175, min_age_days=5 |

## 9. Corruption scenarios và repair

| Corruption              | Cách tạo                           | Record bị tác động | Quality signal kỳ vọng             | Tác động thực tế                                                                                        | Cách repair                                 |
| ----------------------- | ---------------------------------- | -----------------: | ---------------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| drop_frozen_test_record | Xóa một record dùng trong test set |                  1 | Giảm completeness và retrieval hit | [data/results/corrupted_metrics.json](data/results/corrupted_metrics.json) giảm hit rate xuống 0.8333   | Repair từ raw snapshot và chạy lại cleaning |
| blank_summary           | Đặt summary về rỗng                |                  1 | Summary_min_length fail            | [data/quality/corrupted-quality.json](data/quality/corrupted-quality.json) báo 2 summaries không đủ dài | Rebuild từ raw data và clean lại            |
| inject_embedding_noise  | Thêm noise vào text_for_embedding  |                  1 | Retrieval quality giảm             | Metric token F1/judge giảm so với baseline                                                              | Rebuild embeddings từ repaired clean data   |
| truncate_title          | Cắt ngắn title                     |                  1 | Semantic search bị ảnh hưởng       | Một vài câu hỏi bị trả lời sai trong corrupted_answers                                                  | Rebuild index từ cleaned data gốc           |
| stale_publication_date  | Đổi published thành 2000-01-01     |                  1 | Freshness threshold fail           | [data/quality/freshness_corrupted.json](data/quality/freshness_corrupted.json) có stale_rows=1          | Repair lại published từ raw snapshot        |
| duplicate_row           | Nhân bản một row                   |                  1 | Duplicate IDs/rows                 | [data/quality/corrupted-quality.json](data/quality/corrupted-quality.json) báo duplicate_ids=2          | Rebuild clean dataframe từ raw snapshot     |

Corruption log:

- Đường dẫn: [data/results/corruption_log.json](data/results/corruption_log.json)
- Trạng thái: Có
- Nhận xét: Log ghi đầy đủ 6 loại corruption, record bị tác động và tham số trước/sau, nên đủ để audit và phân tích nhân quả.

Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:

Repair không sửa tay answers hoặc metrics. Thay vào đó, nhóm rebuild lại clean dataframe từ raw snapshot gốc, tạo lại embeddings và evaluate lại bằng cùng test set. Cách này đảm bảo repaired data và metrics được tạo ra từ nguồn dữ liệu đáng tin cậy, nên kết quả có thể kiểm chứng.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét                                                       |
| ------------------------ | -------: | --------: | -------: | ---------------------: | -----------: | -------------------------------------------------------------- |
| retrieval_hit_rate       |   1.0000 |    0.8333 |   1.0000 |                -0.1667 |         100% | Corruption làm giảm hit rate, repaired phục hồi hoàn toàn      |
| mean_token_f1            |   1.0000 |    0.8370 |   1.0000 |                -0.1630 |         100% | Token F1 giảm sau corruption rồi trở về baseline               |
| judge_accuracy           |   1.0000 |    0.8333 |   1.0000 |                -0.1667 |         100% | Judge accuracy giảm rồi phục hồi đầy đủ                        |
| mean_judge_score         |   5.0000 |    4.3333 |   5.0000 |                -0.6667 |         100% | Điểm đánh giá trung bình trở về 5                              |
| Quality checks pass/fail |     Pass |      Fail |     Pass |           Fail -> Pass |    Hoàn toàn | Corrupted có duplicate/summary/freshness issues; repaired pass |
| Freshness status         |    Fresh | Not fresh |    Fresh |               Degraded |    Hoàn toàn | Corrupted có 1 stale row; repaired về 0 stale rows             |

Nêu ít nhất hai kết luận có quan hệ nhân quả được hỗ trợ bởi artifacts:

1. Corruption bằng cách drop record, blank summary, stale date và duplicate row → quality/freshness signal bị suy giảm (corrupted-quality fail, freshness_corrupted có stale_rows=1) → retrieval/answer metric giảm (retrieval_hit_rate 0.8333, mean_token_f1 0.8370, judge_accuracy 0.8333).
2. Repair từ raw snapshot → quality/freshness recovery (repaired-quality pass, freshness_repaired 0 stale rows) → agent metric recovery (repaired_metrics quay về 1.0 cho hit rate, token F1, judge accuracy và mean judge score).

Không kết luận corruption “có tác động” nếu số liệu không cho thấy thay đổi. Nếu kết quả khác kỳ vọng, mô tả giả thuyết và cách nhóm đã kiểm tra.

## 11. Vấn đề tích hợp quan trọng

Mô tả một vấn đề phát sinh khi ghép các module trong pipeline và cách nhóm xử lý:

- **Triệu chứng:** Baseline và corruption flow có thể chạy sai nếu các module không dùng chung contract và path artifact.
- **Nguyên nhân:** Root cause là các module liên quan đến ingestion, cleaning, evaluation và observability cần cùng một schema và đường dẫn đầu ra; nếu không, các artifact sẽ bị ghi đè hoặc so sánh không công bằng.
- **Cách xử lý:** Nhóm dùng path riêng cho baseline/corrupted/repaired, giữ nguyên test set baseline cho cả ba trạng thái, và dùng preflight checks trong [src/pipelines/corruption_flow.py](src/pipelines/corruption_flow.py).
- **Cách xác minh:** Chạy [script/run_corruption_flow.py](script/run_corruption_flow.py); kết quả tạo được [data/results/corrupted_metrics.json](data/results/corrupted_metrics.json), [data/results/repaired_metrics.json](data/results/repaired_metrics.json) và [data/reports/corruption_report.md](data/reports/corruption_report.md).

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại                                                   | Ảnh hưởng                                                          | Hướng cải thiện có thể kiểm chứng                                      |
| ------------------------------------------------------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| Evaluator còn phụ thuộc vào môi trường LLM và có fallback heuristic | Một số câu trả lời có thể không phản ánh đúng chất lượng ngữ nghĩa | Chạy với provider LLM thực và bật kiểm tra judge đầy đủ                |
| Chưa có automated test suite cho pipeline                           | Khó phát hiện regression nhanh                                     | Thêm pytest cho baseline/corrupted/repaired workflow và quality checks |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong [data/results](data/results).
- [x] Quality/freshness conclusions khớp với [data/quality](data/quality).
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
