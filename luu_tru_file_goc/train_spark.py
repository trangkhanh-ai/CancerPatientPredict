# -*- coding: utf-8 -*-
"""
HUẤN LUYỆN MÔ HÌNH DỰ ĐOÁN MỨC NGUY CƠ UNG THƯ BẰNG APACHE SPARK MLlib
Đầu vào : cancer_patients_ml_ready.csv (1000 bệnh nhân, 23 đặc trưng, nhãn 0/1/2)
Đầu ra  : thư mục model_spark/  (PipelineModel để FastAPI nạp) + ml_results_spark.json

Vì sao dùng Spark MLlib thay cho scikit-learn?
  - Đúng tinh thần Big Data: pipeline học máy chạy phân tán trên DataFrame của Spark,
    cùng một nền tảng với Spark SQL ở khâu truy vấn/tổng hợp.
  - VectorAssembler + Pipeline gom các bước (ghép vector -> mô hình) thành MỘT đối tượng,
    lưu ra đĩa rồi nạp lại nguyên vẹn ở phía API, không cần lắp lại từng bước thủ công.

Các bước (dễ trình bày khi vấn đáp):
  B1. Tạo SparkSession (điểm vào của mọi job Spark).
  B2. Đọc CSV thành DataFrame, ép kiểu số cho 23 cột đặc trưng, đặt cột nhãn 'label'.
  B3. VectorAssembler gộp 23 cột thành 1 cột vector 'features'.
  B4. Chia train/test 80/20 (cố định seed để chạy lại ra kết quả như nhau).
  B5. Huấn luyện 4 mô hình MLlib: LogisticRegression, DecisionTree, RandomForest, NaiveBayes.
      (Spark GBTClassifier chỉ hỗ trợ 2 lớp nên KHÔNG dùng cho bài toán 3 lớp này.)
  B6. Đánh giá trên tập test: Accuracy, Precision, Recall, F1 (trung bình có trọng số).
  B7. Kiểm chứng chéo 5-fold cho mô hình tốt nhất để xác nhận kết quả ổn định.
  B8. In ma trận nhầm lẫn và độ quan trọng đặc trưng của RandomForest.
  B9. Lưu PipelineModel tốt nhất cho API dự đoán.
"""
import json
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.classification import (LogisticRegression, DecisionTreeClassifier,
                                       RandomForestClassifier, NaiveBayes)
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder

BASE = Path(__file__).resolve().parent
ML_CSV = str(BASE / "cancer_patients_ml_ready.csv")
MODEL_OUT = str(BASE / "model_spark")          # Spark lưu mô hình dưới dạng THƯ MỤC

# ---------- B1. Tạo SparkSession ----------
spark = (SparkSession.builder
         .appName("CancerRiskTraining")
         .master("local[*]")                   # chạy local, dùng mọi nhân CPU
         .config("spark.sql.shuffle.partitions", "8")
         .getOrCreate())
spark.sparkContext.setLogLevel("ERROR")        # bớt log rác cho dễ đọc

# ---------- B2. Đọc dữ liệu ----------
df = spark.read.csv(ML_CSV, header=True, inferSchema=True)
# 23 đặc trưng = mọi cột trừ mã định danh và hai cột nhãn
features = [c for c in df.columns if c not in ("patient_id", "level", "level_encoded")]
# Ép kiểu double cho chắc chắn (tránh cột bị suy ra kiểu chuỗi)
for c in features:
    df = df.withColumn(c, F.col(c).cast("double"))
# Cột nhãn cho MLlib bắt buộc tên 'label' và kiểu double (0=Low, 1=Medium, 2=High)
df = df.withColumn("label", F.col("level_encoded").cast("double"))
print("So benh nhan:", df.count(), "| So dac trung:", len(features))
df.groupBy("level").count().show()

# ---------- B3. VectorAssembler: gộp 23 cột -> 1 vector 'features' ----------
assembler = VectorAssembler(inputCols=features, outputCol="features")

# ---------- B4. Chia train/test 80/20 ----------
train_df, test_df = df.randomSplit([0.8, 0.2], seed=42)
train_df = train_df.cache(); test_df = test_df.cache()
print("Train:", train_df.count(), "| Test:", test_df.count())

