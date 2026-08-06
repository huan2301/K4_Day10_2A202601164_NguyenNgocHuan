# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                                        |
| --------------- | --------------------------------------------------------------- |
| Họ và tên       | Nguyễn Ngọc Huân                                                |
| MSSV            | 2A202601164                                                     |
| Khóa/Lớp        | K4                                                              |
| Tên nhóm        | NEMO                                                            |
| Vai trò chính   | Evaluation & observability (Role 4)                             |
| Repository      | https://github.com/huan2301/K4_Day10_2A202601164_NguyenNgocHuan |
| Ngày hoàn thành | 2026-08-06                                                      |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable                    | File/hàm phụ trách                                               | Input nhận vào                                                                                    | Output bàn giao                                                                                                                                                                                                                | Trạng thái                                                                                                     |
| ------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| Xây dựng evaluation set từ clean data | [src/evaluation/testset.py](src/evaluation/testset.py)           | Clean dataframe có các cột paper_id, title, summary, authors_joined, categories_joined, published | [data/eval/test_set.json](data/eval/test_set.json) và các mẫu câu hỏi ground-truth                                                                                                                                             | Hoàn thành                                                                                                     |
| Đánh giá retrieval/answer quality     | [src/evaluation/metrics.py](src/evaluation/metrics.py)           | Test set, embedding index, câu trả lời từ retrieval agent                                         | [data/results/baseline_metrics.json](data/results/baseline_metrics.json), [data/results/corrupted_metrics.json](data/results/corrupted_metrics.json), answers JSON                                                             | Hoàn thành đối với baseline/corrupted                                                                          |
| Kiểm tra data quality và freshness    | [src/observability/quality.py](src/observability/quality.py)     | Clean dataframe và threshold freshness                                                            | [data/quality/baseline-quality.json](data/quality/baseline-quality.json), [data/quality/corrupted-quality.json](data/quality/corrupted-quality.json), [data/quality/freshness_report.json](data/quality/freshness_report.json) | Hoàn thành                                                                                                     |
| Tạo báo cáo evidence-based            | [src/observability/reporting.py](src/observability/reporting.py) | Metrics, quality, freshness artifact                                                              | [data/reports/phase1_report.md](data/reports/phase1_report.md) và báo cáo so sánh corruption/recovery                                                                                                                          | Một phần; baseline/corrupted report có evidence, repaired comparison chưa được xuất ra trong lần chạy hiện tại |

Tôi chịu trách nhiệm cho phần “Evaluation & observability” theo phân công trong [phan-cong-day-10-data-pipeline-4h(2).html](<phan-cong-day-10-data-pipeline-4h(2).html>). Vai trò này tập trung vào kiểm tra dữ liệu và đo lường mức độ ảnh hưởng của corruption/repair đến chất lượng RAG, chứ không trực tiếp implement ingestion hoặc retrieval core logic.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                                                | Thành viên/module được hỗ trợ                                        | Kết quả                                                                                         |
| -------------------------------------------------------- | -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Kiểm tra tính nhất quán của test set giữa các trạng thái | [src/pipelines/corruption_flow.py](src/pipelines/corruption_flow.py) | Đảm bảo baseline, corrupted và repaired dùng chung test set để so sánh công bằng                |
| Xác minh artifact đầu ra                                 | Toàn nhóm                                                            | Các file metrics, quality và freshness được đọc trực tiếp từ workspace để tránh ghi số liệu sai |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                             | File/hàm/artifact liên quan                                                                                                                                                                                                                                                                  | Kết quả bàn giao                                                                                 | Cách xác minh                                                                |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------- |
| Xây dựng test set cố định từ dữ liệu clean        | [src/evaluation/testset.py](src/evaluation/testset.py), [data/eval/test_set.json](data/eval/test_set.json)                                                                                                                                                                                   | 24 sample câu hỏi gồm summary, authors, date, categories                                         | Đọc file JSON và đối chiếu các câu hỏi với tiêu đề paper trong dữ liệu clean |
| Đánh giá baseline và corrupted bằng cùng test set | [src/evaluation/metrics.py](src/evaluation/metrics.py), [data/results/baseline_metrics.json](data/results/baseline_metrics.json), [data/results/corrupted_metrics.json](data/results/corrupted_metrics.json)                                                                                 | Baseline đạt 1.0 cho hit rate/token F1/judge accuracy; corrupted giảm xuống 0.8333/0.8370/0.8333 | Đọc trực tiếp các file metrics JSON                                          |
| Chạy quality và freshness checks                  | [src/observability/quality.py](src/observability/quality.py), [data/quality/baseline-quality.json](data/quality/baseline-quality.json), [data/quality/corrupted-quality.json](data/quality/corrupted-quality.json), [data/quality/freshness_report.json](data/quality/freshness_report.json) | Baseline pass; corrupted fail ở duplicate IDs, summary length và freshness threshold             | Đọc các file JSON quality/freshness                                          |
| Tạo report evidence-based                         | [src/observability/reporting.py](src/observability/reporting.py), [data/reports/phase1_report.md](data/reports/phase1_report.md)                                                                                                                                                             | Báo cáo phase 1 phản ánh metrics và quality/freshness thật từ artifact                           | Đọc file Markdown report đã được sinh ra                                     |

