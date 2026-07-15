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
    
    # P0-06: Assert expected counts
    EXPECTED_TOTAL = 1000
    if total != EXPECTED_TOTAL:
        print(f"  [FAIL] total ({total}) != {EXPECTED_TOTAL}"); ok = False
    if total != uniq:
        print("  [FAIL] patient_id không unique"); ok = False

    dist = {d["_id"]: d["count"] for d in db.patients.aggregate(
        [{"$group": {"_id": "$level", "count": {"$sum": 1}}}])}
    print("  level_distribution:", dist)
    
    # P0-06: Assert expected level distribution
    expected_level = {"High": 365, "Medium": 332, "Low": 303}
    for k, v in expected_level.items():
        if dist.get(k) != v:
            print(f"  [FAIL] level {k} count ({dist.get(k)}) != {v}"); ok = False
            
    gdist = {d["_id"]: d["count"] for d in db.patients.aggregate(
        [{"$group": {"_id": "$gender", "count": {"$sum": 1}}}])}
    print("  gender_distribution:", gdist)
    
    # P0-06: Assert expected gender distribution
    expected_gender = {1: 598, 2: 402}
    for k, v in expected_gender.items():
        if gdist.get(k) != v:
            print(f"  [FAIL] gender {k} count ({gdist.get(k)}) != {v}"); ok = False

    idx = [i["name"] for i in db.patients.list_indexes()]
    print("  indexes:", idx)
    if "ux_patient_id" not in idx:
        print("  [FAIL] thiếu unique index patient_id"); ok = False

    # Check validator
    coll_info = db.command("listCollections", filter={"name": "patients"})
    if coll_info["cursor"]["firstBatch"]:
        options = coll_info["cursor"]["firstBatch"][0].get("options", {})
        if "validator" not in options:
            print("  [FAIL] missing JSON schema validator on patients collection"); ok = False
    else:
        print("  [FAIL] patients collection does not exist"); ok = False

    sample = db.patients.find_one({}, {"_id": 0}) or {}
    
    # P0-06: Assert sample has every canonical field and signature
    missing_canonical = [f for f in FEATURE_COLUMNS if f not in sample]
    if missing_canonical:
        print(f"  [FAIL] thiếu canonical fields: {missing_canonical}"); ok = False
        
    if "feature_signature" not in sample:
        print("  [FAIL] thiếu feature_signature"); ok = False
    elif len(sample["feature_signature"]) != 64:
        print("  [FAIL] feature_signature không hợp lệ (SHA-256)"); ok = False

    raw_present = [f for f in RAW_FIELDS if f in sample]
    if raw_present:
        print(f"  [FAIL] còn field RAW-case: {raw_present}"); ok = False
    else:
        print("  [OK] không có field RAW-case")

    mr = db.stats_mapreduce.count_documents({})
    print(f"  stats_mapreduce docs: {mr}")
    if mr < 1:
        print("  [FAIL] stats_mapreduce rỗng"); ok = False

    print("VERIFY:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
