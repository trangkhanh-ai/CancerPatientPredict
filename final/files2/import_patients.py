# -*- coding: utf-8 -*-
"""
Nạp bệnh nhân từ CSV sạch vào MongoDB — IDEMPOTENT (bulk upsert theo patient_id).
Chạy lại không tạo trùng. Có tạo feature_signature, level_encoded, age_group, timestamps.
Chạy: python -m src.mongodb.import_patients --input data/processed/cancer_patients_ml_ready.csv
"""
import sys, os, argparse, csv, datetime
from pymongo import UpdateOne
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from common.schema import (FEATURE_COLUMNS, SCALE_1_9_COLUMNS, LABEL_TO_INDEX,  # noqa: E402
                           age_group_of, feature_signature)
from mongodb.client import get_db  # noqa: E402


def to_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def build_doc(row, dataset_version, now):
    doc = {"patient_id": str(row["patient_id"]).strip()}
    doc["age"] = to_int(row.get("age"))
    doc["gender"] = to_int(row.get("gender"))
    for c in SCALE_1_9_COLUMNS:
        doc[c] = to_int(row.get(c))
    doc["level"] = str(row.get("level", "")).strip().title()
    doc["age_group"] = age_group_of(doc["age"])
    doc["level_encoded"] = int(LABEL_TO_INDEX.get(doc["level"], -1))
    doc["feature_signature"] = feature_signature(doc)
    doc["dataset_version"] = dataset_version
    doc["updated_at"] = now
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--dataset-version", default=None)
    args = ap.parse_args()
    now = datetime.datetime.utcnow()
    dsv = args.dataset_version or now.strftime("v%Y%m%d")

    db = get_db()
    ops, total = [], 0
    with open(args.input, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            doc = build_doc(row, dsv, now)
            ops.append(UpdateOne({"patient_id": doc["patient_id"]},
                                 {"$set": doc, "$setOnInsert": {"created_at": now}}, upsert=True))
            total += 1
    res = db.patients.bulk_write(ops, ordered=False)
    print(f"[OK] total={total} upserted={res.upserted_count} modified={res.modified_count} "
          f"matched={res.matched_count}")
    db.dataset_versions.update_one({"_id": dsv},
                                   {"$set": {"rows": total, "created_at": now}}, upsert=True)


if __name__ == "__main__":
    main()