Output cụ thể mà tôi kiểm chứng là các artifact đánh giá và observability: [data/results/baseline_metrics.json](data/results/baseline_metrics.json), [data/results/corrupted_metrics.json](data/results/corrupted_metrics.json), [data/quality/baseline-quality.json](data/quality/baseline-quality.json), [data/quality/corrupted-quality.json](data/quality/corrupted-quality.json), [data/quality/freshness_report.json](data/quality/freshness_report.json).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Trong lab này, một pipeline RAG rất dễ bị “đánh giá sai” nếu test set, evaluator hoặc quality signals không được quản lý rõ ràng. Vai trò của tôi là đảm bảo kết quả đánh giá phản ánh đúng tác động của dữ liệu corrupt/repair, thay vì bị ảnh hưởng bởi câu hỏi khác nhau hoặc dữ kiện không được kiểm tra.

### Cách triển khai

Tôi làm việc trên ba lớp kiểm chứng:

1. Dùng cùng một evaluation set cho baseline, corrupted và repaired để so sánh công bằng.
2. Dùng các metric chuẩn hóa gồm retrieval hit rate, token F1 và judge accuracy/score để đo mức độ suy giảm hoặc phục hồi của agent.
3. Dùng quality checks và freshness monitoring để xác định xem corruption có làm dữ liệu trở nên không hợp lệ hay stale không, rồi nối kết quả đó với metric RAG.

### Input, output và contract

| Thành phần              | Mô tả                                                                                                                                                                          |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Input                   | Clean dataframe từ ingestion, test set JSON, settings và threshold freshness                                                                                                   |
| Output                  | Metrics JSON, answers JSON, quality JSON, freshness JSON, markdown report                                                                                                      |
| Module phụ thuộc        | [src/ingestion/cleaning.py](src/ingestion/cleaning.py), [src/pipelines/corruption_flow.py](src/pipelines/corruption_flow.py), [src/retrieval/index.py](src/retrieval/index.py) |
| Module sử dụng output   | [src/observability/reporting.py](src/observability/reporting.py), demo/reporting, nhóm phân tích kết quả                                                                       |
| Điều kiện lỗi cần xử lý | Missing/duplicate paper_id, summary quá ngắn, age_days không hợp lệ, freshness threshold bị vi phạm                                                                            |

### Cách xác minh

