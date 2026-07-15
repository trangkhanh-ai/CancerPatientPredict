# ML Evaluation — Kết quả THẬT (đã kiểm chứng)

> Nguồn số liệu: `artifacts/metrics/metrics.json`, `artifacts/metrics/confusion_group_aware.csv`
> (sinh bởi `python ml_analysis.py`). Tính bằng scikit-learn trên **đúng group-aware split**
> (proxy kiểm chứng cho pipeline PySpark `src/ml/train.py`). Các con số dưới đây
> **không gõ tay**, lấy từ file output.

## 1. Profiling dữ liệu

| Chỉ tiêu | Giá trị |
|---|---|
| Số dòng | 1000 |
| Số vector 23 đặc trưng **duy nhất** | **152** |
| Số dòng **trùng** vector đặc trưng | **848** |
| feature_signature gắn >1 nhãn (xung đột) | **0** |
| Trùng `patient_id` | 0 · Missing: 0 |

## 2. Chia train/test GROUP-AWARE (chống leakage)

Chia theo **group = `feature_signature`** (không theo dòng), seed=42, ~70/30 theo group
trong từng lớp; thứ tự nhóm deterministic theo `sha256(signature + seed)` — cùng quy tắc
trong `ml_analysis.py` và `src/ml/split.py`:

| | rows | groups | Low | Medium | High |
|---|---|---|---|---|---|
| train | 697 | 106 | 216 | 242 | 239 |
| test | 303 | 46 | 87 | 90 | 126 |

**signature_overlap(train, test) = 0** (đã assert trong code).

## 3. Kết quả trên tập test (group-aware)

| Mô hình | Accuracy | Macro-F1 |
|---|---|---|
| Logistic Regression | **1.0000** | **1.0000** |
| Random Forest | **1.0000** | **1.0000** |

> **Ghi chú trình bày:** báo cáo chính chỉ trình bày chi tiết **Logistic Regression**
> (mô hình được triển khai). Random Forest là **đối chứng nội bộ**: hai thuật toán khác họ
> (tuyến tính vs cây) cho kết quả tương đương, khẳng định điểm số cao đến từ đặc tính tách
> hoàn toàn của dữ liệu chứ không phải do lựa chọn thuật toán.

Ma trận nhầm lẫn (hàng = thật, cột = dự đoán; thứ tự Low/Medium/High), **cả hai mô hình**:

```
          pred_Low  pred_Medium  pred_High
true_Low       87           0          0
true_Medium     0          90          0
true_High       0           0        126
```

## 4. Kết luận trung thực (điểm mấu chốt để vấn đáp)

- Ta **đã áp dụng group-aware split** để loại rủi ro leakage do 848 dòng trùng vector —
  đây là cách làm đúng phương pháp luận.
- **Nhưng ngay cả khi overlap = 0**, cả LR và RF vẫn đạt accuracy = 1.00. Cùng với việc
  **0 xung đột nhãn** trên 152 vector, điều này cho thấy: trong dataset học thuật này,
  **`level` gần như là hàm xác định của 23 chỉ số** → dữ liệu **tách hoàn toàn (separable)**.
- Vì vậy điểm tuyệt đối **KHÔNG do leakage**, nhưng cũng **KHÔNG phải bằng chứng mô hình
  giỏi về mặt lâm sàng** — đó là **đặc tính của dataset**. Trên dữ liệu thực (có nhiễu),
  kết quả sẽ thấp hơn.

## 5. Ghi chú tái lập (quan trọng)

- Kết quả group-aware **nhạy với cách chọn nhóm vào train/test**: cùng seed 42 nhưng
  quy tắc xếp thứ tự nhóm khác nhau sẽ cho tập test khác nhau (152 nhóm là rất ít).
  Ví dụ một lần chạy Spark trước đây dùng khoá sắp xếp khác (`sha256(signature|seed)`)
  cho test = 301 dòng và LR accuracy 0.9668 / RF 0.9336 — vẫn là split chống leakage hợp lệ,
  chỉ khác cách chia nhóm. Repo hiện tại đã chạy lại theo split canonical 697/303.
- Từ phiên bản này, `ml_analysis.py` và `src/ml/split.py` dùng **cùng một quy tắc
  canonical** `sha256(signature + seed)` để mọi lần chạy tái lập đúng bảng ở mục 2–3.

## 6. Đã chạy lại Spark canonical

- Đã chạy lại `src/ml/split.py` + `src/ml/train.py` trên Spark sau khi đồng bộ quy tắc
  split canonical. Kết quả Spark khớp mục 2-3: `rows_train=697`, `rows_test=303`,
  `accuracy=1.0000`, `f1=1.0000`, confusion `[[87,0,0],[0,90,0],[0,0,126]]`.
  Lệnh tái lập (cần JDK 17):

```bash
spark-submit src/ml/split.py --input data/processed/cancer_patients_ml_ready.csv --out data/processed --seed 42
spark-submit src/ml/train.py --split data/processed/split_manifest.parquet --out models
```
