# Phân chia code theo 5 module (bản sao để xem / nộp bài)

> ⚠ Đây là **BẢN SAO** sắp xếp theo module cho dễ đọc — dùng để trình bày / vấn đáp.
> Code **chạy được** nằm ở `../cancer_bigdata/` (cấu trúc package chuẩn, chạy với
> `PYTHONPATH=src`). Đừng sửa code ở đây rồi mong hệ thống đổi theo — hãy sửa bên
> `cancer_bigdata/` rồi copy lại.

## Module 1 — Thu thập & Chuẩn hoá dữ liệu (`Module1_ThuThap_ChuanHoaDuLieu/`)
Công nghệ: Hadoop MapReduce, PySpark, MongoDB.

| File | Vai trò |
|---|---|
| `schema.py` | Schema canonical snake_case: 23 FEATURE_COLUMNS, ánh xạ RAW→canonical, `feature_signature` |
| `client.py` | Kết nối MongoDB từ `.env` |
| `create_collections.py` | Tạo 6 collections + JSON Schema validator cho `patients` |
| `create_indexes.py` | Unique `patient_id` + index level/age/gender/signature |
| `import_patients.py` | Bulk upsert idempotent, tự sinh signature/age_group/level_encoded |
| `import_mapreduce_stats.py` | Nạp `distributions.tsv` → `stats_mapreduce` |
| `verify_database.py` | Kiểm tra DB → in `VERIFY: PASS` |
| `du_lieu/` | Excel gốc (Kaggle) + CSV đã làm sạch (1000 dòng) |

## Module 2 — Phân tích Dữ liệu (`Module2_PhanTichDuLieu/`)

> Module 2 chỉ gồm **MapReduce** (2 job: phân bố + tương quan) — một concept duy nhất.
> Tính năng *Tìm kiếm & lọc bệnh nhân* là tính năng người dùng cuối → thuộc **Module 5**
> (endpoint `/patients` do Module 4 sở hữu, whitelist trong `query_builder.py`).
Công nghệ: Hadoop Streaming MapReduce, MongoDB aggregation.

| File | Vai trò |
|---|---|
| `mapper_distribution.py` + `reducer_distribution.py` | Đếm phân bố level/gender/age_group/chỉ số (word-count style) |
| `mapper_correlation.py` + `reducer_correlation.py` | Tương quan yếu tố nguy cơ: mean theo level + bảng chéo bucket |
| `aggregations.py` | compute_stats / compute_quality (phục vụ `/stats`, `/quality`) |
| `correlation_service.py` | Cùng logic tương quan, phục vụ online `GET /correlation` |
| `ket_qua/` | `distributions.tsv` (High 365 / Medium 332 / Low 303) + `correlation.tsv` |

## Module 3 — Huấn luyện & Đánh giá mô hình (`Module3_HuanLuyen_DanhGiaMoHinh/`)
Công nghệ: PySpark ML (Logistic Regression — mô hình trình bày chính; Random Forest chỉ
chạy đối chứng nội bộ, kết quả tương đương, không trình bày thành mục riêng).

| File | Vai trò |
|---|---|
| `split.py` | Group-aware split theo `feature_signature` (chống leakage), assert overlap = 0 |
| `train.py` | LR (Assembler→Scaler→LogReg) + RF; đánh giá 1 lần trên test; lưu PipelineModel |
| `ml_analysis.py` | Kiểm chứng nhanh bằng scikit-learn (không cần Spark) |
| `ket_qua/` | `metrics.json` (152 signatures · 848 trùng · 697/303 · acc=1.0) + confusion matrix |

## Module 4 — Dịch vụ Dự đoán (`Module4_DichVu_DuDoan_API/`)
Công nghệ: FastAPI, prefix `/api/v1`, 11 endpoint.

| File | Vai trò |
|---|---|
| `main.py` | App chính — lifespan nạp Spark + PipelineModel MỘT LẦN, CORS, ẩn stack trace |
| `api_router.py` | 11 endpoint; `/patients/export` khai báo TRƯỚC `/patients/{patient_id}` |
| `model_service.py` | Predict 1 dòng, `asyncio.Lock`, 503 nếu model chưa nạp |
| `data_services.py` | Truy vấn patients / predictions / stats / quality |
| `query_builder.py` | Whitelist field/operator/sort — chống injection, sai → 422 |
| `schemas.py` | Pydantic v2, `extra="forbid"`, gender ∈ {1,2}, chỉ số ∈ [1..9] |
| `settings.py` + `deps.py` | Cấu hình `.env` + dependency `get_db` |

## Module 5 — Ứng dụng Người dùng (`Module5_UngDung_NguoiDung_WinForms/`)
Công nghệ: C# WinForms (.NET 8), namespace `CancerBigData.Api` / `CancerBigData.UI`.

| File | Vai trò |
|---|---|
| `CancerBigData.sln` + `CancerBigData.csproj` | Solution / project (.NET 8, UseWindowsForms) |
| `Program.cs` | Entry point |
| `MainForm.cs` | TabControl 5 tab + thanh trạng thái poll `GET /health` |
| `appsettings.json` | Base URL API: `http://localhost:8000/api/v1/` |
| `ApiClient.cs` | MỘT HttpClient static dùng chung + toàn bộ DTO |
| `PredictionControl.cs` | Tab Dự đoán — 23 ô nhập → `POST /predict` (bắt 503/422) |
| `PatientSearchControl.cs` | Tab Danh sách BN — **mục 5.2 Tìm kiếm & lọc bệnh nhân** (lọc từng chỉ số, phân trang, xuất CSV; không dùng MapReduce — chỉ lọc rồi trả về) |
| `StatsDashboardControl.cs` | Tab Thống kê — KPI + donut + cột (GDI+) → `GET /stats` |
| `RiskCorrelationControl.cs` | Tab Yếu tố nguy cơ — xếp hạng impact → `GET /correlation` |
| `DataQualityControl.cs` | Tab Chất lượng dữ liệu — KPI + bảng kiểm định → `GET /quality` |

---

Sơ đồ ghép nối giữa các module:

```
[M1] Excel/CSV → làm sạch → MongoDB ──→ [M2] MapReduce phân bố + tương quan
                     │                          │
                     ▼                          ▼
[M3] group-aware split → LR + RF → PipelineModel → [M4] FastAPI /api/v1 → [M5] WinForms 5 tab
```
