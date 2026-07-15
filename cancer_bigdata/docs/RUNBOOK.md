# RUNBOOK — Thứ tự chạy

Chạy **từ thư mục gốc repo** (`cancer_bigdata/`) với `PYTHONPATH=src`.
Ký hiệu: ✅ = đã kiểm chứng trên máy dev · ⚠ = cần dịch vụ ngoài (MongoDB / Java+Spark).

## 0) Cài đặt

```bash
cd cancer_bigdata
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
export PYTHONPATH=src                                # PowerShell: $env:PYTHONPATH='src'
```

Windows nên đặt thêm `PYTHONUTF8=1`. PySpark 4.x yêu cầu **JDK 17+** —
đặt `JAVA_HOME` trỏ tới JDK 17 trước khi chạy bước Spark.

## 1) ✅ MapReduce — phân bố

```bash
cat data/processed/cancer_patients_ml_ready.csv \
  | python src/hadoop/mapper_distribution.py | sort \
  | python src/hadoop/reducer_distribution.py > artifacts/distributions.tsv
```

Kết quả phải có: `level|High 365` · `level|Low 303` · `level|Medium 332`.

## 2) ✅ MapReduce — tương quan yếu tố nguy cơ

```bash
cat data/processed/cancer_patients_ml_ready.csv \
  | python src/hadoop/mapper_correlation.py | sort \
  | python src/hadoop/reducer_correlation.py > artifacts/correlation.tsv
```

Kiểm nhanh: `MEAN alcohol_use High 6.83` · `MEAN alcohol_use Low 2.23`.

## 3) ⚠ MongoDB

Cần mongod đang chạy (`docker run -d -p 27017:27017 mongo:7` hoặc service local).

```bash
python src/mongodb/create_collections.py
python src/mongodb/create_indexes.py
python src/mongodb/import_patients.py --input data/processed/cancer_patients_ml_ready.csv
python src/mongodb/import_mapreduce_stats.py --input artifacts/distributions.tsv
python src/mongodb/verify_database.py          # phải in: VERIFY: PASS
```

## 4a) ✅ Metrics nhanh (không cần Spark)

```bash
python ml_analysis.py
```

Phải ra đúng: `rows=1000 unique_signatures=152 duplicated_feature_rows=848
signature_label_conflicts=0` · `rows_train=697 rows_test=303 signature_overlap=0` ·
LR acc=1.0 · RF acc=1.0. Ghi `artifacts/metrics/metrics.json` + `confusion_group_aware.csv`.

## 4b) ⚠ PySpark thật (cần JDK 17 + Spark)

```bash
spark-submit src/ml/split.py --input data/processed/cancer_patients_ml_ready.csv --out data/processed --seed 42
spark-submit src/ml/train.py --split data/processed/split_manifest.parquet --out models
mkdir -p models/current
cp -r models/runs/logistic_regression/pipeline_model models/current/pipeline_model
cp models/runs/logistic_regression/metrics.json models/current/metadata.json
```

## 5) ✅ API (đúng 1 worker)

```bash
uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

- Swagger: `http://127.0.0.1:8000/docs` — phải liệt kê đủ 11 endpoint.
- Không tăng số worker: mỗi worker tạo 1 SparkSession riêng, ngốn RAM.
- Lần `POST /predict` đầu tiên có thể mất ~60 giây (Spark codegen) — không phải treo.

## 6) ⚠ WinForms

```bash
cd winforms
dotnet build
dotnet run --project CancerBigData
```

Base URL API đọc từ `winforms/CancerBigData/appsettings.json`
(mặc định `http://localhost:8000/api/v1/` — bắt buộc có prefix `/api/v1/` và `/` cuối).

## Lỗi thường gặp

| Triệu chứng | Nguyên nhân / Cách sửa |
|---|---|
| `ModuleNotFoundError: common` | Chưa `PYTHONPATH=src` hoặc không chạy từ gốc repo |
| Spark: `class file version 61.0` | Java < 17 — đặt `JAVA_HOME` trỏ JDK 17 |
| Mọi request C# trả 404 | Base URL thiếu `/api/v1/` hoặc thiếu `/` cuối |
| `/patients/export` trả 404 "không tìm thấy bệnh nhân" | Route order sai — export phải khai báo trước `{patient_id}` |
| CSV đọc sai cột đầu | File có UTF-8 BOM — đọc bằng `encoding="utf-8-sig"` |
