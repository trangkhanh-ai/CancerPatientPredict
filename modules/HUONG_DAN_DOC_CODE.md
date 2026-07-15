# HƯỚNG DẪN ĐỌC CODE — phần nào quan trọng, phần nào là "khung sườn"

> Cách dùng: đọc file theo đúng thứ tự dưới đây (theo dòng chảy dữ liệu).
> Trong các file chính đã có sẵn khối chú thích `MỤC LỤC FILE` + đánh dấu `[QUAN TRỌNG]`.
> Quy ước ở đây: 🔑 = phần phải hiểu để vấn đáp · ⚙ = code "khung sườn" (boilerplate), đọc lướt.

## Thứ tự đọc đề xuất (theo dòng chảy dữ liệu)

```
schema.py → import_patients.py → mapper/reducer → split.py → train.py / ml_analysis.py
         → main.py → api_router.py → model_service.py → ApiClient.cs → MainForm.cs → 5 Controls
```

---

## Module 1 — Thu thập & Chuẩn hoá dữ liệu

| File | 🔑 Phần quan trọng | ⚙ Phần còn lại |
|---|---|---|
| `schema.py` | `FEATURE_COLUMNS` (23 cột ĐÚNG THỨ TỰ), `LABEL_TO_INDEX` cố định, `feature_signature()` (SHA-256, "chứng minh thư" của 1 cấu hình bệnh nhân) | `RAW_TO_CANONICAL` (bảng đổi tên cột Excel), `age_group_of()` |
| `import_patients.py` | Bulk **upsert idempotent** theo `patient_id` (chạy lại không nhân đôi); đọc `utf-8-sig` vì CSV có BOM; `build_doc()` sinh 3 cột dẫn xuất | `to_int()`, argparse, ghi `dataset_versions` |
| `create_collections.py` | JSON Schema **validator** gắn vào collection `patients` — MongoDB tự chặn document sai kiểu | Vòng lặp tạo 6 collection |
| `create_indexes.py` | Index **unique** trên `patient_id` — tầng chặn trùng thứ 2 (sau upsert) | Các index thường (level/age/gender/signature) |
| `verify_database.py` | Các phép kiểm PASS/FAIL: đủ 1000, unique đủ, **không còn field RAW-case** trong DB | Code in ấn kết quả |
| `client.py` | ⚙ toàn bộ — chỉ đọc `.env` và trả về `MongoClient` | — |

## Module 2 — Phân tích Dữ liệu (chỉ MapReduce)

> Lưu ý cấu trúc mới: Module 2 chỉ còn 2 job MapReduce. *Tìm kiếm & lọc* đã chuyển sang
> Module 5 (mục 5.2) vì là tính năng người dùng cuối — code không đổi, chỉ đổi cách trình bày.

| File | 🔑 Phần quan trọng | ⚙ Phần còn lại |
|---|---|---|
| `mapper_distribution.py` | Tư tưởng word-count: mỗi dòng CSV phát ~26 cặp `key\t1` (5 loại khoá: level/gender/age_group/indicator/cross); dùng `csv.DictReader` đọc theo TÊN cột | `age_group()`, đếm `bad_rows` qua stderr counter |
| `reducer_distribution.py` | Mẫu reducer chuẩn Hadoop Streaming: input **đã sort theo key** → chỉ cần cộng dồn khi key đổi | Toàn file ngắn, đọc 1 lần là hiểu |
| `mapper_correlation.py` | Emit 2 loại khoá: `mean\|chỉ số\|level` (giá trị) và `xtab\|chỉ số\|bucket\|level` (đếm); bucket 1-3/4-6/7-9 | `bucket()`, `emit()` |
| `reducer_correlation.py` | `flush()` xử lý theo loại khoá: MEAN = trung bình, XTAB/N = tổng | Vòng đọc stdin giống reducer kia |
| `aggregations.py` | `compute_quality()`: phân biệt **valid_row_pct (theo DÒNG)** vs **field_completeness_pct (theo Ô)** — bẫy #7; đếm 152 signature/848 trùng ngay tại đây | `compute_stats()` chủ yếu là cộng dồn phân bố |
| `correlation_service.py` | Công thức xếp hạng: `impact = mean(High) − mean(Low)`; `pct_high_when_high_value` = %High trong nhóm chỉ số 7–9 | Vòng gom sums/cnts/xtab |

## Module 3 — Huấn luyện & Đánh giá mô hình

| File | 🔑 Phần quan trọng | ⚙ Phần còn lại |
|---|---|---|
| `split.py` | **Cốt lõi cả đồ án**: chia theo NHÓM `feature_signature` (848 dòng trùng → chia theo dòng là leakage); thứ tự nhóm = `sha256(signature + seed)` (deterministic, đồng bộ với ml_analysis.py); `assert overlap == 0`; `assert_no_conflict()` | Đọc/ghi parquet, in đếm từng lớp |
| `train.py` | 2 pipeline: LR **có StandardScaler** (age lệch thang 0–120 so với 1–9), RF không cần; StringIndexer + `handleInvalid`; đánh giá **đúng 1 lần** trên test; đoạn map lại confusion matrix về thứ tự Low/Med/High (vì alphabetAsc cho High=0) | argparse, lưu model/metrics, vòng for 2 model |
| `ml_analysis.py` | Bản "kiểm chứng độc lập" bằng sklearn — cùng split, phải ra: 152 · 848 · 0 xung đột · 697/303 · overlap=0 · **acc=1.0 cả 2 mô hình**; scaler chỉ fit trên train | In ấn, ghi json/csv |
| `ket_qua/metrics.json` | Số liệu chuẩn để đối chiếu với báo cáo | — |

