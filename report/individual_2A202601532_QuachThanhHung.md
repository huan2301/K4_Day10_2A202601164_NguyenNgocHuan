# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Quách Thanh Hưng |
| MSSV | 2A202601532 |
| Khóa/Lớp | K4 |
| Tên nhóm | NEMO |
| Vai trò chính | RAG & agent người phụ trách |
| Repository | https://github.com/huan2301/K4_Day10_2A202601164_NguyenNgocHuan |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Embedding backend | `src/retrieval/embeddings.py`, `MiniLMEmbeddings` | Danh sách `text_for_embedding` từ clean dataset | Vector embedding dùng cho semantic search | Hoàn thành |
| ChromaDB vector index | `src/retrieval/index.py`, `LocalEmbeddingIndex` | Clean DataFrame, `Settings`, embedding model | ChromaDB collections và embedding manifests | Hoàn thành |
| Search và exact lookup | `LocalEmbeddingIndex.search()`, `lookup()` | Query hoặc `paper_id`/title | Top-k `SearchResult` hoặc paper document | Hoàn thành |
| Agent tools | `src/retrieval/agent.py`, `build_agent()` | Settings và local index | Agent với `semantic_search_papers` và `lookup_paper` | Hoàn thành code; cần smoke test agent riêng |

Các output của vai trò này được pipeline baseline và corruption sử dụng để xây index, truy xuất context và đánh giá câu trả lời. Ba trạng thái có collection riêng: `papers-baseline`, `papers-corrupted` và `papers-repaired`.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Kiểm tra contract dữ liệu cho index | Ingestion và cleaning | Xác nhận clean dataset có `paper_id`, `title`, `summary`, metadata và `text_for_embedding` |
| Kiểm tra test set và ground-truth IDs | Evaluation | Xác nhận `ground_truth_doc_ids` trỏ tới các paper ID có trong corpus |
| Kiểm tra index ở ba trạng thái | Pipeline và observability | Xác nhận baseline không bị ghi đè khi build corrupted/repaired index |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Tạo embedding bằng MiniLM | `src/retrieval/embeddings.py` | Dùng `sentence-transformers/all-MiniLM-L6-v2`, chuẩn hóa vector trước khi lưu | Đọc implementation `MiniLMEmbeddings`; manifest trong `data/embeddings/` |
| Xây ChromaDB index | `src/retrieval/index.py` | Lưu 24 documents cho baseline và các index corrupted/repaired riêng | `data/embeddings/papers_embeddings*.json`, `data/chroma/` |
| Implement semantic search và exact lookup | `LocalEmbeddingIndex.search()`, `lookup()` | Truy vấn semantic top-k và lookup theo `paper_id` hoặc exact title | `data/results/baseline_answers.json`, `data/results/corrupted_answers.json`, `data/results/repaired_answers.json` |
| Xây agent có tools | `src/retrieval/agent.py` | Agent được cấp semantic search và exact lookup, có system prompt yêu cầu dùng tool cho factual question | Đọc `build_agent()` và kiểm tra hai tool được đăng ký |
| Hỗ trợ evaluate RAG | `src/retrieval/qa.py`, `src/evaluation/metrics.py` | Retrieval và answer metrics phản ánh thay đổi của dữ liệu | `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json` |

Output quan trọng nhất là ba embedding manifests và ba kết quả đánh giá dùng cùng `data/eval/test_set.json`. Baseline đạt retrieval hit rate `1.0`, corrupted giảm còn `0.8333`, repaired phục hồi về `1.0`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

RAG cần biến clean paper corpus thành một vector index có thể truy vấn và trả về context đúng. Index phải hỗ trợ cả semantic search cho câu hỏi tự nhiên và exact lookup cho `paper_id` hoặc title. Khi chạy corruption flow, các collection và manifest cũng phải tách riêng để kết quả baseline không bị mutate.

### Cách triển khai

`MiniLMEmbeddings` dùng Sentence Transformers với model `all-MiniLM-L6-v2`. Document được lấy từ cột `text_for_embedding`, sau đó embedding được chuẩn hóa và đưa vào ChromaDB với cosine distance.

