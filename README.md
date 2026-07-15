# 🏥 Hệ thống Dự đoán Mức độ Mắc bệnh Ung thư — Big Data

> **Đồ án môn Lập trình Python ứng dụng (Big Data) — Trường Đại học Ngoại ngữ - Tin học TP.HCM (HUFLIT)**
>
> GVHD: TS. Võ Thị Hồng Tuyết

---

## 📋 Mục lục

- [Tổng quan](#-tổng-quan)
- [Kiến trúc hệ thống](#-kiến-trúc-hệ-thống)
- [Cấu trúc thư mục](#-cấu-trúc-thư-mục)
- [Dataset](#-dataset)
- [5 Module chi tiết](#-5-module-chi-tiết)
- [Yêu cầu môi trường](#-yêu-cầu-môi-trường)
- [Hướng dẫn cài đặt & chạy](#-hướng-dẫn-cài-đặt--chạy)
- [API Endpoints](#-api-endpoints)
- [Đánh giá mô hình ML](#-đánh-giá-mô-hình-ml)
- [Ảnh chụp giao diện](#-ảnh-chụp-giao-diện)
- [Câu hỏi thường gặp](#-câu-hỏi-thường-gặp)
- [Lưu ý học thuật](#-lưu-ý-học-thuật)

---

## 🎯 Tổng quan

Hệ thống nhận **23 chỉ số** của bệnh nhân (tuổi, giới tính và 21 chỉ số nguy cơ thang 1–9), dự đoán mức độ mắc bệnh ung thư (**Low / Medium / High**), đồng thời cung cấp:

- 📊 **Thống kê** phân bố dữ liệu (level, giới tính, nhóm tuổi)
- 🔍 **Tìm kiếm & lọc** bệnh nhân theo từng chỉ số với whitelist chống injection
- ⚠️ **Xếp hạng yếu tố nguy cơ** (impact = mean(High) − mean(Low))
- ✅ **Báo cáo chất lượng dữ liệu** (valid_row_pct vs field_completeness_pct)
- 🩺 **Dự đoán trực tuyến** với xác suất 3 lớp + disclaimer học thuật

### Công nghệ sử dụng

| Công nghệ | Vai trò |
|---|---|
| **Hadoop MapReduce** | Phân tích phân bố & tương quan yếu tố nguy cơ |
| **PySpark MLlib** | Huấn luyện mô hình Logistic Regression (group-aware split) |
| **MongoDB** | Kho dữ liệu bệnh nhân, lịch sử dự đoán, thống kê |
| **FastAPI** | REST API serving layer — 11 endpoint, prefix `/api/v1` |
| **C# WinForms (.NET 8)** | Ứng dụng desktop 5 tab cho người dùng cuối |
| **scikit-learn** | Kiểm chứng nhanh kết quả ML (không cần Spark) |

---

## 🏗 Kiến trúc hệ thống

```
Excel/CSV → Làm sạch → HDFS/CSV sạch → Hadoop MapReduce (đếm phân bố + tương quan)
                                              ↓
                                          MongoDB
                                              ↓
             PySpark ML (group-aware split → Logistic Regression) → PipelineModel
                                              ↓
                                 FastAPI (/api/v1) ← serving layer
                                              ↓
                                 C# WinForms (5 tab)
```

### Luồng dữ liệu end-to-end

```
[Module 1] Excel gốc (25 cột, RAW-case)
    → Làm sạch (đổi tên cột snake_case, ép kiểu, kiểm miền giá trị)
    → CSV sạch (1000 dòng × 23 đặc trưng + nhãn level)
    → MongoDB (collection patients — bulk upsert idempotent)

[Module 2] CSV sạch
    → Job 1: MapReduce đếm phân bố (level|High → 365, gender|1 → 512, ...)
    → Job 2: MapReduce tương quan (mean chỉ số theo level + bảng chéo bucket)
    → distributions.tsv + correlation.tsv → MongoDB stats_mapreduce

[Module 3] CSV sạch
    → feature_signature (SHA-256 của 23 chỉ số)
    → Group-aware split (697 train / 303 test, overlap = 0)
    → VectorAssembler → StandardScaler → LogisticRegression
    → PipelineModel (lưu models/current/)

[Module 4] FastAPI :8000
    ← Nạp PipelineModel 1 lần lúc startup
    ← Kết nối MongoDB qua get_db()
    → 11 endpoint: health, model, predict, patients, predictions, stats, quality, correlation

[Module 5] C# WinForms
    → 5 tab: Dự đoán · Danh sách BN · Thống kê · Yếu tố nguy cơ · Chất lượng DL
    → Gọi API qua HttpClient static (async, không block UI)
```

---

## 📁 Cấu trúc thư mục

```
.
├── cancer_bigdata/          ⭐ REPO CHÍNH — code CHẠY ĐƯỢC
│   ├── src/
│   │   ├── common/          Schema canonical, aggregations, correlation_service
│   │   ├── hadoop/          Mapper/Reducer cho 2 job MapReduce
│   │   ├── mongodb/         Client, collections, indexes, import, verify
│   │   ├── ml/              split.py, train.py (PySpark ML)
│   │   └── api/             FastAPI: main, router, services, schemas, settings
│   ├── winforms/            Solution C# WinForms (.NET 8)
│   ├── data/                Dữ liệu gốc + đã xử lý
│   ├── artifacts/           Output MapReduce (distributions.tsv, correlation.tsv)
│   ├── models/              PipelineModel + metrics
│   ├── docs/                ARCHITECTURE · API · ML_EVALUATION · RUNBOOK
│   └── ml_analysis.py       Kiểm chứng nhanh bằng scikit-learn
│
├── modules/                 📖 BẢN SAO chia theo 5 module, CÓ CHÚ THÍCH
│   ├── Module1_ThuThap_ChuanHoaDuLieu/
│   ├── Module2_PhanTichDuLieu/
│   ├── Module3_HuanLuyen_DanhGiaMoHinh/
│   ├── Module4_DichVu_DuDoan_API/
│   ├── Module5_UngDung_NguoiDung_WinForms/
│   ├── README.md
│   ├── HUONG_DAN_DOC_CODE.md
│   ├── HUONG_DAN_CHAY_DEMO_VA_VAN_DAP.md
│   └── GIAI_DAP_CAU_HOI_NHOM.md
│
├── cleandata cancer/        Notebook + script tiền xử lý dữ liệu
├── final+spark/             Train Spark MLlib (train_spark.py + model_spark/)
├── tai_lieu_bao_cao/        📄 Báo cáo Word/PDF + tài liệu + hình ảnh
├── luu_tru_file_goc/        🗄 File code gốc ban đầu (lưu trữ, không dùng để chạy)
└── _run/                    Log/output các lần chạy thử
```

---

## 📊 Dataset

| Thuộc tính | Giá trị |
|---|---|
| **Nguồn** | `cancer patient data sets.xlsx` — Kaggle, tác giả **Rishi Damarla (2021)** |
| **Kích thước** | 1000 bệnh nhân × 25 cột |
| **Đặc trưng** | `patient_id`, `age`, `gender`, 21 chỉ số nguy cơ (thang 1–9), nhãn `level` |
| **Phân bố nhãn** | **High = 365** · **Medium = 332** · **Low = 303** |
| **Chất lượng** | 0 sai miền · 0 thiếu · 0 trùng patient_id → giữ 1000/1000 dòng |
| **⚠ Đặc điểm quan trọng** | Chỉ **152 vector 23-đặc-trưng duy nhất** (848 dòng trùng vector) |

> ⚠ **Vì 848/1000 dòng trùng vector đặc trưng**, random split theo dòng sẽ gây **data leakage**.
> → Bắt buộc sử dụng **group-aware split** theo `feature_signature` (SHA-256 của 23 chỉ số).

---

## 🧩 5 Module chi tiết

### Module 1 — Thu thập & Chuẩn hoá Dữ liệu

> **Công nghệ:** Hadoop MapReduce, PySpark, MongoDB

| File | Vai trò |
|---|---|
| `schema.py` | Schema canonical snake_case: 23 `FEATURE_COLUMNS` đúng thứ tự, `LABEL_TO_INDEX` cố định, `feature_signature()` (SHA-256) |
| `client.py` | Kết nối MongoDB singleton (`MongoClient` tái sử dụng connection pool) |
| `create_collections.py` | Tạo collections + JSON Schema validator cho `patients` |
| `create_indexes.py` | Unique index `patient_id` + index level/age/gender/signature |
| `import_patients.py` | Bulk upsert **idempotent** (chạy lại không tạo trùng), sinh `feature_signature`, `age_group`, `level_encoded` |
| `import_mapreduce_stats.py` | Nạp kết quả MapReduce (`distributions.tsv`) vào `stats_mapreduce` |
| `verify_database.py` | Kiểm tra DB: tổng, unique, phân bố, index, validator, không RAW-case → `VERIFY: PASS` |

**Điểm quan trọng:**
- Đọc CSV bằng `encoding="utf-8-sig"` vì file có BOM
- `UpdateOne(upsert=True)` → chạy 10 lần vẫn đúng 1000 document
- 3 tầng chặn trùng: (1) upsert logic, (2) unique index, (3) JSON Schema validator

---

### Module 2 — Phân tích Dữ liệu (2 job MapReduce)

> **Công nghệ:** Hadoop Streaming MapReduce, MongoDB aggregation
>
> Module 2 chỉ gồm MapReduce — **một concept duy nhất**. Tìm kiếm & lọc bệnh nhân đã chuyển sang Module 5.

| File | Vai trò |
|---|---|
| `mapper_distribution.py` + `reducer_distribution.py` | **Job 1:** Đếm phân bố level/gender/age_group/chỉ số (word-count style) |
| `mapper_correlation.py` + `reducer_correlation.py` | **Job 2:** Tương quan yếu tố nguy cơ: mean theo level + bảng chéo bucket |
| `aggregations.py` | `compute_stats()` / `compute_quality()` (phục vụ `/stats`, `/quality`) |
| `correlation_service.py` | Xếp hạng: `impact = mean(High) − mean(Low)` + `pct_high_when_high_value` |

**Sự khác biệt giữa 2 job:**

| | Mapper phát ra | Reducer làm gì | Kết quả |
|---|---|---|---|
| **Job 1 (Phân bố)** | `(key, 1)` | Cộng dồn | `level\|High = 365` |
| **Job 2 (Tương quan)** | `(key, giá trị chỉ số)` | Tính trung bình (Σ/n) | `mean(smoking, High) = 6.07` |

**Top 5 yếu tố nguy cơ (impact cao nhất):**

| Hạng | Chỉ số | Impact (Δ) | % High khi chỉ số 7–9 |
|---|---|---|---|
| 1 | `alcohol_use` | +4.60 | — |
| 2 | `coughing_of_blood` | +4.58 | — |
| 3 | `obesity` | +4.27 | — |
| 4 | `passive_smoker` | +3.90 | **100%** |
| 5 | `genetic_risk` | +3.65 | — |

---

### Module 3 — Huấn luyện & Đánh giá Mô hình

> **Công nghệ:** PySpark MLlib (Logistic Regression)

| File | Vai trò |
|---|---|
| `split.py` | **Group-aware split** theo `feature_signature` — chống leakage, assert overlap = 0 |
| `train.py` | Pipeline: `VectorAssembler → StandardScaler → LogisticRegression` (multinomial) |
| `ml_analysis.py` | Kiểm chứng nhanh bằng scikit-learn — cùng split, phải ra cùng kết quả |

**Pipeline huấn luyện:**

```
CSV sạch → feature_signature (SHA-256)
         → group-aware split (697 train / 303 test, overlap = 0)
         → VectorAssembler (23 đặc trưng)
         → StandardScaler (fit trên train, transform test)
         → LogisticRegression (family=multinomial, maxIter=300)
         → Đánh giá ĐÚNG 1 LẦN trên test
         → PipelineModel (lưu models/current/)
```

**Kết quả chính thức:**

| Metric | Giá trị |
|---|---|
| **Accuracy** | 1.0000 |
| **Macro-F1** | 1.0000 |
| **Confusion Matrix** | `[[87,0,0],[0,90,0],[0,0,126]]` |
| **Train / Test** | 697 / 303 |
| **Signature overlap** | 0 |

> *Ghi chú: nhóm có chạy thêm một mô hình đối chứng (Random Forest) để kiểm chứng nội bộ và thu được kết quả tương đương, khẳng định điểm số cao đến từ **đặc tính tách hoàn toàn của dữ liệu** chứ không phải do lựa chọn thuật toán.*

**Giải thích `feature_signature`:**

```
23 chỉ số theo đúng thứ tự → nối bằng "|" → SHA-256
"44|1|6|7|7|7|6|6|7|7|7|7|7|8|5|3|2|7|8|2|4|5|3"  →  "eb532c41..." (64 hex)
```

- 1000 dòng nhưng chỉ **152 signature duy nhất** → 848 dòng trùng vector
- 0 xung đột nhãn (cùng vector → cùng level)
- Chia train/test theo **nhóm** (không theo dòng) → overlap = 0

---

### Module 4 — Dịch vụ Dự đoán (FastAPI)

> **Công nghệ:** FastAPI, 11 endpoint, prefix `/api/v1`

| File | Vai trò |
|---|---|
| `main.py` | Lifespan: nạp Spark + PipelineModel **1 lần** lúc startup; CORS; ẩn stack trace |
| `api_router.py` | 11 endpoint; `/patients/export` khai báo **TRƯỚC** `/patients/{patient_id}` |
| `model_service.py` | Predict 1 dòng, `asyncio.Lock` (Spark không an toàn song song), 503 nếu model chưa nạp |
| `data_services.py` | CRUD patients/predictions/stats/quality |
| `query_builder.py` | **Whitelist** field/operator/sort — chống injection, sai → 422 |
| `schemas.py` | Pydantic v2: `extra="forbid"`, gender ∈ {1,2}, chỉ số ∈ [1..9] |
| `settings.py` + `deps.py` | Cấu hình `.env` + dependency `get_db` |

**3 cơ chế phòng thủ:**
1. **Pydantic `extra="forbid"`** — thừa field → 422, không nhận `level`
2. **Whitelist** (21 chỉ số × 4 toán tử) — chuỗi lạ không lọt vào Mongo query
3. **`asyncio.Lock`** — Spark transform tuần tự, tránh race condition

---

### Module 5 — Ứng dụng Người dùng (WinForms)

> **Công nghệ:** C# WinForms (.NET 8)

| File | Vai trò |
|---|---|
| `Program.cs` | Entry point |
| `MainForm.cs` | TabControl 5 tab + thanh trạng thái poll `/health` mỗi 30 giây |
| `ApiClient.cs` | **1 HttpClient static** dùng chung (tránh socket exhaustion) + toàn bộ DTO |
| `PredictionControl.cs` | Tab Dự đoán — 23 ô nhập → `POST /predict` (bắt 503/422) |
| `PatientSearchControl.cs` | Tab Danh sách BN — lọc theo từng chỉ số, phân trang, xuất CSV |
| `StatsDashboardControl.cs` | Tab Thống kê — KPI + donut + biểu đồ cột (GDI+) |
| `RiskCorrelationControl.cs` | Tab Yếu tố nguy cơ — thanh xếp hạng impact |
| `DataQualityControl.cs` | Tab Chất lượng DL — KPI + bảng kiểm định |

**5 tab giao diện:**

| Tab | Endpoint gọi | Mô tả |
|---|---|---|
| 🩺 **Dự đoán** | `POST /predict` | Nhập 23 chỉ số → mức độ + xác suất 3 lớp |
| 👥 **Danh sách BN** | `GET /patients` + `/export` | Tìm kiếm, lọc theo chỉ số, phân trang, xuất CSV |
| 📊 **Thống kê** | `GET /stats` | KPI + donut phân bố + cột trung bình chỉ số |
| ⚠ **Yếu tố nguy cơ** | `GET /correlation` | Xếp hạng impact, bảng chi tiết, xuất CSV |
| ✔ **Chất lượng DL** | `GET /quality` | KPI + bảng kiểm định (valid_row vs field_completeness) |

---

## ⚙ Yêu cầu môi trường

| Thành phần | Phiên bản |
|---|---|
| **Python** | 3.10+ |
| **JDK** | 17+ (PySpark cần — đặt `JAVA_HOME`) |
| **MongoDB** | 7.x (chạy ở `localhost:27017`) |
| **.NET SDK** | 8.0+ (WinForms, project đặt `RollForward=LatestMajor`) |

**Thư viện Python:**
```
pandas, scikit-learn, pymongo, fastapi, uvicorn, pyspark, openpyxl
```

---

## 🚀 Hướng dẫn cài đặt & chạy

### Bước 0 — Clone & cài đặt

```powershell
git clone https://github.com/trangkhanh-ai/CancerPatientPredict.git
cd CancerPatientPredict/cancer_bigdata
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
$env:PYTHONPATH = 'src'
$env:PYTHONUTF8 = '1'
```

### Bước 1 — MongoDB (kho dữ liệu)

```powershell
# Kiểm tra MongoDB
Test-NetConnection localhost -Port 27017

# Nếu chưa chạy:
docker run -d -p 27017:27017 --name mongo7 mongo:7

# Nạp dữ liệu (idempotent — chạy lại không sao)
python src/mongodb/create_collections.py
python src/mongodb/create_indexes.py
python src/mongodb/import_patients.py --input data/processed/cancer_patients_ml_ready.csv
python src/mongodb/import_mapreduce_stats.py --input artifacts/distributions.tsv
python src/mongodb/verify_database.py     # PHẢI in: VERIFY: PASS
```

### Bước 2 — MapReduce (phân tích dữ liệu)

```powershell
# Job 1: Phân bố
cat data/processed/cancer_patients_ml_ready.csv |
  python src/hadoop/mapper_distribution.py | sort |
  python src/hadoop/reducer_distribution.py > artifacts/distributions.tsv

# Job 2: Tương quan yếu tố nguy cơ
cat data/processed/cancer_patients_ml_ready.csv |
  python src/hadoop/mapper_correlation.py | sort |
  python src/hadoop/reducer_correlation.py > artifacts/correlation.tsv
```

### Bước 3 — Huấn luyện mô hình (PySpark)

```powershell
$env:JAVA_HOME = 'C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot'

# Kiểm chứng nhanh bằng scikit-learn (không cần Spark)
python ml_analysis.py

# Hoặc train chính thức bằng Spark
python src/ml/split.py --input data/processed/cancer_patients_ml_ready.csv --out data/processed
python src/ml/train.py --split data/processed/split_manifest.parquet --out models
```

### Bước 4 — FastAPI (serving layer)

```powershell
$env:JAVA_HOME = 'C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot'
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
# Chờ dòng: [startup] model_loaded=True
# Swagger: http://127.0.0.1:8000/docs
```

### Bước 5 — WinForms (giao diện)

```powershell
cd winforms
dotnet run --project CancerBigData
```

> **Thứ tự khởi động:** MongoDB → FastAPI → WinForms. Tắt theo thứ tự ngược.

---

## 🌐 API Endpoints

Base URL: `http://localhost:8000/api/v1`

| Method | Endpoint | Mô tả |
|---|---|---|
| `GET` | `/health` | Trạng thái API, MongoDB, model |
| `GET` | `/model` | Thông tin model (algorithm, features, metrics) |
| `POST` | `/predict` | Dự đoán mức độ (23 chỉ số → level + probabilities) |
| `GET` | `/patients` | Tìm kiếm bệnh nhân (whitelist filter, phân trang) |
| `GET` | `/patients/export` | Xuất CSV theo bộ lọc |
| `GET` | `/patients/{patient_id}` | Chi tiết 1 bệnh nhân |
| `GET` | `/predictions` | Lịch sử dự đoán |
| `GET` | `/predictions/{prediction_id}` | Chi tiết 1 prediction |
| `GET` | `/stats` | Thống kê tổng quan |
| `GET` | `/quality` | Chất lượng dữ liệu |
| `GET` | `/correlation` | Tương quan yếu tố nguy cơ |

**Mã lỗi:**
- `422` — Dữ liệu không hợp lệ (Pydantic validate hoặc whitelist reject)
- `503` — Model chưa được nạp (thiếu Spark hoặc model artifact)
- `500` — Lỗi server (không lộ stack trace)

---

## 📈 Đánh giá mô hình ML

### Baseline Check

| Metric | Giá trị |
|---|---|
| Tổng dòng | 1000 |
| Vector đặc trưng duy nhất | 152 |
| Dòng trùng vector | 848 |
| Xung đột nhãn (cùng vector, khác level) | **0** |

### Group-Aware Split

| | Train | Test |
|---|---|---|
| **Tổng** | 697 | 303 |
| Low | 216 | 87 |
| Medium | 242 | 90 |
| High | 239 | 126 |
| **Signature overlap** | **0** | |

### Kết quả Logistic Regression

| Metric | Giá trị |
|---|---|
| Accuracy | **1.0000** |
| Weighted Precision | **1.0000** |
| Weighted Recall | **1.0000** |
| Macro-F1 | **1.0000** |

**Confusion Matrix** (rows = actual, cols = predicted):

|  | Low | Medium | High |
|---|---|---|---|
| **Low** | 87 | 0 | 0 |
| **Medium** | 0 | 90 | 0 |
| **High** | 0 | 0 | 126 |

### Kết luận trung thực

> Accuracy = 1.0 **KHÔNG** chứng minh mô hình mạnh. Dataset này có **0 xung đột nhãn** trên 152 vector duy nhất → nhãn gần như là **hàm xác định** của 23 chỉ số → dữ liệu **separable hoàn toàn**. Dữ liệu thực tế có nhiễu sẽ cho kết quả thấp hơn đáng kể.

---

## 🖼 Ảnh chụp giao diện

### Thanh trạng thái

| Màu | Ý nghĩa |
|---|---|
| 🟢 Xanh | API + Model hoạt động |
| 🟡 Vàng | API hoạt động, Model chưa nạp |
| 🔴 Đỏ | Không kết nối được API |

### 5 Tab

1. **🩺 Dự đoán** — Nhập 23 chỉ số → kết quả + 3 thanh xác suất + disclaimer
2. **👥 Danh sách BN** — Lọc theo chỉ số, phân trang, xuất CSV
3. **📊 Thống kê** — Donut phân bố + cột trung bình + KPI
4. **⚠ Yếu tố nguy cơ** — Thanh xếp hạng impact + bảng chi tiết
5. **✔ Chất lượng DL** — KPI (raw/valid/invalid/%) + bảng kiểm định

---

## ❓ Câu hỏi thường gặp

<details>
<summary><b>1. Vì sao dùng MongoDB mà không phải MySQL?</b></summary>

Document JSON khớp thẳng bản ghi bệnh nhân 25 trường, dễ thêm trường dẫn xuất (`feature_signature`, `age_group`) không cần ALTER TABLE. Aggregation pipeline phục vụ thống kê linh hoạt.
</details>

<details>
<summary><b>2. Dữ liệu vào MongoDB bằng cách nào? Chạy lại có bị nhân đôi không?</b></summary>

`import_patients.py` dùng bulk `UpdateOne(upsert=True)` khớp theo `patient_id` — **idempotent**: chạy 10 lần vẫn đúng 1000 document. Thêm 2 tầng chặn: unique index `patient_id` + JSON Schema validator.
</details>

<details>
<summary><b>3. Vì sao phải group-aware split?</b></summary>

1000 dòng nhưng chỉ 152 vector duy nhất (848 trùng). Random split theo dòng → cùng cấu hình rơi vào cả train lẫn test → **leakage**. Nên chia theo NHÓM `feature_signature`, assert overlap = 0.
</details>

<details>
<summary><b>4. Accuracy = 1.0 có phải mô hình quá giỏi / gian lận?</b></summary>

Không do leakage (overlap=0 đã assert). Cũng không phải mô hình giỏi: 152 vector có 0 xung đột nhãn → nhãn là **hàm xác định** của 23 chỉ số → dữ liệu separable. Dataset học thuật; dữ liệu thực sẽ thấp hơn.
</details>

<details>
<summary><b>5. Chống injection ở API thế nào?</b></summary>

Whitelist 3 tập trong `query_builder.py` (field/operator/sort) + ép `int()` mọi giá trị. Ngoài tập → 422. Chuỗi lạ không bao giờ chạm tới Mongo query.
</details>

<details>
<summary><b>6. Vì sao model chỉ nạp 1 lần? Vì sao 1 worker?</b></summary>

Nạp SparkSession + PipelineModel mất hàng chục giây — nạp trong lifespan startup để mỗi request chỉ transform. Nhiều worker = nhiều SparkSession = ngốn RAM vô ích.
</details>

<details>
<summary><b>7. MapReduce nằm ở đâu, chạy kiểu gì?</b></summary>

Hadoop Streaming: mapper/reducer là script Python đọc stdin ghi stdout, nối bằng `cat | mapper | sort | reducer`. Job 1 đếm phân bố (word-count), job 2 tính mean + bảng chéo bucket → xếp hạng impact.
</details>

<details>
<summary><b>8. Ở C# vì sao chỉ có 1 HttpClient static?</b></summary>

Tạo HttpClient mỗi request → cạn socket (socket exhaustion). Async/await để UI thread không bị đứng. Tuyệt đối không `.Result`/`.Wait()` (deadlock).
</details>

<details>
<summary><b>9. `/patients/export` vì sao khai báo trước `/patients/{patient_id}`?</b></summary>

FastAPI khớp route theo thứ tự khai báo. Đảo lại → "export" bị hiểu là `patient_id="export"` → 404.
</details>

<details>
<summary><b>10. valid_row_pct khác gì field_completeness_pct?</b></summary>

`valid_row_pct` = % **DÒNG** đạt mọi ràng buộc. `field_completeness_pct` = % **Ô** dữ liệu không thiếu. Một dòng đủ ô vẫn có thể sai miền giá trị → hai chỉ số đo hai thứ khác nhau.
</details>

---

## 🔧 Xử lý sự cố

| Triệu chứng | Nguyên nhân → Cách xử lý |
|---|---|
| WinForms báo đỏ "API: KHÔNG kết nối được" | Chưa bật uvicorn → chạy Bước 4 |
| Tab có dữ liệu nhưng Dự đoán báo 503 | Thiếu `models/current/` hoặc `JAVA_HOME` sai |
| `/predict` trả 500 sau khi máy ngủ | JVM Spark chết ngầm → restart uvicorn |
| Mọi request 404 từ C# | `appsettings.json` thiếu `/api/v1/` hoặc thiếu `/` cuối |
| `ModuleNotFoundError: common` | Quên `$env:PYTHONPATH='src'` |
| Spark lỗi "class file version 61.0" | Java < 17 → đặt `JAVA_HOME` trỏ JDK 17 |
| Tab trống, `/health` báo `mongodb: down` | MongoDB chưa chạy → Bước 1 |

---

## ⚖ Lưu ý học thuật

> **Kết quả dự đoán phục vụ mục đích học thuật, không thay thế chẩn đoán y khoa.**
>
> Accuracy = 1.00 trên dataset này **không phải** bằng chứng mô hình mạnh — nhãn `level` gần như là hàm xác định của 23 chỉ số (dữ liệu tách hoàn toàn — separable). Dữ liệu thực tế có nhiễu sẽ cho kết quả thấp hơn.

---

<div align="center">

**© 2026 — Đồ án Big Data, HUFLIT**

</div>
