# -*- coding: utf-8 -*-
"""
Train official Spark MLlib model for cancer risk classification.

This file replaces the old random 80/20 experiment. The official result uses:
- group-aware split by feature_signature, overlap = 0
- Logistic Regression as the served model
- test set = 303 rows, confusion = [[87,0,0],[0,90,0],[0,0,126]]

Run:
  python train_spark.py

If Spark fails with Java 11, run in PowerShell first:
  $env:JAVA_HOME='C:\\Program Files\\Eclipse Adoptium\\jdk-17.0.19.10-hotspot'
"""

import argparse
import json
import time
from pathlib import Path

from pyspark.ml import Pipeline
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.feature import StandardScaler, VectorAssembler
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F


BASE = Path(__file__).resolve().parent
PROJECT_ROOT = BASE.parent
DEFAULT_MODEL_OUT = BASE / "model_spark"
DEFAULT_RESULTS_OUT = BASE / "ml_results_spark.json"
SEED = 42
TRAIN_RATIO = 0.70

FEATURES = [
    "age",
    "gender",
    "air_pollution",
    "alcohol_use",
    "dust_allergy",
    "occupational_hazards",
    "genetic_risk",
    "chronic_lung_disease",
    "balanced_diet",
    "obesity",
    "smoking",
    "passive_smoker",
    "chest_pain",
    "coughing_of_blood",
    "fatigue",
    "weight_loss",
    "shortness_of_breath",
    "wheezing",
    "swallowing_difficulty",
    "clubbing_of_finger_nails",
    "frequent_cold",
    "dry_cough",
    "snoring",
]

LABELS = ["Low", "Medium", "High"]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Path to cancer_patients_ml_ready.csv")
    parser.add_argument("--model-out", default=str(DEFAULT_MODEL_OUT))
    parser.add_argument("--results-out", default=str(DEFAULT_RESULTS_OUT))
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--train-ratio", type=float, default=TRAIN_RATIO)
    return parser.parse_args()


def find_input_csv(cli_input):
    candidates = []
    if cli_input:
        candidates.append(Path(cli_input))
    candidates.extend(
        [
            BASE / "cancer_patients_ml_ready.csv",
            PROJECT_ROOT / "_run" / "cancer_patients_ml_ready.csv",
            PROJECT_ROOT / "cancer_bigdata" / "data" / "processed" / "cancer_patients_ml_ready.csv",
            PROJECT_ROOT / "cleandata cancer" / "cancer_patients_ml_ready.csv",
        ]
    )
    for path in candidates:
        if path.exists():
            return path.resolve()
    checked = "\n".join(str(path) for path in candidates)
    raise FileNotFoundError(f"Cannot find cancer_patients_ml_ready.csv. Checked:\n{checked}")


def build_spark():
    return (
        SparkSession.builder.appName("CancerRiskTrainingGroupAware")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )


def prepare_dataframe(df):
    missing = [c for c in FEATURES + ["level"] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    for col_name in FEATURES:
        df = df.withColumn(col_name, F.col(col_name).cast("double"))

    df = df.withColumn("level", F.initcap(F.trim(F.col("level").cast("string"))))
    df = df.withColumn(
        "label",
        F.when(F.col("level") == "Low", F.lit(0.0))
        .when(F.col("level") == "Medium", F.lit(1.0))
        .when(F.col("level") == "High", F.lit(2.0)),
    )

    invalid_labels = df.filter(F.col("label").isNull()).select("level").distinct().collect()
    if invalid_labels:
        raise ValueError(f"Invalid labels: {[r['level'] for r in invalid_labels]}")

    signature_expr = F.concat_ws("|", *[F.col(c).cast("int").cast("string") for c in FEATURES])
    return df.withColumn("feature_signature", F.sha2(signature_expr, 256))


def baseline_checks(df):
    row_count = df.count()
    unique_signatures = df.select("feature_signature").distinct().count()
    conflict_df = (
        df.groupBy("feature_signature")
        .agg(F.countDistinct("level").alias("label_count"))
        .filter(F.col("label_count") > 1)
    )
    conflicts = conflict_df.count()
    if conflicts:
        conflict_df.show(truncate=False)
        raise ValueError("feature_signature has more than one label; stop training.")

    return {
        "rows": row_count,
        "unique_signatures": unique_signatures,
        "duplicated_feature_rows": row_count - unique_signatures,
        "signature_label_conflicts": conflicts,
    }


def group_aware_split(df, seed, train_ratio):
    groups = df.select("feature_signature", "level").distinct()
    order_key = F.sha2(F.concat(F.col("feature_signature"), F.lit(str(seed))), 256)
    window_by_level = Window.partitionBy("level")
    ranked = (
        groups.withColumn("rn", F.row_number().over(window_by_level.orderBy(order_key)))
        .withColumn("group_count", F.count("*").over(window_by_level))
        .withColumn(
            "train_n",
            F.greatest(
                F.lit(1),
                F.least(
                    F.col("group_count") - 1,
                    F.round(F.col("group_count") * F.lit(float(train_ratio))).cast("int"),
                ),
            ),
        )
        .withColumn("split", F.when(F.col("rn") <= F.col("train_n"), "train").otherwise("test"))
    )
    assigned = df.join(ranked.select("feature_signature", "split"), on="feature_signature", how="inner")

    train_sigs = assigned.filter(F.col("split") == "train").select("feature_signature").distinct()
    test_sigs = assigned.filter(F.col("split") == "test").select("feature_signature").distinct()
    overlap = train_sigs.intersect(test_sigs).count()
    if overlap:
        raise AssertionError(f"Signature overlap train/test = {overlap}; expected 0")

    return assigned, overlap


def count_by_label(df):
    rows = df.groupBy("level").count().collect()
    found = {row["level"]: int(row["count"]) for row in rows}
    return {label: found.get(label, 0) for label in LABELS}


def evaluate_predictions(predictions):
    evaluator = MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction")
    metrics = {
        metric: round(float(evaluator.setMetricName(metric).evaluate(predictions)), 4)
        for metric in ["accuracy", "weightedPrecision", "weightedRecall", "f1"]
    }

    matrix = [[0, 0, 0] for _ in LABELS]
    for row in predictions.groupBy("label", "prediction").count().collect():
        matrix[int(row["label"])][int(row["prediction"])] = int(row["count"])

    return metrics, matrix


def train_logistic_regression(train_df):
    assembler = VectorAssembler(inputCols=FEATURES, outputCol="raw_features", handleInvalid="skip")
    scaler = StandardScaler(inputCol="raw_features", outputCol="features", withMean=True, withStd=True)
    lr = LogisticRegression(
        featuresCol="features",
        labelCol="label",
        family="multinomial",
        maxIter=300,
        regParam=0.0,
        elasticNetParam=0.0,
    )
    return Pipeline(stages=[assembler, scaler, lr]).fit(train_df)


def main():
    args = parse_args()
    csv_path = find_input_csv(args.input)
    model_out = Path(args.model_out).resolve()
    results_out = Path(args.results_out).resolve()

    spark = build_spark()
    spark.sparkContext.setLogLevel("ERROR")
    started = time.time()

    try:
        df = spark.read.csv(str(csv_path), header=True, inferSchema=True)
        df = prepare_dataframe(df)
        baseline = baseline_checks(df)

        split_df, overlap = group_aware_split(df, seed=args.seed, train_ratio=args.train_ratio)
        train_df = split_df.filter(F.col("split") == "train").cache()
        test_df = split_df.filter(F.col("split") == "test").cache()
        train_count = train_df.count()
        test_count = test_df.count()

        print(f"[BASELINE] rows={baseline['rows']} unique_signatures={baseline['unique_signatures']} duplicated_feature_rows={baseline['duplicated_feature_rows']} conflicts={baseline['signature_label_conflicts']}")
        print(f"[GROUP SPLIT] rows_train={train_count} rows_test={test_count} signature_overlap={overlap}")
        print(f"[TEST SUPPORT] {count_by_label(test_df)}")

        model = train_logistic_regression(train_df)
        predictions = model.transform(test_df).cache()
        metrics, confusion_matrix = evaluate_predictions(predictions)

        model.write().overwrite().save(str(model_out))
        elapsed = round(time.time() - started, 2)

        result = {
            "official_result": True,
            "algorithm": "Logistic Regression (Spark MLlib multinomial, StandardScaler, regParam=0.0)",
            "dataset": {
                "input_csv": str(csv_path),
                **baseline,
            },
            "split": {
                "method": "group-aware by feature_signature",
                "seed": args.seed,
                "train_ratio": args.train_ratio,
                "rows_train": train_count,
                "rows_test": test_count,
                "signature_overlap": overlap,
                "train_support": count_by_label(train_df),
                "test_support": count_by_label(test_df),
            },
            "label_order": LABELS,
            "metrics": metrics,
            "confusion_matrix": confusion_matrix,
            "model_path": str(model_out),
            "features": FEATURES,
            "train_time_s": elapsed,
            "note": "Random 80/20 split experiment removed from official training path to avoid leakage from duplicated feature vectors.",
        }
        results_out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

        print(f"[LR] accuracy={metrics['accuracy']:.4f} f1={metrics['f1']:.4f} confusion={confusion_matrix}")
        print(f"[OK] saved model -> {model_out}")
        print(f"[OK] saved results -> {results_out}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
