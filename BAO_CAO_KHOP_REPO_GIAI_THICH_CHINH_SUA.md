# Giải thích chỉnh sửa báo cáo khớp repo

## File đầu vào

- `C:\Users\dzyuu\Downloads\BaoCao_UngThu_BigData_KhopRepo.docx`

## File đã tạo

- `C:\Users\dzyuu\Downloads\BaoCao_UngThu_BigData_KhopRepo_DaBoSung.docx`
- `tai_lieu_bao_cao/BaoCao_UngThu_BigData_KhopRepo_DaBoSung.docx`

## Những điểm đã phát hiện

1. Báo cáo cũ ghi `commit e94b59e8fa`; workspace hiện tại không phải git repo, nên đổi sang mô tả repo cục bộ `D:\1BigDataproject1\final`.
2. Báo cáo cũ nói PySpark canonical chưa chạy lại và `models/current` còn 0,9668/test=301.
3. Repo hiện tại đã được chạy lại Spark canonical:
   - `rows_train=697`, `rows_test=303`
   - `signature_overlap=0`
   - Logistic Regression: `accuracy=1.0000`, `f1=1.0000`
   - confusion matrix: `[[87,0,0],[0,90,0],[0,0,126]]`
4. `models/current/metadata.json`, `models/runs/logistic_regression/metrics.json`, `_run/ml_results_spark.json` và `final+spark/ml_results_spark.json` đã cùng nói Logistic Regression group-aware.
5. API code có 11 route dưới `/api/v1`, nên sửa mô tả 10 endpoint thành 11 endpoint trong tài liệu repo và báo cáo.

## Những gì đã sửa trong DOCX

- Cập nhật phần tóm tắt, phạm vi, kiến trúc, kết quả mô hình, kết luận và phụ lục trạng thái.
- Cập nhật bảng Artifact mô hình: canonical metrics, Spark `models/current`, Spark `final+spark` đều 303 test, overlap 0, acc 1.0.
- Cập nhật bảng đối chiếu yêu cầu đề bài: dự đoán mức độ đã có artifact đồng bộ.
- Cập nhật bảng vấn đề còn lại: bỏ “chưa rerun PySpark canonical”, thay bằng các việc thật còn phải làm trước demo như chạy MongoDB/FastAPI/WinForms và chụp lại UI.
- Cập nhật checklist nộp: PySpark/model đã rerun canonical; cần giữ metadata và JSON kết quả.

## Lệnh Spark đã chạy

```powershell
$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot'
$env:PYTHONUTF8='1'
$env:PYTHONPATH='src'
python src\ml\split.py --input data\processed\cancer_patients_ml_ready.csv --out data\processed
python src\ml\train.py --split data\processed\split_manifest.parquet --out models
```
