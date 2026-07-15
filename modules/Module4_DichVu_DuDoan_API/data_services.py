# -*- coding: utf-8 -*-
"""Các service thao tác MongoDB cho patients / predictions / stats / quality."""
import sys, os, math
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from common.aggregations import compute_stats, compute_quality  # noqa: E402


# ---------------- patients ----------------
def list_patients(db, query: dict, sort, page: int, page_size: int) -> dict:
    page = max(1, int(page))
    page_size = min(100, max(1, int(page_size)))
    total = db.patients.count_documents(query)
    cur = (db.patients.find(query, {"_id": 0})
           .sort(sort).skip((page - 1) * page_size).limit(page_size))
    items = list(cur)
    return {"items": items, "page": page, "page_size": page_size, "total": total,
            "total_pages": max(1, math.ceil(total / page_size))}


def get_patient(db, patient_id: str):
    return db.patients.find_one({"patient_id": str(patient_id)}, {"_id": 0})


# ---------------- predictions ----------------
def save_prediction(db, doc: dict):
    db.predictions.insert_one(dict(doc))


def list_predictions(db, patient_id=None, predicted_level=None, page=1, page_size=20):
    q = {}
    if patient_id:
        q["patient_id"] = str(patient_id)
    if predicted_level:
        q["predicted_level"] = str(predicted_level).title()
    page = max(1, int(page)); page_size = min(100, max(1, int(page_size)))
    total = db.predictions.count_documents(q)
    items = list(db.predictions.find(q, {"_id": 0}).sort([("created_at", -1)])
                 .skip((page - 1) * page_size).limit(page_size))
    return {"items": items, "page": page, "page_size": page_size, "total": total,
            "total_pages": max(1, math.ceil(total / page_size))}


def get_prediction(db, prediction_id: str):
    return db.predictions.find_one({"prediction_id": str(prediction_id)}, {"_id": 0})


# ---------------- stats / quality ----------------
def get_stats(db) -> dict:
    records = list(db.patients.find({}, {"_id": 0}))
    res = compute_stats(records)
    mr = db.stats_mapreduce.find_one({}, sort=[("created_at", -1)])
    res["mapreduce_run_at"] = mr["created_at"].isoformat() if mr and mr.get("created_at") else None
    return res


def get_quality(db) -> dict:
    records = list(db.patients.find({}, {"_id": 0}))
    return compute_quality(records)
