# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Vương Đức Thoại |
| MSSV | 2A202601770 |
| Khóa/Lớp | K4 |
| Tên nhóm | NEMO |
| Vai trò chính | Điều phối pipeline |
| Repository | https://github.com/huan2301/K4_Day10_2A202601164_NguyenNgocHuan |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Cấu hình và contract pipeline | `src/core/config.py`, `.env`, contract giữa các module | Biến môi trường, yêu cầu artifact của nhóm | Quy ước paths, collection và thứ tự handoff | Hoàn thành rà soát |
| Baseline orchestration | `src/pipelines/phase1.py`, hàm `main()` | Raw records, clean DataFrame, index, test set, quality/freshness | Clean artifacts, baseline embedding, metrics, answers, report khi tích hợp | Hoàn thành phần code, chờ tích hợp |
| Corruption/repair orchestration | `src/pipelines/corruption_flow.py`, hàm `main()` | Baseline artifacts, corrupted/repaired DataFrame, test set cố định | Corrupted/repaired artifacts và comparison report khi tích hợp | Hoàn thành phần code, chờ tích hợp |
| Release và demo checklist | `script/run_phase1.py`, `script/run_corruption_flow.py`, `data/` | Artifact do các module bàn giao | Quy trình chạy, kiểm tra artifact và kịch bản demo | Đã chuẩn bị, chờ chạy end-to-end |

Tôi chịu trách nhiệm điều phối luồng dữ liệu và bảo đảm các module giao tiếp đúng contract. Tôi không sở hữu thuật toán parse Crossref, cleaning, embedding, evaluation hoặc observability; các module đó được gọi từ pipeline sau khi thành viên phụ trách bàn giao.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Thiết lập môi trường | Toàn nhóm | Cài project bằng `python -m pip install -e .` để package trong `src/` có thể import được |
| Chốt contract dữ liệu | Ingestion, Cleaning, RAG, Evaluation, Observability | Xác định cột clean bắt buộc và đường dẫn artifact giữa các module |
| Kiểm tra cú pháp pipeline | Toàn nhóm | `phase1.py` và `corruption_flow.py` được compile thành công trước khi tích hợp |
| Hướng dẫn release | Toàn nhóm | Quy định baseline chạy trước; corrupted/repaired không ghi đè baseline |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Cài package project ở chế độ editable | `pyproject.toml`, `src/` | Có thể import các package như `core`, `pipelines`, `ingestion` | `python -m pip install -e .` |
| Hoàn thiện baseline pipeline skeleton | `src/pipelines/phase1.py` | Pipeline theo thứ tự raw → clean → index → test set → evaluate → quality/freshness → report | `python -m compileall src\pipelines` |
| Hoàn thiện corruption/repair pipeline skeleton | `src/pipelines/corruption_flow.py` | Pipeline theo thứ tự corrupt → evaluate → quality/freshness → repair from raw → compare | `python -m compileall src\pipelines` |
| Thiết kế preflight checks | Hai file pipeline | Dừng sớm nếu thiếu raw, clean, test set hoặc baseline metrics; không tạo kết quả sai | Đọc logic validation và các `RuntimeError` |

Output cụ thể do phần việc của tôi tạo ra là hai module orchestration: `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`. Hai file đã compile thành công. Artifact runtime như metrics, report và Chroma collection sẽ chỉ được tạo sau khi các module phụ thuộc được tích hợp và chạy end-to-end.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline RAG gồm nhiều module do các thành viên khác nhau phụ trách. Nếu không có orchestration rõ ràng, dữ liệu có thể bị dùng sai thứ tự, baseline có thể bị ghi đè bởi corruption flow, hoặc việc so sánh metrics không còn công bằng vì test set thay đổi.

Phần của tôi giải quyết việc kết nối các module thành hai workflow tái lập được: baseline pipeline và corruption/repair pipeline.

### Cách triển khai

Trong `phase1.py`, tôi triển khai thứ tự: load/fetch raw records → clean → lưu clean CSV/JSON → build Chroma baseline → tạo hoặc load test set → evaluate → quality/freshness → report.

Trong `corruption_flow.py`, tôi triển khai: kiểm tra baseline artifacts → corrupt clean data → build corrupted index → evaluate → quality/freshness → repair từ raw snapshot → build repaired index → evaluate bằng cùng test set → comparison report.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `Settings`, raw records, clean DataFrame, test set JSON, embedding index, baseline metrics |
| Output | Clean CSV/JSON, embedding manifests, metrics JSON, answers JSON, quality/freshness JSON và Markdown reports |
| Module phụ thuộc | `ingestion.crossref`, `ingestion.cleaning`, `ingestion.corruption`, `retrieval.index`, `evaluation.testset`, `evaluation.metrics`, `observability.quality`, `observability.reporting` |
| Module sử dụng output | Script entrypoints, report module, người demo và toàn nhóm khi kiểm tra artifact |
| Điều kiện lỗi cần xử lý | Raw records rỗng, clean DataFrame rỗng, thiếu cột bắt buộc, `paper_id` trùng, `text_for_embedding` rỗng, thiếu baseline artifact trước corruption flow |

### Cách xác minh

```powershell
python -m compileall src\pipelines
```