# Bốn bộ đánh giá tương ứng 4 chỉ số (đều dựa trên cột 'label' và 'prediction')
ev_acc = MulticlassClassificationEvaluator(metricName="accuracy")
ev_pre = MulticlassClassificationEvaluator(metricName="weightedPrecision")
ev_rec = MulticlassClassificationEvaluator(metricName="weightedRecall")
ev_f1  = MulticlassClassificationEvaluator(metricName="f1")

# ---------- B5+B6. Huấn luyện và đánh giá 4 mô hình ----------
def danh_gia(ten, classifier):
    # Mỗi mô hình là một Pipeline 2 bước: assembler -> bộ phân loại
    model = Pipeline(stages=[assembler, classifier]).fit(train_df)
    pred = model.transform(test_df)
    return model, {
        "model": ten,
        "accuracy":  round(ev_acc.evaluate(pred), 4),
        "precision": round(ev_pre.evaluate(pred), 4),
        "recall":    round(ev_rec.evaluate(pred), 4),
        "f1":        round(ev_f1.evaluate(pred), 4),
    }

mo_hinh = {
    "Logistic Regression": LogisticRegression(maxIter=100, family="multinomial"),
    "Decision Tree":       DecisionTreeClassifier(seed=42),
    "Random Forest":       RandomForestClassifier(numTrees=200, seed=42),
    "Naive Bayes":         NaiveBayes(),   # đặc trưng đều không âm nên dùng được
}

ket_qua, models = [], {}
for ten, clf in mo_hinh.items():
    m, kq = danh_gia(ten, clf)
    models[ten] = m
    ket_qua.append(kq)

print("\n=== BANG SO SANH MO HINH (tren tap test) ===")
for kq in ket_qua:
    print(kq)

# Chọn mô hình tốt nhất theo F1; nếu nhiều mô hình hòa nhau thì ưu tiên Random Forest
# (ensemble bền vững, lại có sẵn độ quan trọng đặc trưng để giải thích mô hình).
uu_tien = {"Random Forest": 0, "Logistic Regression": 1, "Decision Tree": 2, "Naive Bayes": 3}
best_name = sorted(ket_qua, key=lambda r: (-r["f1"], uu_tien[r["model"]]))[0]["model"]
best_model = models[best_name]
print("\nMo hinh tot nhat:", best_name)

# ---------- B7. Kiểm chứng chéo 5-fold cho mô hình tốt nhất ----------
best_clf = mo_hinh[best_name]
cv = CrossValidator(
    estimator=Pipeline(stages=[assembler, best_clf]),
    estimatorParamMaps=ParamGridBuilder().build(),   # lưới rỗng = chỉ kiểm chứng, không dò siêu tham số
    evaluator=ev_acc, numFolds=5, seed=42)
cv_model = cv.fit(df)
cv_acc = round(float(sum(cv_model.avgMetrics) / len(cv_model.avgMetrics)), 4)
print(f"5-fold CV ({best_name}) accuracy trung binh:", cv_acc)

# ---------- B8. Ma trận nhầm lẫn + độ quan trọng đặc trưng ----------
pred_best = best_model.transform(test_df)
cm_rows = (pred_best.groupBy("label", "prediction").count()
           .orderBy("label", "prediction").collect())
cm = [[0, 0, 0] for _ in range(3)]
for r in cm_rows:
    cm[int(r["label"])][int(r["prediction"])] = r["count"]
print("\nMa tran nham lan (hang=thuc te, cot=du doan) [Low,Medium,High]:")
for row in cm:
    print(row)

# Độ quan trọng đặc trưng: lấy từ Random Forest (luôn huấn luyện để giải thích mô hình)
rf_model = models["Random Forest"]
rf_stage = rf_model.stages[-1]
imp = sorted(zip(features, rf_stage.featureImportances.toArray()),
             key=lambda x: x[1], reverse=True)[:10]
importance = {k: round(float(v), 4) for k, v in imp}
print("\nTop 10 dac trung quan trong (Random Forest):")
for k, v in importance.items():
    print(f"  {k}: {v}")

# ---------- B9. Lưu PipelineModel tốt nhất cho API ----------
best_model.write().overwrite().save(MODEL_OUT)
print("\nDa luu PipelineModel ->", MODEL_OUT)

# Xuất kết quả ra JSON để cập nhật báo cáo
out = {"best_model": best_name, "comparison": ket_qua,
       "cv_accuracy": cv_acc, "confusion_matrix": cm,
       "importance_top10": importance, "features": features}
(BASE / "ml_results_spark.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
spark.stop()
print("Xong.")
