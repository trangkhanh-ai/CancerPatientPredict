# Kiến trúc hệ thống — 5 module

```
Excel/CSV → Làm sạch → HDFS → Hadoop MapReduce (đếm phân bố + tương quan)
                                     ↓
                                 MongoDB
                                     ↓
              PySpark ML (group-aware split → Logistic Regression) → PipelineModel
                                     ↓
                          FastAPI (/api/v1) ← serving layer
                                     ↓
                          C# WinForms (5 tab)
```

## Module 1 — Thu thập & Chuẩn hoá dữ liệu (Data Ingestion & Preparation)

**Công nghệ:** Hadoop MapReduce, PySpark, MongoDB.

- Nguồn: `data/raw/cancer_patient_data_sets.xlsx` (Kaggle — Rishi Damarla, 2021),
  1000 bệnh nhân × 25 cột.
- Chuẩn hoá về schema canonical **snake_case** (`src/common/schema.py`):
  `RAW_TO_CANONICAL` đổi `Patient Id` → `patient_id`, `Level` → `level`, …
  Sau bước này **không còn RAW-case ở bất kỳ đâu**.
- Làm sạch bản chất là **map-only** (mỗi dòng độc lập); pha Reduce có ý nghĩa thật ở
  bước **đếm số vi phạm theo `check_name`** (R2).
- Kết quả: `data/processed/cancer_patients_ml_ready.csv` (1000 dòng, snake_case,
  lưu ý file có UTF-8 BOM → đọc bằng `utf-8-sig`).
- Nạp MongoDB (`src/mongodb/`):
  - `create_collections.py` — 6 collections (`patients`, `stats_mapreduce`, `data_quality`,
    `model_runs`, `predictions`, `dataset_versions`) + JSON Schema validator cho `patients`.
  - `create_indexes.py` — unique `patient_id` + index level/age/gender/signature.
  - `import_patients.py` — **bulk upsert idempotent**; tự sinh `feature_signature`
    (SHA-256 của 23 đặc trưng nối `|` đúng thứ tự), `age_group`, `level_encoded`.
  - `verify_database.py` — kiểm tổng/unique/index/không còn RAW-case → in `VERIFY: PASS`.

## Module 2 — Phân tích Dữ liệu (Data Analytics)

**Công nghệ:** Hadoop Streaming MapReduce — module này gồm đúng **2 job MapReduce**
(tính năng *Tìm kiếm & lọc bệnh nhân* là tính năng người dùng cuối, thuộc Module 5;
endpoint `/patients` do Module 4 sở hữu).

- **Đếm phân bố** (`mapper_distribution.py` + `reducer_distribution.py`, word-count style):
  mỗi dòng phát ~26 cặp `(key, 1)` với 5 loại khoá — `level|`, `gender|`, `age_group|`,
  `indicator|<tên>|<giá trị>`, `cross|`. Output: `artifacts/distributions.tsv`.
- **Tương quan yếu tố nguy cơ** (`mapper_correlation.py` + `reducer_correlation.py`):
  emit `mean|<ind>|<level>` và `xtab|<ind>|<bucket>|<level>`
  (bucket: 1–3 thấp / 4–6 trung bình / 7–9 cao); reduce → trung bình + bảng chéo.
  Output: `artifacts/correlation.tsv`. `impact = mean(High) − mean(Low)`.
- Cùng logic phục vụ online qua `src/api/services/correlation_service.py`
  (endpoint `GET /correlation`) và `src/common/aggregations.py` (`/stats`, `/quality`).

## Module 3 — Huấn luyện & Đánh giá mô hình (Model Training & Evaluation)

**Công nghệ:** PySpark ML — mô hình trình bày chính là **Logistic Regression** (phục vụ
qua `models/current/`); Random Forest chỉ chạy **đối chứng nội bộ** (kết quả tương đương,
xem ghi chú trong ML_EVALUATION.md).

- **Phát hiện quan trọng nhất:** chỉ **152 vector 23-đặc-trưng duy nhất** trên 1000 dòng
  (848 dòng trùng vector, 0 xung đột nhãn) → random split theo dòng gây **leakage**.
- `src/ml/split.py` — **group-aware split** theo `feature_signature`, phân tầng theo lớp,
  thứ tự nhóm deterministic theo `sha256(signature + seed)`, assert `overlap == 0`.
- `src/ml/train.py` — LR (VectorAssembler → StandardScaler → LogisticRegression multinomial)
  + RF (không cần scaler); StringIndexer ánh xạ **cố định** Low=0, Medium=1, High=2;
  đánh giá **một lần duy nhất** trên test; lưu PipelineModel + metrics.
- `ml_analysis.py` (gốc repo) — kiểm chứng nhanh bằng scikit-learn trên **cùng** split,
  không cần Spark; ghi `artifacts/metrics/metrics.json`.
- Model phục vụ dự đoán: `models/current/pipeline_model` + `models/current/metadata.json`.

## Module 4 — Dịch vụ Dự đoán (Prediction Service)

**Công nghệ:** FastAPI (`src/api/`).

- `main.py` — lifespan nạp Spark + PipelineModel **một lần**; CORS giới hạn;
  exception handler không lộ stack trace; chạy **1 worker** (mỗi worker 1 SparkSession).
- `routers/api_router.py` — 11 endpoint (xem [API.md](API.md));
  `/patients/export` khai báo **trước** `/patients/{patient_id}` (tránh nuốt route).
- `query_builder.py` — **whitelist** field/operator/sort cho tìm kiếm (chống injection);
  sai whitelist → 422.
- `services/model_service.py` — predict 1 dòng, `asyncio.Lock`, decode index→label,
  503 nếu model chưa nạp.
- `models/schemas.py` — Pydantic v2, `extra="forbid"`, gender ∈ {1,2}, chỉ số ∈ [1..9].

## Module 5 — Ứng dụng Người dùng (C# WinForms, .NET 8)

**Cấu trúc:** `winforms/CancerBigData.sln` — namespace `CancerBigData.Api` / `CancerBigData.UI`.

| Tab | Control | API |
|---|---|---|
| Dự đoán | `PredictionControl` | `POST /predict` |
| Danh sách bệnh nhân | `PatientSearchControl` | `GET /patients`, `/patients/export` |
| Thống kê | `StatsDashboardControl` | `GET /stats` |
| Yếu tố nguy cơ | `RiskCorrelationControl` | `GET /correlation` |
| Chất lượng dữ liệu | `DataQualityControl` | `GET /quality` |

- **Một `HttpClient` static dùng chung** (`Api/ApiClient.cs`); base URL đọc từ
  `appsettings.json` (`http://localhost:8000/api/v1/` — bắt buộc có prefix + `/` cuối).
- Mọi lời gọi API **async** — không block UI thread.
- Biểu đồ vẽ bằng **GDI+ (`OnPaint`)** — không dùng thư viện chart ngoài.
- `MainForm` — TabControl 5 tab + thanh trạng thái poll `GET /health` (30s/lần):
  trạng thái API · `model_run_id` · `dataset_version` + disclaimer học thuật.

## Quy ước dùng chung

- Schema canonical snake_case ở `src/common/schema.py` — **mọi** thành phần
  (CSV/MongoDB/Spark/API/C#) dùng đúng 23 `FEATURE_COLUMNS` theo đúng thứ tự.
- `feature_signature` = SHA-256 của 23 đặc trưng nối bằng `|` đúng thứ tự.
- Ánh xạ nhãn cố định `Low=0, Medium=1, High=2`.
- Code Python import theo package → chạy từ gốc repo với `PYTHONPATH=src`.
