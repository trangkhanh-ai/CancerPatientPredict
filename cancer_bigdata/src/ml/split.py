# -*- coding: utf-8 -*-
"""
Chia train/test CHỐNG LEAKAGE theo group = feature_signature (PySpark).
Lý do: dataset có nhiều dòng trùng vector 23 đặc trưng (baseline: 152 vector duy nhất /
848 dòng trùng). Random split theo dòng sẽ đưa cùng một cấu hình sang cả train & test → leakage.

Chạy:  spark-submit src/ml/split.py --input <clean.csv/parquet> --out data/processed
Yêu cầu: mỗi feature_signature chỉ ứng với ĐÚNG MỘT level (đã kiểm ở tiền xử lý).
"""
import argparse
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as Fx

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from common.schema import FEATURE_COLUMNS, LABELS  # noqa: E402


def add_feature_signature(df):
    expr = Fx.concat_ws("|", *[Fx.col(c).cast("string") for c in FEATURE_COLUMNS])
    return df.withColumn("feature_signature", Fx.sha2(expr, 256))


def assert_no_conflict(df):
    conflict = (df.groupBy("feature_signature")
                  .agg(Fx.countDistinct("level").alias("n"))
                  .filter("n > 1"))
    if conflict.count() > 0:
        conflict.show(truncate=False)
        raise ValueError("Có feature_signature gắn >1 level → dừng training (xem quarantine).")


def group_aware_split(df, seed=42, train_ratio=0.70):
    """Chia theo GROUP (feature_signature), giữ tỉ lệ lớp, đảm bảo mỗi lớp có mặt ở cả 2 phía."""
    groups = df.select("feature_signature", "level").distinct()
    # thứ tự deterministic theo sha256(signature + seed) trong từng lớp
    # (CÙNG quy tắc với ml_analysis.py — nối trực tiếp, KHÔNG có dấu '|',
    #  để tái lập đúng split đã kiểm chứng train=697/test=303)
    w = Window.partitionBy("level").orderBy(
        Fx.sha2(Fx.concat(Fx.col("feature_signature"), Fx.lit(str(seed))), 256))
    ranked = (groups
              .withColumn("rn", Fx.row_number().over(w))
              .withColumn("gc", Fx.count("*").over(Window.partitionBy("level"))))
    # train_n nằm trong [1, gc-1] để mỗi lớp đều có group ở train và test
    ranked = ranked.withColumn(
        "train_n", Fx.greatest(Fx.lit(1),
                   Fx.least(Fx.col("gc") - 1, Fx.round(Fx.col("gc") * train_ratio).cast("int"))))
    ranked = ranked.withColumn("split", Fx.when(Fx.col("rn") <= Fx.col("train_n"), "train").otherwise("test"))
    assign = ranked.select("feature_signature", "split")
    out = df.join(assign, on="feature_signature", how="left")

    # kiểm tra overlap = 0
    tr = set(r.feature_signature for r in out.filter("split='train'").select("feature_signature").distinct().collect())
    te = set(r.feature_signature for r in out.filter("split='test'").select("feature_signature").distinct().collect())
    overlap = len(tr & te)
    assert overlap == 0, f"Signature overlap train/test = {overlap} (phải = 0)"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", default="data/processed")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    spark = SparkSession.builder.appName("group_aware_split").getOrCreate()
    df = spark.read.option("header", True).option("inferSchema", True).csv(args.input)
    df = add_feature_signature(df)
    assert_no_conflict(df)
    out = group_aware_split(df, seed=args.seed)

    for lv in LABELS:
        for sp in ("train", "test"):
            print(f"{sp} {lv}: {out.filter((Fx.col('level')==lv) & (Fx.col('split')==sp)).count()}")
    out.write.mode("overwrite").parquet(f"{args.out}/split_manifest.parquet")
    print(f"[OK] Đã ghi split_manifest.parquet · overlap=0")
    spark.stop()


if __name__ == "__main__":
    main()
