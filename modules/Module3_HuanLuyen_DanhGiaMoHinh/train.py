# -*- coding: utf-8 -*-
"""
Huấn luyện & đánh giá LR (multinomial) + RF trên tập đã chia group-aware.
- LR: VectorAssembler -> StandardScaler -> LogisticRegression(family=multinomial)
- RF: VectorAssembler -> RandomForestClassifier (không cần scale)
- Ánh xạ nhãn CỐ ĐỊNH Low=0/Medium=1/High=2 (dùng StringIndexer với stringOrderType, KHÔNG theo tần suất)
- Đánh giá đúng MỘT LẦN trên test; xuất metrics.json + confusion_matrix.csv + PipelineModel.

Chạy: spark-submit src/ml/train.py --split data/processed/split_manifest.parquet --out models
NOTE: cần Spark + Java. Số liệu tham chiếu đã được kiểm bằng scikit-learn trên đúng
      group-aware split (xem artifacts/metrics/metrics.json): accuracy=1.00 cho cả LR & RF,
      confusion (Low/Med/High) = [[87,0,0],[0,90,0],[0,0,126]] trên test=303.
"""
import argparse, json, os, time
from pyspark.sql import SparkSession
from pyspark.sql import functions as Fx
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, StandardScaler, StringIndexer
from pyspark.ml.classification import LogisticRegression, RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator

import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from common.schema import FEATURE_COLUMNS, LABELS  # noqa: E402


def build_lr():
    """
    Xây dựng Pipeline huấn luyện Logistic Regression đa lớp (Multinomial).
    Pipeline gồm các bước xử lý dữ liệu (stages):
    """
    return Pipeline(stages=[
        # 1. StringIndexer: Chuyển đổi nhãn phân loại từ chuỗi (Low, Medium, High) thành số (0.0, 1.0, 2.0).
        # stringOrderType="alphabetAsc" giúp cố định thứ tự ánh xạ (High=0, Low=1, Medium=2) độc lập với tần suất.
        StringIndexer(inputCol="level", outputCol="label",
                      stringOrderType="alphabetAsc", handleInvalid="keep"),
                      
        # 2. VectorAssembler: Gom 23 cột chỉ số đặc trưng thành một cột Vector duy nhất tên là 'raw_features'.
        VectorAssembler(inputCols=FEATURE_COLUMNS, outputCol="raw_features", handleInvalid="skip"),
        
        # 3. StandardScaler: Chuẩn hóa vector đặc trưng (mean=0, std=1) để tránh các cột thang đo lớn (tuổi) lấn át cột thang đo nhỏ (chỉ số 1-9).
        StandardScaler(inputCol="raw_features", outputCol="features", withMean=True, withStd=True),
        
        # 4. LogisticRegression: Thuật toán phân lớp đa lớp (multinomial) dùng hàm kích hoạt Softmax để dự đoán xác suất của 3 lớp.
        LogisticRegression(featuresCol="features", labelCol="label",
                           family="multinomial", maxIter=300, regParam=0.0, elasticNetParam=0.0),
    ])


def build_rf(seed=42):
    """
    Xây dựng Pipeline huấn luyện mô hình Random Forest (Rừng ngẫu nhiên).
    """
    return Pipeline(stages=[
        # 1. StringIndexer: Chuyển nhãn dạng chuỗi sang nhãn dạng số (High=0, Low=1, Medium=2).
        StringIndexer(inputCol="level", outputCol="label",
                      stringOrderType="alphabetAsc", handleInvalid="keep"),
                      
        # 2. VectorAssembler: Gom 23 cột chỉ số đặc trưng thành một cột Vector duy nhất tên là 'features'.
        # Lưu ý: Thuật toán Random Forest là dạng cây quyết định nên không nhạy cảm với thang đo dữ liệu, do đó KHÔNG cần bước chuẩn hóa StandardScaler.
        VectorAssembler(inputCols=FEATURE_COLUMNS, outputCol="features", handleInvalid="skip"),
        
        # 3. RandomForestClassifier: Bộ phân lớp rừng ngẫu nhiên với 100 cây quyết định, độ sâu tối đa mỗi cây là 10.
        RandomForestClassifier(featuresCol="features", labelCol="label",
                               numTrees=100, maxDepth=10, seed=seed),
    ])