`LocalEmbeddingIndex._build_documents()` tạo document có `record_id`, `paper_id`, title, content và metadata. Collection name được suy ra từ output path để map lần lượt tới `papers-baseline`, `papers-corrupted` hoặc `papers-repaired`. Khi search, cosine distance được chuyển thành score bằng `1 - distance`; khi lookup, hệ thống ưu tiên exact `paper_id` rồi exact title.

Agent trong `agent.py` đóng gói index thành hai tools. System prompt yêu cầu agent gọi tool trước khi trả lời factual question và nói rõ khi corpus không hỗ trợ câu trả lời.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Clean DataFrame có `paper_id`, `title`, `text_for_embedding` và metadata; `Settings` chứa embedding model, Chroma path và collection names |
| Output | ChromaDB collection, embedding manifest, `SearchResult`, exact paper record và agent tools |
| Module phụ thuộc | `core.config`, `ingestion.cleaning`, `retrieval.embeddings`, `retrieval.llm`, `evaluation.metrics` |
| Module sử dụng output | `pipelines.phase1`, `pipelines.corruption_flow`, `retrieval.qa`, `retrieval.agent` |
| Điều kiện lỗi cần xử lý | Clean data rỗng, thiếu cột bắt buộc, `text_for_embedding` rỗng, collection không tồn tại, query không có exact match hoặc không có search result |

### Cách xác minh

```bash
python -m compileall -q src
```

- **Kết quả mong đợi:** Các module retrieval và pipeline compile không lỗi.
- **Kết quả thực tế:** Lệnh chạy thành công.
- **Artifact/log:** `data/embeddings/papers_embeddings.json`, `data/embeddings/papers_embeddings_corrupted.json`, `data/embeddings/papers_embeddings_repaired.json`, `data/chroma/`.

Ngoài ra, các pipeline đã chạy và tạo 24 mẫu answer cho từng trạng thái trong `data/results/`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Corruption flow cần rebuild index nhưng vẫn phải giữ nguyên baseline để so sánh công bằng.
- **Các phương án đã cân nhắc:** Dùng chung một collection rồi ghi đè dữ liệu; hoặc dùng collection và manifest riêng cho từng trạng thái.
- **Phương án đã chọn:** Dùng `papers-baseline`, `papers-corrupted` và `papers-repaired`, tương ứng với ba embedding manifest riêng.
- **Lý do:** Tách collection tránh baseline bị mutate, giúp truy vết dữ liệu, tái lập kết quả và chứng minh repair đã rebuild từ raw snapshot.
- **Bằng chứng quyết định phù hợp:** `src/core/config.py` định nghĩa ba collection name; `src/retrieval/index.py` map output path tới collection; metrics repaired phục hồi về `1.0`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Khi dùng cùng collection cho nhiều trạng thái, kết quả index có nguy cơ bị trạng thái sau ghi đè trạng thái trước.
- **Lệnh hoặc bước tái hiện:** Chạy liên tiếp baseline và corruption flow trong cùng `data/chroma/` nếu không có collection name riêng.
- **Nguyên nhân gốc:** ChromaDB lưu dữ liệu theo collection; dùng một collection chung làm mất ranh giới giữa baseline, corrupted và repaired.
- **Cách xử lý:** Bổ sung collection name riêng trong `Settings` và để `LocalEmbeddingIndex._derive_collection_name()` chọn collection theo embedding output path.
- **Cách xác minh sau khi sửa:** Kiểm tra ba manifest có collection name khác nhau và chạy lại hai entrypoint pipeline; metrics baseline vẫn là `1.0` sau corruption flow.
- **Điều học được:** Vector index là một artifact cần version hóa cùng dataset; không nên chỉ lưu kết quả cuối mà bỏ qua identity của collection.

## 7. Hiểu biết về luồng end-to-end

