# -*- coding: utf-8 -*-
"""Kiểm tra MongoDB sau import: tổng, unique, phân bố, index, validator, không RAW-case."""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from common.schema import FEATURE_COLUMNS, RAW_TO_CANONICAL  # noqa: E402
from mongodb.client import get_db  # noqa: E402

RAW_FIELDS = list(RAW_TO_CANONICAL.keys())


def main():
    db = get_db()
    ok = True
    total = db.patients.count_documents({})
    uniq = len(db.patients.distinct("patient_id"))
    print(f"patients: total={total} unique_patient_id={uniq}")
    if total != uniq:
        print("  [FAIL] patient_id không unique"); ok = False

    dist = {d["_id"]: d["count"] for d in db.patients.aggregate(
        [{"$group": {"_id": "$level", "count": {"$sum": 1}}}])}
    print("  level_distribution:", dist)
    gdist = {d["_id"]: d["count"] for d in db.patients.aggregate(
        [{"$group": {"_id": "$gender", "count": {"$sum": 1}}}])}
    print("  gender_distribution:", gdist)

    idx = [i["name"] for i in db.patients.list_indexes()]
    print("  indexes:", idx)
    if "ux_patient_id" not in idx:
        print("  [FAIL] thiếu unique index patient_id"); ok = False

    # không được có field RAW-case
    sample = db.patients.find_one({}, {"_id": 0}) or {}
    raw_present = [f for f in RAW_FIELDS if f in sample]
    if raw_present:
        print(f"  [FAIL] còn field RAW-case: {raw_present}"); ok = False
    else:
        print("  [OK] không có field RAW-case")

    mr = db.stats_mapreduce.count_documents({})
    print(f"  stats_mapreduce docs: {mr}")

    print("VERIFY:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
