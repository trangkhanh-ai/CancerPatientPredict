# Hệ thống dự đoán mức độ mắc bệnh ung thư (Big Data)

Đồ án môn **Lập trình Python ứng dụng (Big Data)** — HUFLIT
GVHD: TS. Võ Thị Hồng Tuyết
Nhóm: **Nguyễn Bảo Duy (24DH190309)** · **Trang Mai Quốc Khánh (24DH190081)**

## Tổng quan

Hệ thống nhận 23 chỉ số của bệnh nhân (tuổi, giới tính và 21 chỉ số nguy cơ thang 1–9),
dự đoán mức độ mắc bệnh ung thư (**Low / Medium / High**), đồng thời cung cấp
thống kê, tìm kiếm bệnh nhân theo bộ lọc từng chỉ số, xếp hạng yếu tố nguy cơ và
báo cáo chất lượng dữ liệu.

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

**5 module:**

| # | Module | Công nghệ |
|---|---|---|
| 1 | Thu thập & Chuẩn hoá dữ liệu (Data Ingestion & Preparation) | Hadoop MapReduce, PySpark, MongoDB |
| 2 | Phân tích Dữ liệu (Data Analytics) — 2 job MapReduce | Hadoop MapReduce |
| 3 | Huấn luyện & Đánh giá mô hình (Model Training & Evaluation) | PySpark ML (Logistic Regression) |
| 4 | Dịch vụ Dự đoán (Prediction Service) | FastAPI |
| 5 | Ứng dụng Người dùng (Desktop Client) | C# WinForms (.NET 8) |

## Dataset

- Nguồn: `cancer patient data sets.xlsx` — Kaggle, tác giả **Rishi Damarla (2021)**
  (`data/raw/cancer_patient_data_sets.xlsx`).
- **1000 bệnh nhân × 25 cột** (patient_id, age, gender, 22 chỉ số thang 1–9, nhãn level).
- Phân bố nhãn: **High = 365 · Medium = 332 · Low = 303**.
- Chất lượng: 0 sai thang · 0 thiếu · 0 trùng patient_id → giữ 1000/1000 dòng.
- ⚠ Chỉ có **152 vector 23-đặc-trưng duy nhất** (848 dòng trùng vector) → bắt buộc
  **group-aware split** theo `feature_signature` khi huấn luyện (chi tiết:
  [docs/ML_EVALUATION.md](docs/ML_EVALUATION.md)).

## Quickstart

```bash
cd cancer_bigdata
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
export PYTHONPATH=src                                # Windows: $env:PYTHONPATH='src'

# 1) MapReduce — phân bố (level|High 365 / Low 303 / Medium 332)
cat data/processed/cancer_patients_ml_ready.csv \
  | python src/hadoop/mapper_distribution.py | sort \
  | python src/hadoop/reducer_distribution.py > artifacts/distributions.tsv

# 2) MapReduce — tương quan yếu tố nguy cơ
cat data/processed/cancer_patients_ml_ready.csv \
  | python src/hadoop/mapper_correlation.py | sort \
  | python src/hadoop/reducer_correlation.py > artifacts/correlation.tsv

# 3) MongoDB (cần mongod: docker run -d -p 27017:27017 mongo:7)
python src/mongodb/create_collections.py
python src/mongodb/create_indexes.py
python src/mongodb/import_patients.py --input data/processed/cancer_patients_ml_ready.csv
python src/mongodb/import_mapreduce_stats.py --input artifacts/distributions.tsv
python src/mongodb/verify_database.py        # phải in: VERIFY: PASS

# 4) Kiểm chứng ML nhanh (không cần Spark) — 152 signatures · 848 trùng · overlap=0 · acc=1.0
python ml_analysis.py

# 5) API (đúng 1 worker — mỗi worker tạo 1 SparkSession)
uvicorn src.api.main:app --host 127.0.0.1 --port 8000
# Swagger: http://127.0.0.1:8000/docs

# 6) WinForms
cd winforms && dotnet build && dotnet run --project CancerBigData
```

Thứ tự chạy đầy đủ (kèm bước Spark thật): [docs/RUNBOOK.md](docs/RUNBOOK.md).

## Yêu cầu môi trường

- Python 3.10+ (`requirements.txt`); **PySpark 4.x cần JDK 17+** (đặt `JAVA_HOME` trỏ JDK 17).
- MongoDB chạy ở `localhost:27017` (đổi qua `.env`).
- .NET 8 SDK trở lên cho WinForms (project đặt `RollForward=LatestMajor` nên chạy được
  trên runtime mới hơn).

## Tài liệu

| File | Nội dung |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Kiến trúc 5 module + luồng dữ liệu |
| [docs/API.md](docs/API.md) | Hợp đồng API — 11 endpoint, whitelist, mã lỗi |
| [docs/ML_EVALUATION.md](docs/ML_EVALUATION.md) | Số liệu ML đã kiểm chứng + kết luận trung thực (separable) |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | Thứ tự chạy từng bước |

## Lưu ý học thuật

> Kết quả dự đoán phục vụ mục đích **học thuật**, không thay thế chẩn đoán y khoa.
> Accuracy = 1.00 trên dataset này **không phải** bằng chứng mô hình mạnh — nhãn `level`
> gần như là hàm xác định của 23 chỉ số (dữ liệu tách hoàn toàn — separable).
> Xem phân tích đầy đủ trong [docs/ML_EVALUATION.md](docs/ML_EVALUATION.md).
