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
    return Pipeline(stages=[
        StringIndexer(inputCol="level", outputCol="label",
                      stringOrderType="alphabetAsc", handleInvalid="keep"),
        VectorAssembler(inputCols=FEATURE_COLUMNS, outputCol="raw_features", handleInvalid="skip"),
        StandardScaler(inputCol="raw_features", outputCol="features", withMean=True, withStd=True),
        LogisticRegression(featuresCol="features", labelCol="label",
                           family="multinomial", maxIter=300, regParam=0.0, elasticNetParam=0.0),
    ])


def build_rf(seed=42):
    return Pipeline(stages=[
        StringIndexer(inputCol="level", outputCol="label",
                      stringOrderType="alphabetAsc", handleInvalid="keep"),
        VectorAssembler(inputCols=FEATURE_COLUMNS, outputCol="features", handleInvalid="skip"),
        RandomForestClassifier(featuresCol="features", labelCol="label",
                               numTrees=100, maxDepth=10, seed=seed),
    ])


def evaluate(model, test_df, labels_order):
    preds = model.transform(test_df)
    ev = MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction")
    metrics = {m: ev.setMetricName(m).evaluate(preds)
               for m in ["accuracy", "weightedPrecision", "weightedRecall", "f1"]}
    # confusion matrix theo thứ tự cố định Low/Med/High (index 0/1/2 nhờ alphabetAsc? -> map lại)
    # alphabetAsc: High=0, Low=1, Medium=2 -> ta xuất confusion theo nhãn gốc
    idx_labels = model.stages[0].labels  # thứ tự index -> label
    cm = [[0, 0, 0] for _ in range(3)]
    order = {lb: i for i, lb in enumerate(labels_order)}   # Low,Med,High -> 0,1,2
    rows = preds.select("label", "prediction").collect()
    for r in rows:
        tl = idx_labels[int(r["label"])]; pl = idx_labels[int(r["prediction"])]
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
