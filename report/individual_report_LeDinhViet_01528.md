# Báo cáo cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Lê Đình Việt |
| MSSV | 2A292601528 |
| Khóa/Lớp | K4 |
| Tên nhóm | Nemo |
| Vai trò chính | Role 2 — Nền tảng dữ liệu và recovery |
| Repository | https://github.com/huan2301/K4_Day10_2A202601164_NguyenNgocHuan |
| Branch | `LeDinhViet_01528` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|---|---|---|---|---|
| Crossref ingestion | `src/ingestion/crossref.py` | Crossref `/works` payload | Raw response và `PaperRecord` JSON | Hoàn thành |
| Clean data contract | `src/ingestion/cleaning.py` | Danh sách `PaperRecord` | Clean CSV/JSON và cleaning report | Hoàn thành |
| CP1 validation | `src/ingestion/validation.py` | Crossref sample | Sample raw/clean artifacts | Hoàn thành |
| Controlled corruption | `src/ingestion/corruption.py` | Clean baseline và frozen test IDs | Corrupted CSV/JSON và corruption log | Hoàn thành phần Role 2 |
| Repair từ raw | `src/ingestion/recovery.py`, raw snapshot | Raw snapshot đáng tin | Repaired clean artifacts và recovery evidence | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Module được hỗ trợ | Kết quả và bằng chứng |
|---|---|---|
| Audit lineage CP2 | Retrieval/evaluation | Xác nhận 24 DOI khớp raw → clean → index và test IDs hợp lệ |
| Audit baseline CP3 | Pipeline/observability | Phát hiện một index document còn JATS markup và report dùng đường dẫn tuyệt đối |
| Đồng bộ Git | Nhóm | Commit theo checkpoint, merge `main`, fetch lại trước mốc tiếp theo |

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/hàm/artifact | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| Parse và fetch Crossref | `parse_crossref_payload`, `fetch_source_records` | 24 raw records, DOI unique, retry/backoff 429/503 | Đọc `data/raw/crossref_records.json` |
| Làm sạch dữ liệu | `build_clean_dataframe` | 24 clean records, không ID trùng, không embedding text rỗng | `data/clean/cleaning_report.json` |
| Chuẩn hóa markup | `_strip_markup`, `_normalize_text` | Xóa JATS như `<scp>RAG</scp>` khỏi title/summary | So sánh raw/clean trước và sau commit `06f4f10` |
| Tạo corruption có kiểm soát | `corrupt_clean_dataframe` | Sáu corruption event có DOI và before/after count | `data/results/corruption_log.json` |
| Giữ baseline bất biến | Deep copy và output path riêng | Baseline clean/raw không bị ghi đè | So sánh Git status và các path baseline/corrupted |
| Phục hồi từ raw | `repair_clean_dataset_from_raw`, `build_recovery_evidence` | 24 repaired rows giống baseline; 6/6 corruption checks pass | `data/results/recovery_log.json` |

Các commit chính của tôi:

- `fe525ff`: hoàn thiện CP0 data contracts.
- `aed7461`: tạo clean dataset có audit cho CP1.
- `06f4f10`: loại Crossref/JATS markup ở CP2.
- `7b29c0f`: tạo corrupted dataset và log cho CP5.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

RAG chỉ đáng tin khi tài liệu có định danh ổn định, dữ liệu sạch và có thể truy vết về nguồn. Phần tôi phụ trách bảo đảm metadata Crossref được lưu nguyên bản trước khi parse, DOI được dùng xuyên suốt làm `paper_id`, mọi record bị loại đều có lý do, và dữ liệu bị corruption có thể phục hồi bằng cách chạy lại từ raw snapshot.

### Cách triển khai

1. Gọi Crossref bằng query/filter trong `Settings`; dùng retry có backoff cho HTTP 429/503.
2. Ghi toàn bộ API response trước khi parse để vẫn có bằng chứng nguồn nếu parser lỗi.
3. Chuẩn hóa DOI về lowercase và bỏ tiền tố `doi:`/`https://doi.org/`.
4. Parse title, abstract, authors, categories, ngày xuất bản và URL thành `PaperRecord`.
5. Cleaning yêu cầu `paper_id`, `title`, `summary`, `published`; record thiếu hoặc ngày sai bị loại và ghi reason code.
6. Authors/categories được chuẩn hóa, loại trùng nhưng giữ thứ tự; thiếu thì dùng `Unknown`/`Uncategorized` ở field joined.
7. `age_days` là số ngày UTC từ `published` tới ngày chạy.
8. `text_for_embedding` ghép title, authors, categories, published và abstract theo một format dùng chung cho clean/corrupted/repaired.
9. Corruption chỉ tác động bản deep copy và dùng các DOI thuộc frozen test set để tác động có thể đo được.

