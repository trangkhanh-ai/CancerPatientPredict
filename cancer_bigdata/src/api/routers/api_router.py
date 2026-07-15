# -*- coding: utf-8 -*-
"""Gộp các APIRouter cho gọn: health, model, predict, patients, predictions, stats, quality."""
import sys, os, uuid, datetime
from fastapi import APIRouter, Depends, HTTPException, Query
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from api.models.schemas import PredictRequest, PredictResponse, PaginatedPatients  # noqa: E402
from api.services import data_services as svc  # noqa: E402
from api.services.model_service import model_service  # noqa: E402
from api.services.correlation_service import compute_correlation  # noqa: E402
from api.query_builder import build_patient_query, build_sort  # noqa: E402
from api.deps import get_db  # noqa: E402

router = APIRouter()


@router.get("/health")
def health(db=Depends(get_db)):
    mongo_ok = True
    try:
        db.command("ping")
    except Exception:  # noqa: BLE001
        mongo_ok = False
    return {"status": "ok", "mongodb": "ok" if mongo_ok else "down",
            "model_loaded": model_service.loaded,
            "model_run_id": model_service.metadata.get("model_run_id"),
            "dataset_version": model_service.metadata.get("dataset_version")}


@router.get("/model")
def model_info():
    if not model_service.loaded:
        raise HTTPException(503, "Model chưa nạp.")
    m = model_service.metadata
    return {"algorithm": m.get("algorithm"), "feature_columns": m.get("feature_columns"),
            "label_mapping": m.get("label_mapping"), "metrics": m.get("metrics"),
            "model_run_id": m.get("model_run_id"), "trained_at": m.get("trained_at")}


@router.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest, db=Depends(get_db)):
    try:
        out = await model_service.predict(req.model_dump())
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    now = datetime.datetime.utcnow()
    resp = {"prediction_id": str(uuid.uuid4()), "patient_id": req.patient_id,
            "created_at": now.isoformat(), **out}
    doc = {**resp, "features": req.model_dump(exclude={"patient_id"}), "created_at": now}
    try:
        svc.save_prediction(db, doc)
    except Exception as e:  # noqa: BLE001
        print(f"[predict] không lưu được prediction: {e}")
    return resp


@router.get("/patients", response_model=PaginatedPatients)
def patients(db=Depends(get_db), page: int = 1, page_size: int = 20,
             patient_id: str = None, level: str = None, gender: int = None,
             age_min: int = None, age_max: int = None,
             feature: str = None, operator: str = None, value: int = None,
             min_value: int = None, max_value: int = None,
             sort_by: str = None, sort_dir: str = "asc"):
    try:
        q = build_patient_query(patient_id=patient_id, level=level, gender=gender,
                                age_min=age_min, age_max=age_max, feature=feature,
                                operator=operator, value=value, min_value=min_value, max_value=max_value)
        sort = build_sort(sort_by, sort_dir)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return svc.list_patients(db, q, sort, page, page_size)


@router.get("/patients/export")
def export_patients(db=Depends(get_db), level: str = None, gender: int = None,
                    age_min: int = None, age_max: int = None,
                    feature: str = None, operator: str = None, value: int = None,
                    min_value: int = None, max_value: int = None, limit: int = 5000):
    """Module 5 — xuất danh sách bệnh nhân (đã lọc) ra CSV."""
    import csv, io
    from fastapi.responses import StreamingResponse
    try:
        q = build_patient_query(level=level, gender=gender, age_min=age_min, age_max=age_max,
                                feature=feature, operator=operator, value=value,
                                min_value=min_value, max_value=max_value)
    except ValueError as e:
        raise HTTPException(422, str(e))
    rows = list(db.patients.find(q, {"_id": 0}).limit(min(int(limit), 20000)))
    if not rows:
        raise HTTPException(404, "Không có bản ghi nào khớp bộ lọc.")
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=patients_export.csv"})


@router.get("/patients/{patient_id}")
def patient_detail(patient_id: str, db=Depends(get_db)):
    p = svc.get_patient(db, patient_id)
    if not p:
        raise HTTPException(404, "Không tìm thấy bệnh nhân")
    return p


@router.get("/predictions")
def predictions(db=Depends(get_db), patient_id: str = None, predicted_level: str = None,
                page: int = 1, page_size: int = 20):
    return svc.list_predictions(db, patient_id, predicted_level, page, page_size)


@router.get("/predictions/{prediction_id}")
def prediction_detail(prediction_id: str, db=Depends(get_db)):
    p = svc.get_prediction(db, prediction_id)
    if not p:
        raise HTTPException(404, "Không tìm thấy prediction")
    return p


@router.get("/stats")
def stats(db=Depends(get_db)):
    return svc.get_stats(db)


@router.get("/quality")
def quality(db=Depends(get_db)):
    return svc.get_quality(db)


@router.get("/correlation")
def correlation(db=Depends(get_db)):
    """Module 2 — tương quan yếu tố nguy cơ (aggregation, không ML)."""
    records = list(db.patients.find({}, {"_id": 0}))
    res = compute_correlation(records)
    db.stats_mapreduce.update_one({"_id": "risk_correlation"}, {"$set": res}, upsert=True)
    return res