> 🔑 **Câu vấn đáp quan trọng nhất:** acc=1.0 KHÔNG phải do leakage (overlap=0 đã assert),
> cũng KHÔNG chứng minh mô hình giỏi — dataset này nhãn gần như là **hàm xác định** của
> 23 chỉ số (separable). Dữ liệu thực có nhiễu sẽ thấp hơn.

## Module 4 — Dịch vụ Dự đoán (FastAPI)

| File | 🔑 Phần quan trọng | ⚙ Phần còn lại |
|---|---|---|
| `main.py` | `lifespan`: nạp Spark + model **1 lần lúc khởi động** (không nạp mỗi request); exception handler trả "Lỗi máy chủ nội bộ" — **không lộ stack trace** | Khai báo CORS, include_router, route `/` |
| `api_router.py` | `/patients/export` khai báo **TRƯỚC** `/patients/{patient_id}` (bẫy #1); `predict()` bắt RuntimeError → 503; lưu prediction trong try/except riêng (ghi sổ fail vẫn trả kết quả) | health/model/stats/quality/correlation chỉ là "gọi service rồi trả JSON" |
| `model_service.py` | `load()` 1 lần; `asyncio.Lock` cho predict (Spark không an toàn song song); decode index→label lấy từ StringIndexer TRONG model | Đo latency, đóng gói probabilities |
| `query_builder.py` | 3 whitelist (field/operator/sort) + ép `int()` mọi giá trị = chống injection; sai → ValueError → 422 | Ghép dict filter từng phần |
| `schemas.py` | `extra="forbid"` (thừa field → 422, không nhận `level`); validator gender ∈ {1,2}, chỉ số ∈ [1..9] | Khai báo field, các model response |
| `data_services.py` | ⚙ gần như toàn bộ — CRUD phân trang chuẩn (`count_documents` + `skip/limit`) | — |
| `settings.py` / `deps.py` | ⚙ đọc `.env` + dependency `get_db` | — |

## Module 5 — Ứng dụng WinForms (C#)

| File | 🔑 Phần quan trọng | ⚙ Phần còn lại |
|---|---|---|
| `ApiClient.cs` | `HttpClient` **static dùng chung** (tạo mới mỗi request = cạn socket); `LoadBaseUrl()` đọc appsettings, base URL phải có `/api/v1/` + `/` cuối (bẫy #2); `ApiException` mang mã HTTP; DTO `JsonPropertyName` khớp từng chữ key snake_case | Các method Get*/Predict* chỉ là gọi endpoint + parse JSON |
| `MainForm.cs` | `RefreshHealthAsync()` poll `/health` 30s, đổi màu xanh/vàng/đỏ | `BuildTabs()`/`BuildStatusBar()` = layout |
| `PredictionControl.cs` | `BuildFeatures()` (tên key phải trùng FEATURE_COLUMNS); `PredictAsync()` bắt riêng 503/422; `FormatValidationError()` dịch lỗi 422 của FastAPI | Lưới 23 ô nhập, vẽ 3 thanh xác suất GDI+ |
| `PatientSearchControl.cs` | `BuildQuery()` (UI → whitelist query); `SearchAsync()` async + `CancellationToken` huỷ request cũ | BuildUi/FillGrid/ShowDetail/Export = khung sườn |
| `StatsDashboardControl.cs` | `DrawDonut()` (FillPie + phủ tròn trắng làm lỗ) | DrawKpi/DrawBars/FillGrid = vẽ + đổ liệu |
| `RiskCorrelationControl.cs` | Client CHỈ hiển thị — mọi tính toán impact nằm ở backend | DrawRanking/FillGrid/ExportCsv |
| `DataQualityControl.cs` | Phân biệt 2 chỉ số % (bẫy #7); dòng 152/848 là THAM KHẢO, không phải lỗi | DrawKpi/FillGrid |
| `Program.cs` / `.csproj` / `.sln` / `appsettings.json` | ⚙ toàn bộ — entry point + cấu hình project | — |

---

## Tóm tắt 5 ý "sống còn" nếu chỉ có 5 phút

1. **`feature_signature`** = SHA-256 của 23 chỉ số → phát hiện 848/1000 dòng trùng vector.
2. Vì trùng nhiều → **group-aware split** (chia theo nhóm signature, overlap=0), không chia theo dòng.
3. **acc=1.0 là đặc tính dataset (separable)**, không phải mô hình giỏi — 0 xung đột nhãn trên 152 vector.
4. API an toàn nhờ **whitelist** (422) + model nạp **1 lần** + route `/patients/export` đứng trước `/{patient_id}`.
5. WinForms: **1 HttpClient static**, mọi call **async**, base URL phải có `/api/v1/`.