### Input, output và contract

| Thành phần | Mô tả |
|---|---|
| Input ingestion | Crossref JSON payload |
| Input cleaning | `list[PaperRecord]` và UTC run date |
| Output raw | `crossref_response.json`, `crossref_records.json` |
| Output clean | `papers_clean.csv`, `papers_clean.json`, `cleaning_report.json` |
| Output corruption | `papers_clean_corrupted.csv/json`, `corruption_log.json` |
| Output recovery | `papers_clean_repaired.csv/json`, `cleaning_report_repaired.json`, `recovery_log.json` |
| Module dùng output | `src/retrieval/`, `src/evaluation/`, `src/observability/` |
| Lỗi được xử lý | Thiếu DOI/title/summary, ngày sai, duplicate, XML/JATS markup, HTTP 429/503 |

### Cách xác minh

```powershell
.\.venv\Scripts\python.exe -m ingestion.validation
```

- Kết quả mong đợi: duplicate DOI bị loại, record thiếu abstract không vào clean data.
- Kết quả thực tế: `parsed_records=3`, `clean_records=2`.
- Artifact: `data/raw/crossref_sample*.json`, `data/clean/papers_clean_sample.*`.

Kiểm tra dữ liệu thật cho kết quả 24 raw records, 24 clean records, 24 DOI duy nhất và không có `text_for_embedding` rỗng.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần một ID ổn định để nối raw, clean, index, test set và recovery.
- **Phương án cân nhắc:** tạo ID theo số thứ tự; hash title; hoặc dùng DOI chuẩn hóa.
- **Phương án chọn:** dùng DOI lowercase, bỏ tiền tố URL/`doi:`.
- **Lý do:** số thứ tự thay đổi khi API đổi thứ tự; title có thể đổi hoặc chứa markup; DOI là định danh publication do nguồn cung cấp.
- **Bằng chứng:** 24 raw DOI đều unique và tập ID khớp giữa raw, clean và index. Test set dùng các DOI này trong `ground_truth_doc_ids`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** title của DOI `10.1111/exsy.70341` chứa `Hi‐ <scp>RAG</scp> ...` trong raw, clean và index.
- **Tái hiện:** đọc title tương ứng trong `data/raw/crossref_records.json` và `data/embeddings/papers_embeddings.json`.
- **Nguyên nhân gốc:** parser chỉ loại markup trong abstract, chưa loại JATS markup trong title.
- **Cách xử lý:** thêm `_strip_markup` ở parser và `_normalize_text` phòng vệ ở cleaning; parse lại từ raw API response cũ, không refetch nguồn.
- **Xác minh:** `RAW_MARKUP_TITLES=0`, `CLEAN_MARKUP_TITLES=0`, `CLEAN_MARKUP_SUMMARIES=0`.
- **Điều học được:** cần normalize tại biên nguồn và vẫn kiểm tra phòng vệ ở clean layer; khi clean thay đổi thì index phải rebuild để tránh schema drift.

Blocker còn theo dõi: baseline index cũ từng giữ title có markup và `phase1_report.md` có đường dẫn tuyệt đối từ máy khác. Các owner liên quan cần regenerate artifact trước khi khóa kết quả cuối.

## 7. Hiểu biết về luồng end-to-end

Crossref trả metadata và được lưu thành raw snapshot. Parser chuyển từng item thành `PaperRecord`, sau đó cleaning chuẩn hóa và tạo `text_for_embedding`. Role 3 biến text này thành vector MiniLM và lưu trong collection ChromaDB. Khi có câu hỏi, retrieval so sánh vector để lấy tài liệu gần nhất; exact lookup có thể dùng DOI/title.

Evaluation set chứa câu hỏi, đáp án chuẩn và `ground_truth_doc_ids`. Retrieval hit khi tài liệu trả về chứa DOI chuẩn. Token F1 đo mức giống giữa câu trả lời và đáp án; judge metric chấm tính đúng của answer.

Quality checks đo tính đầy đủ, hợp lệ và duy nhất như null, duplicate, độ dài summary. Freshness tập trung vào tuổi dữ liệu qua `published` và `age_days`. Hai nhóm signal bổ sung cho nhau nhưng không thay thế nhau.