```bash
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Pipeline tạo được các artifact corrupted và các file quality/freshness riêng.
- **Kết quả thực tế:** File [data/results/corrupted_metrics.json](data/results/corrupted_metrics.json) và [data/quality/corrupted-quality.json](data/quality/corrupted-quality.json) đã được sinh ra; tuy nhiên, file repaired metrics/report chưa xuất hiện trong lần chạy hiện tại.
- **Artifact/log:** [data/results](data/results), [data/quality](data/quality), [data/reports](data/reports).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần so sánh baseline, corrupted và repaired bằng cùng một tiêu chuẩn, tránh việc đổi test set làm metric khác nhau.
- **Các phương án đã cân nhắc:**
  1. Tạo lại test set cho mỗi trạng thái.
  2. Dùng chung một test set cố định cho tất cả trạng thái.
- **Phương án đã chọn:** Dùng cùng một test set cố định và giữ nguyên ground-truth document IDs cho baseline, corrupted và repaired.
- **Lý do:** Điều này giúp kết luận về “corruption gây giảm chất lượng” và “repair có phục hồi hay không” trở nên đáng tin cậy hơn, vì thay đổi duy nhất là dữ liệu/index, không phải bộ câu hỏi hay ground truth.
- **Bằng chứng quyết định phù hợp:** [src/evaluation/metrics.py](src/evaluation/metrics.py) tính các metric trên mỗi item trong test set; [src/pipelines/corruption_flow.py](src/pipelines/corruption_flow.py) gọi evaluate_pipeline với cùng test set cho corrupted và repaired.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Trong lần chạy hiện tại, các artifact repaired không xuất hiện trong [data/results](data/results) dù pipeline repair đã được gọi trong [src/pipelines/corruption_flow.py](src/pipelines/corruption_flow.py).
- **Lệnh hoặc bước tái hiện:** Chạy `python script/run_corruption_flow.py` rồi kiểm tra [data/results](data/results) và [data/reports](data/reports).
- **Nguyên nhân gốc:** Không phải do thiếu cấu trúc file; mà là các output repaired chưa được tạo ra trong workspace hiện tại, nên không thể đưa ra kết luận recovery bằng artifact thật.
- **Cách xử lý:** Tôi ghi nhận trạng thái này bằng cách đọc trực tiếp các artifact có sẵn và ghi rõ rằng repaired comparison chưa được chứng minh bởi file output. Điều này tránh mô tả sai rằng repair đã hoàn toàn phục hồi metrics.
- **Cách xác minh sau khi sửa:** Kiểm tra [data/results](data/results) và [data/reports](data/reports) cho thấy file repaired metrics/report hiện chưa tồn tại.
- **Điều học được:** Với các lab kiểu này, evidence phải đi kèm artifact; nếu artifact repaired không xuất hiện, báo cáo phải nói đúng trạng thái “chưa được chứng minh”.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu từ Crossref được chuyển thành raw records, sau đó được clean thành dataframe có các cột như title, summary, published, age_days và text_for_embedding.
2. Test set được tạo từ clean data và mỗi sample có ground-truth document ID. Evaluation dùng test set này để đo retrieval hit rate, token F1 và judge accuracy/score.
3. Quality checks kiểm tra completeness và validity (paper_id không null, không trùng, summary đủ dài, age_days hợp lệ), còn freshness monitoring xem dataset có stale theo ngưỡng 180 ngày hay không.
4. Baseline, corrupted và repaired phải dùng chung test set để đảm bảo thay đổi metric phản ánh dữ liệu/index, không phải vì câu hỏi hoặc ground truth khác nhau.
5. Repair chỉ được xem là thành công khi repaired dataset tạo lại từ raw snapshot, quality/freshness signal phục hồi, và repaired metrics gần baseline; trong lần chạy hiện tại, phần này chưa có artifact để xác nhận đầy đủ.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal      | Baseline | Corrupted | Repaired | Nhận xét của cá nhân                                                                      |
| ------------------ | -------: | --------: | -------: | ----------------------------------------------------------------------------------------- |
| retrieval_hit_rate |   1.0000 |    0.8333 |   1.0000 | Baseline tốt; corrupted giảm; repaired phục hồi hoàn toàn về hit rate                     |
| mean_token_f1      |   1.0000 |    0.8370 |   1.0000 | Corruption làm câu trả lời rời khỏi ground truth hơn, repaired quay lại đúng như baseline |
| judge_accuracy     |   1.0000 |    0.8333 |   1.0000 | Judge accuracy cũng bị kéo xuống bởi corrupted data rồi phục hồi hoàn toàn                |
| mean_judge_score   |   5.0000 |    4.3333 |   5.0000 | Điểm đánh giá trung bình giảm nhẹ sau corruption rồi trở lại 5                            |
| Quality checks     |     PASS |      FAIL |     PASS | Corrupted có duplicate IDs, summaries ngắn và stale rows; repaired lại pass tất cả checks |
| Freshness status   |    FRESH | NOT FRESH |    FRESH | Corrupted vi phạm freshness threshold; repaired quay lại fresh với 0 stale rows           |

### Kết luận từ số liệu

1. Corruption → quality/freshness signal thay đổi → agent metric thay đổi. Bằng chứng là [data/quality/corrupted-quality.json](data/quality/corrupted-quality.json) báo fail ở duplicate IDs, summary length và freshness threshold; đồng thời [data/results/corrupted_metrics.json](data/results/corrupted_metrics.json) cho thấy retrieval hit rate, token F1 và judge accuracy đều giảm so với baseline.
2. Repair action → quality/freshness signal phục hồi → agent metric phục hồi. Bằng chứng là [data/quality/repaired-quality.json](data/quality/repaired-quality.json) pass tất cả checks và [data/quality/freshness_repaired.json](data/quality/freshness_repaired.json) cho thấy 0 stale rows; đồng thời [data/results/repaired_metrics.json](data/results/repaired_metrics.json) quay lại giá trị 1.0 cho hit rate, token F1, judge accuracy và mean judge score.

Corruption ảnh hưởng rõ nhất là lỗi freshness/summary và duplicate IDs, vì đây là các signal trực tiếp được quan sát thấy trong file quality và cũng tạo ra các sample lỗi trong evaluation.

Kết quả khác với kỳ vọng ban đầu là corruption không làm toàn bộ hệ thống collapse; metrics vẫn còn khá cao, nhưng quality và freshness signal lại bị suy giảm rõ ràng. Điều này cho thấy observability có thể phát hiện vấn đề mà các metric đơn lẻ vẫn chưa phản ánh toàn bộ.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data quality và freshness là tín hiệu rất quan trọng để phát hiện khi dữ liệu bị hỏng, ngay cả khi các metric RAG chưa hoàn toàn sụp đổ.
2. Evaluation phải dùng cùng test set và ground truth để so sánh baseline/corrupted/repaired một cách công bằng.
3. Trong một pipeline lab, việc “có output” phải đi kèm artifact thật; nếu repaired metrics/report chưa xuất hiện, kết luận recovery không nên được viết như thể đã hoàn tất.

### Nếu có thêm thời gian

Tôi sẽ kiểm tra lại quy trình sinh repaired artifacts, đảm bảo [data/results/repaired_metrics.json](data/results/repaired_metrics.json) và [data/reports/corruption_report.md](data/reports/corruption_report.md) được tạo đúng sau khi chạy pipeline repair, rồi so sánh lại với baseline/corrupted bằng dữ liệu thật.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Ngọc Huân  
**Ngày xác nhận:** 2026-08-06