- **Kết quả mong đợi:** Cả `phase1.py` và `corruption_flow.py` compile không lỗi cú pháp.
- **Kết quả thực tế:** Terminal hiển thị hai dòng compile cho `corruption_flow.py` và `phase1.py`.
- **Artifact/log:** `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`. Chưa có runtime artifact vì các module của role khác chưa hoàn thành.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần so sánh công bằng chất lượng RAG ở ba trạng thái baseline, corrupted và repaired.
- **Các phương án đã cân nhắc:**
  1. Dùng chung file và collection cho cả ba trạng thái.
  2. Dùng path, embedding manifest và Chroma collection riêng cho từng trạng thái.
- **Phương án đã chọn:** Dùng collection riêng `papers-baseline`, `papers-corrupted`, `papers-repaired`; đồng thời dùng file clean, embeddings, metrics và answers riêng.
- **Lý do:** Nếu corruption ghi đè baseline, sẽ không thể truy vết dữ liệu gốc hoặc chứng minh repair phục hồi kết quả. Tách artifact giúp reproducibility, audit và demo rõ ràng.
- **Bằng chứng:** `Settings.paths` đã định nghĩa các path baseline/corrupted/repaired riêng; pipeline gọi `LocalEmbeddingIndex.build()` với embedding output path tương ứng.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi:** Các module starter còn chứa `NotImplementedError: Student task: ...`.
- **Cách tái hiện:** `rg -n "TODO\(student\)|NotImplementedError" src`
- **Nguyên nhân gốc:** Các module ingestion, cleaning, evaluation và observability chưa được role tương ứng implement.
- **Cách xử lý:** Hoàn thiện pipeline orchestration theo đúng function signatures, đồng thời thêm preflight validation. Pipeline sẽ chỉ chạy end-to-end khi các module phụ thuộc được bàn giao.
- **Cách xác minh:** `python -m compileall src\pipelines` chạy thành công cho cả hai file pipeline.
- **Điều học được:** Trong dự án nhiều người, có thể hoàn thiện contract và orchestration trước; nhưng không được báo cáo end-to-end thành công nếu chưa có artifact thật.
- **Phạm vi bị ảnh hưởng:** Chưa thể tạo baseline/corrupted/repaired metrics và reports.
- **Bước tiếp theo:** Nhận bàn giao các module TODO, chạy baseline trước, kiểm tra artifact, rồi mới chạy corruption flow.

## 7. Hiểu biết về luồng end-to-end

1. Crossref API trả về metadata bài báo. Ingestion lưu raw API response và raw records JSON. Cleaning chuẩn hóa dữ liệu, tạo `text_for_embedding`, `age_days` và metadata cần thiết. `LocalEmbeddingIndex` dùng `text_for_embedding` để tạo MiniLM embeddings và lưu vào ChromaDB.
2. Evaluation set chứa câu hỏi, ground truth và `ground_truth_doc_ids`. Hệ thống retrieve top-k documents, đối chiếu document IDs với ground truth để tính `retrieval_hit_rate`; sau đó so sánh câu trả lời với ground truth để tính token F1 và judge metrics.
3. Quality checks kiểm tra row count, missing values, duplicate `paper_id`, title và summary. Freshness monitoring tập trung vào `published`, `age_days`, số row stale, ngày mới nhất và cũ nhất.
4. Phải dùng cùng test set cho baseline, corrupted và repaired để thay đổi metric phản ánh tác động của dữ liệu/index, không phải do câu hỏi hoặc ground truth thay đổi.
5. Repair thành công khi repaired dataset được tạo lại từ raw snapshot, quality/freshness signals được phục hồi và repaired metrics tốt hơn corrupted, lý tưởng là gần baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | Chưa chạy | Chưa chạy | Chưa chạy | Chờ integration để đo bằng cùng test set |
| `mean_token_f1` | Chưa chạy | Chưa chạy | Chưa chạy | Chờ answers artifact thật |
| `judge_accuracy` | Chưa chạy | Chưa chạy | Chưa chạy | Chờ evaluator và provider được cấu hình |
| `mean_judge_score` | Chưa chạy | Chưa chạy | Chưa chạy | Chờ evaluator chạy end-to-end |
| Quality checks | Chưa chạy | Chưa chạy | Chưa chạy | Chờ module observability bàn giao |
| Freshness status | Chưa chạy | Chưa chạy | Chưa chạy | Chờ clean dataset có `published` và `age_days` |

### Kết luận từ số liệu

Tại thời điểm viết báo cáo, chưa có số liệu runtime nên tôi chưa kết luận corruption làm giảm metrics hay repair phục hồi metrics.

Sau integration, cần chứng minh hai chuỗi bằng chứng:

1. Corruption có log → quality/freshness signal thay đổi → retrieval/answer metrics thay đổi.
2. Repair từ raw snapshot → quality/freshness signal phục hồi → repaired metrics phục hồi một phần hoặc toàn bộ.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data pipeline cần artifact rõ ràng ở từng bước để truy vết từ raw data đến câu trả lời của RAG.
2. Data quality và freshness là tín hiệu vận hành độc lập với metric RAG.
3. Muốn chứng minh corruption ảnh hưởng đến RAG phải giữ nguyên test set, ground truth, evaluator và top-k.

### Nếu có thêm thời gian

Tôi sẽ bổ sung test tự động cho orchestration: kiểm tra pipeline dừng đúng khi thiếu artifact, xác nhận baseline không bị ghi đè và kiểm tra ba embedding manifests trỏ đến ba collection khác nhau.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận đã nêu đều có code, command hoặc artifact để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng end-to-end.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này tập trung vào phần việc điều phối pipeline của cá nhân tôi.

**Họ và tên:** Vương Đức Thoại  
**Ngày xác nhận:** 2026-08-06