Baseline, corrupted và repaired phải dùng cùng test set, top-k và evaluator để biến dữ liệu thành biến độc lập duy nhất. Nếu đổi câu hỏi hoặc cách chấm giữa các lần, metric không còn so sánh công bằng.

Repair thành công khi repaired data được tạo lại từ raw, schema và quality/freshness phục hồi, index repaired chứa đúng document, và metrics tiến gần hoặc trở lại baseline. Không được sửa answers hoặc metrics bằng tay.

## 8. Phân tích kết quả hiện có

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
|---|---:|---:|---:|---|
| `retrieval_hit_rate` | 1.0000 | Chưa được bàn giao | Chưa được bàn giao | Baseline tìm đúng tài liệu cho 24/24 câu hỏi |
| `mean_token_f1` | 1.0000 | Chưa được bàn giao | Chưa được bàn giao | Baseline answer khớp ground truth hiện tại |
| `judge_accuracy` | 1.0000 | Chưa được bàn giao | Chưa được bàn giao | Cần giữ nguyên evaluator khi so sánh |
| `mean_judge_score` | 5.0000 | Chưa được bàn giao | Chưa được bàn giao | Điểm tối đa ở baseline |
| Quality checks | PASS | Chưa được Role 4 bàn giao | Data recovery PASS | Repaired JSON tái tạo đúng 24 baseline rows |
| Freshness status | FRESH | Chưa được Role 4 bàn giao | Dữ liệu khớp baseline | Repaired `published`/`age_days` giống baseline |

### Corruption đã chuẩn bị

Corrupted dataset có sáu event được log:

1. Drop DOI `10.2118/234689-pa`: 24 → 23 rows.
2. Blank summary DOI `10.1007/s10278-026-02086-9`.
3. Inject embedding noise DOI `10.21203/rs.3.rs-10178277/v1`.
4. Truncate title DOI `10.2196/preprints.106157`.
5. Đổi published của DOI `10.21079/11681/50309` về `2000-01-01`.
6. Duplicate DOI `10.1007/s10278-026-02086-9`: 23 → 24 rows.

Chưa kết luận corruption nào làm agent giảm mạnh nhất vì corrupted/repaired index và metrics chưa được Role 3/4 bàn giao tại thời điểm hoàn thiện báo cáo. Tôi không suy đoán hoặc tự điền số liệu thay cho artifact còn thiếu.

### Kết quả recovery tầng dữ liệu

Recovery được thực hiện bằng cách load lại `data/raw/crossref_records.json` có SHA-256 `e36e56305037458857b1f1afa50e18ab392eca3a04fc785a7f740011cf133094`, rồi chạy lại canonical cleaner. Kết quả có 24 rows, `paper_id` unique và JSON repaired giống JSON baseline. Sáu kiểm tra trong corruption log đều pass: record bị drop xuất hiện lại, summary được phục hồi, noise biến mất, title trở lại đầy đủ, publication date trở lại giá trị raw và duplicate chỉ còn một row.

Chuỗi bằng chứng hiện có là: corruption có log → clean corrupted xuất hiện missing/duplicate/stale/noise có chủ đích → repair từ raw → 6/6 recovery checks pass và repaired data bằng baseline. Chuỗi metric agent chưa thể kết luận cho đến khi Role 3/4 bàn giao evaluation artifacts.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw snapshot và stable ID là nền tảng của lineage và recovery; chỉ giữ clean data là chưa đủ.
2. Data observability cần cả count và lý do chi tiết. Tổng số rows có thể không đổi dù dữ liệu đã xấu, ví dụ một drop cộng một duplicate.
3. Một lỗi nhỏ như XML tag trong title có thể lan từ raw sang clean, embedding và test question; mọi artifact downstream phải rebuild sau khi data contract thay đổi.

### Nếu có thêm thời gian

Tôi sẽ bổ sung test tự động cho parser/cleaner/corruption với payload biên: DOI dạng URL, partial date, HTML entities, authors thiếu given/family, duplicate hợp lệ sau record lỗi và publication date tương lai. Chất lượng cải thiện được đo bằng số branch rule được test và khả năng tái tạo cùng artifact từ cùng raw snapshot.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phạm vi công việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận hiện có đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không sao chép nguyên văn báo cáo nhóm hoặc thành viên khác.

**Họ và tên:** Lê Đình Việt
**Ngày xác nhận:** 2026-08-06