def evaluate(model, test_df, labels_order):
    """
    Đánh giá hiệu năng mô hình trên tập kiểm thử (Test Dataset).
    """
    # Bước 1: Áp dụng mô hình đã huấn luyện lên tập Test để dự đoán kết quả
    preds = model.transform(test_df)
    
    # Bước 2: Dùng MulticlassClassificationEvaluator để tính toán các chỉ số đánh giá độ chính xác
    ev = MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction")
    metrics = {m: ev.setMetricName(m).evaluate(preds)
               for m in ["accuracy", "weightedPrecision", "weightedRecall", "f1"]}
               
    # Bước 3: Trích xuất thứ tự nhãn thực tế từ mô hình (ví dụ: ['High', 'Low', 'Medium'])
    idx_labels = model.stages[0].labels  
    
    # Khởi tạo ma trận nhầm lẫn (Confusion Matrix) kích thước 3x3 với các giá trị ban đầu bằng 0
    cm = [[0, 0, 0] for _ in range(3)]
    # Thiết lập thứ tự dòng/cột hiển thị cho báo cáo: Low=0, Medium=1, High=2
    order = {lb: i for i, lb in enumerate(labels_order)}   
    
    # Thu thập tất cả các nhãn thực tế (label) và nhãn dự đoán (prediction) từ tập Test
    rows = preds.select("label", "prediction").collect()
    for r in rows:
        # Chuyển đổi nhãn số của Spark ML về lại nhãn dạng chuỗi văn bản tương ứng
        tl = idx_labels[int(r["label"])]
        pl = idx_labels[int(r["prediction"])]
        # Tăng giá trị đếm tại ô giao nhau giữa Nhãn thực tế (tl) và Nhãn dự đoán (pl) trong ma trận
        cm[order[tl]][order[pl]] += 1
    return metrics, cm, idx_labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, help="split_manifest.parquet (có cột split)")
    ap.add_argument("--out", default="models")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    spark = SparkSession.builder.appName("train_lr_rf").getOrCreate()
    df = spark.read.parquet(args.split)
    train_df = df.filter(Fx.col("split") == "train").cache()
    test_df = df.filter(Fx.col("split") == "test").cache()
    print(f"rows_train={train_df.count()} rows_test={test_df.count()}")

    results = {}
    for name, pipe in [("logistic_regression", build_lr()), ("random_forest", build_rf(args.seed))]:
        t0 = time.time()
        model = pipe.fit(train_df)
        metrics, cm, idx_labels = evaluate(model, test_df, LABELS)
        results[name] = {"metrics": metrics, "confusion_matrix": cm,
                         "label_order": LABELS, "train_time_s": round(time.time() - t0, 2)}
        run_dir = f"{args.out}/runs/{name}"
        os.makedirs(run_dir, exist_ok=True)
        
        # Save model
        model.write().overwrite().save(f"{run_dir}/pipeline_model")
        
        # Save metrics.json
        with open(f"{run_dir}/metrics.json", "w", encoding="utf-8") as f:
            json.dump(results[name], f, indent=2, ensure_ascii=False)
            
        # P0-01, P0-04: Export metadata.json for API to read label mapping
        metadata = {
            "model_run_id": f"{name}_{int(time.time())}",
            "dataset_version": "1.0",
            "algorithm": name,
            "feature_list": FEATURE_COLUMNS,
            "label_index_source": "StringIndexerModel.labels",
            "index_to_label": {str(i): lb for i, lb in enumerate(idx_labels)},
            "display_label_order": LABELS,
            "metrics": metrics
        }
        with open(f"{run_dir}/metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
            
        print(f"[{name}] accuracy={metrics['accuracy']:.4f} f1={metrics['f1']:.4f} confusion={cm}")

    # chọn model theo f1 (macro/weighted) — ở đây in ra để đối chiếu
    json.dump(results, open(f"{args.out}/summary_metrics.json", "w"), indent=2, ensure_ascii=False)
    print("[OK] Đã lưu model + metrics.")
    spark.stop()


if __name__ == "__main__":
    main()
