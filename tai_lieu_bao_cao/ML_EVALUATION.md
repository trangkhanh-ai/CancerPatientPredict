# ML Evaluation — Kết quả THẬT (đã kiểm chứng)

> Nguồn số liệu: `artifacts/metrics/metrics.json`, `artifacts/metrics/confusion_group_aware.csv`.
> Tính bằng scikit-learn trên **đúng group-aware split** (proxy kiểm chứng cho pipeline PySpark
> `src/ml/train.py`). Các con số dưới đây **không gõ tay**, lấy từ file output.

## 1. Profiling dữ liệu (khớp baseline master prompt)
| Chỉ tiêu | Giá trị |
|---|---|
| Số dòng | 1000 |
| Số vector 23 đặc trưng **duy nhất** | **152** |
| Số dòng **trùng** vector đặc trưng | **848** |
| feature_signature gắn >1 nhãn (xung đột) | **0** |
| Trùng `patient_id` | 0 · Missing | 0 |

## 2. Chia train/test GROUP-AWARE (chống leakage)
Chia theo **group = `feature_signature`** (không theo dòng), seed=42, ~70/30 theo group trong từng lớp:

| | rows | groups | Low | Medium | High |
|---|---|---|---|---|---|
| train | 697 | 106 | 216 | 242 | 239 |
| test | 303 | 46 | 87 | 90 | 126 |

**signature_overlap(train,test) = 0** (đã assert).

## 3. Kết quả trên tập test (group-aware)
| Mô hình | Accuracy | Macro-F1 | Weighted-F1 |
|---|---|---|---|
| Logistic Regression | **1.0000** | **1.0000** | **1.0000** |
| Random Forest | **1.0000** | **1.0000** | **1.0000** |

Ma trận nhầm lẫn (hàng = thật, cột = dự đoán; thứ tự Low/Medium/High), **cả hai mô hình**:
```
          pred_Low  pred_Medium  pred_High
true_Low       87           0          0
true_Medium     0          90          0
true_High       0           0        126
```

## 4. Kết luận trung thực (điểm mấu chốt để vấn đáp)
- Ta **đã áp dụng group-aware split** để loại rủi ro leakage do 848 dòng trùng vector — đây là
  cách làm đúng phương pháp luận.
- **Nhưng ngay cả khi overlap = 0**, cả LR và RF vẫn đạt accuracy = 1.00. Cùng với việc **0 xung
  đột nhãn** trên 152 vector, điều này cho thấy: trong dataset học thuật này, **`level` là hàm
  xác định của 23 chỉ số** → dữ liệu **tách hoàn toàn (separable)**.
- Vì vậy điểm tuyệt đối **KHÔNG phải bằng chứng mô hình mạnh về mặt lâm sàng**, mà là **đặc tính
  của dataset**. Trên dữ liệu thực (có nhiễu), kết quả sẽ thấp hơn.
- So sánh: random-split theo dòng cũng cho 1.00 — ở dataset separable này leakage không làm thay
  đổi con số, nhưng group-aware vẫn là cách trình bày đúng để bảo vệ tính hợp lệ của đánh giá.

## 5. NOT VERIFIED trong môi trường chat
- Chưa chạy `src/ml/train.py` trên Spark thật (thiếu Java/Spark ở đây). Số liệu trên là từ
  scikit-learn trên **cùng** group-aware split; kỳ vọng Spark cho kết quả tương đương.
  Lệnh chạy thật: `spark-submit src/ml/split.py ...` rồi `spark-submit src/ml/train.py ...`.