1. Crossref trả về raw records. Cleaning chuẩn hóa record, tạo `text_for_embedding`, rồi `LocalEmbeddingIndex` embed nội dung bằng MiniLM và lưu vector cùng metadata vào ChromaDB.
2. Evaluation set chứa question, ground truth và `ground_truth_doc_ids`. Kết quả retrieve được đối chiếu với các ID này để tính `retrieval_hit_rate`; answer được so sánh với ground truth để tính token F1 và judge metrics.
3. Quality checks kiểm tra tính hợp lệ của dữ liệu như row count, null, duplicate ID và summary length. Freshness monitoring tập trung vào ngày published, age và số record vượt ngưỡng stale.
4. Cùng test set giúp thay đổi metric phản ánh tác động của corruption/index, thay vì phản ánh một bộ câu hỏi hoặc ground truth khác.
5. Repair thành công khi dataset được dựng lại từ raw snapshot, quality/freshness trở về PASS/FRESH và metrics phục hồi. Trong kết quả hiện tại, repaired đạt lại các metric baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.8333 | 1.0000 | Corruption làm mất hoặc làm yếu context của một số câu hỏi; repair phục hồi hoàn toàn. |
| `mean_token_f1` | 1.0000 | 0.8333 | 1.0000 | Chất lượng answer giảm cùng chiều với retrieval. |
| `judge_accuracy` | 1.0000 | 0.8333 | 1.0000 | Có 4/24 mẫu corrupted không đạt mức đúng như baseline. |
| `mean_judge_score` | 5.0000 | 4.3333 | 5.0000 | Điểm đánh giá giảm khi dữ liệu bị blank/noise/truncate/drop. |
| Quality checks | PASS | FAIL | PASS | Corrupted fail duplicate ID, summary length và freshness; repaired pass lại. |
| Freshness status | FRESH | STALE | FRESH | Corruption tạo một record có ngày `2000-01-01`; repair khôi phục ngày từ raw. |

### Kết luận từ số liệu

1. Corruption gồm drop một frozen test record, blank summary, inject noise, truncate title, stale publication date và duplicate row → quality checks chuyển từ PASS sang FAIL, freshness có `1` stale row → retrieval hit rate giảm từ `1.0000` xuống `0.8333`, token F1 và judge accuracy cũng giảm xuống `0.8333`.
2. Repair bằng cách đọc lại raw snapshot và chạy lại cleaning → quality/freshness trở lại PASS/FRESH → retrieval hit rate, token F1, judge accuracy và mean judge score đều trở lại mức baseline.

Corruption ảnh hưởng rõ nhất là xóa record thuộc frozen test set và blank summary. Xóa record có thể làm retrieval không còn tài liệu ground-truth; blank summary làm nội dung embedding và answer context thiếu thông tin. Bằng chứng trực tiếp nằm trong `data/results/corruption_log.json` và các quality artifacts.

Kết quả đáng chú ý là số dòng corrupted cuối cùng vẫn là 24 vì một record bị xóa rồi một duplicate được thêm vào. Tuy nhiên quality vẫn fail do duplicate `paper_id`, và freshness vẫn phát hiện được ngày stale. Điều này cho thấy row count riêng lẻ không đủ để đánh giá chất lượng index.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Embedding index phải giữ đúng document ID và metadata để có thể nối retrieval result trở lại paper source.
2. Quality và freshness là các tín hiệu độc lập với RAG metrics, nhưng giúp giải thích nguyên nhân khi retrieval hoặc answer quality giảm.
3. Corruption trong dữ liệu có thể làm agent trả lời kém dù code retrieval không thay đổi; chất lượng corpus là một phần trực tiếp của chất lượng RAG.

### Nếu có thêm thời gian

Tôi sẽ bổ sung một smoke test tự động cho `build_agent()` để gọi trực tiếp cả `semantic_search_papers` và `lookup_paper`, sau đó kiểm tra agent factual answer có dùng tool và không trả lời vượt corpus. Test này sẽ bổ sung bằng chứng cho agent layer, vì các metrics pipeline hiện tại chủ yếu đánh giá đường `answer_question()` deterministic.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Quách Thanh Hưng  
**Ngày xác nhận:** 2026-08-06
