# -*- coding: utf-8 -*-
"""
API /stats & /quality — SCHEMA CANONICAL snake_case (thay bản RAW-case cũ).
- /quality tách rõ 2 khái niệm: valid_row_pct (dòng hợp lệ) vs field_completeness_pct (ô không thiếu).
- CORS giới hạn origin cấu hình, KHÔNG dùng '*'.
Chạy: uvicorn api_stats_quality:app --host 127.0.0.1 --port 8000
"""
import os, hashlib
from typing import List, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "cancer_project")
CORS_ORIGINS = os.getenv("API_CORS_ORIGINS", "http://localhost").split(",")

FEATURE_COLUMNS = ["age","gender","air_pollution","alcohol_use","dust_allergy","occupational_hazards",
 "genetic_risk","chronic_lung_disease","balanced_diet","obesity","smoking","passive_smoker",
 "chest_pain","coughing_of_blood","fatigue","weight_loss","shortness_of_breath","wheezing",
 "swallowing_difficulty","clubbing_of_finger_nails","frequent_cold","dry_cough","snoring"]
SCALE_COLS = [c for c in FEATURE_COLUMNS if c not in ("age", "gender")]
INDICATORS = SCALE_COLS
LABELS = ["Low", "Medium", "High"]
CHART_INDICATORS = ["smoking", "coughing_of_blood", "obesity", "alcohol_use", "genetic_risk"]
CHECK_COLS = FEATURE_COLUMNS + ["level"]   # cột được kiểm completeness
AGE_BINS = [(0,19,"<20"),(20,29,"20-29"),(30,39,"30-39"),(40,49,"40-49"),(50,59,"50-59"),(60,200,">=60")]


def _num(v):
    try: return float(v)
    except (TypeError, ValueError): return None

def _age_group(a):
    n=_num(a)
    if n is None: return "N/A"
    for lo,hi,lab in AGE_BINS:
        if lo<=n<=hi: return lab
    return ">=60"

def _signature(r):
    try:
        return hashlib.sha256("|".join(str(int(float(r[c]))) for c in FEATURE_COLUMNS).encode()).hexdigest()
    except (KeyError, TypeError, ValueError):
        return None


def compute_stats(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    total=len(records)
    level={l:0 for l in LABELS}; gender={"Nam":0,"Nữ":0,"Khác":0}; age={b[2]:0 for b in AGE_BINS}
    sums={l:{c:0.0 for c in INDICATORS} for l in LABELS}; cnt={l:0 for l in LABELS}; alls={c:0.0 for c in INDICATORS}
    for r in records:
        lv=str(r.get("level","")).strip().title()
        if lv in level:
            level[lv]+=1; cnt[lv]+=1
            for c in INDICATORS:
                v=_num(r.get(c));  sums[lv][c]+= v if v is not None else 0
        g=_num(r.get("gender")); gender["Nam" if g==1 else "Nữ" if g==2 else "Khác"]+=1
        age[_age_group(r.get("age"))]=age.get(_age_group(r.get("age")),0)+1
        for c in INDICATORS:
            v=_num(r.get(c));  alls[c]+= v if v is not None else 0
    avg_lv={c:{l:round(sums[l][c]/cnt[l],2) if cnt[l] else 0.0 for l in LABELS} for c in INDICATORS}
    return {"total":total,"level_distribution":level,
            "gender_distribution":{k:v for k,v in gender.items() if v or k!="Khác"},
            "age_group_distribution":age,"avg_indicators_by_level":avg_lv,
            "avg_indicators_overall":{c:round(alls[c]/total,2) if total else 0.0 for c in INDICATORS},
            "chart_indicators":CHART_INDICATORS,"source":"mongodb.patients"}


def compute_quality(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    total=len(records)
    inv_age=inv_gender=inv_scale=inv_level=missing_cells=0
    valid_rows=0; seen_pid=set(); dup_pid=0; full_rows={}; sigs={}
    for r in records:
        bad=False
        if _num(r.get("gender")) not in (1.0,2.0): inv_gender+=1; bad=True
        a=_num(r.get("age"))
        if a is None or not (0<=a<=120): inv_age+=1; bad=True
        if str(r.get("level","")).strip().title() not in LABELS: inv_level+=1; bad=True
        for c in SCALE_COLS:
            v=_num(r.get(c))
            if v is None or not (1<=v<=9): inv_scale+=1; bad=True
        for c in CHECK_COLS:
            val=r.get(c)
            if val is None or str(val).strip()=="" : missing_cells+=1
        pid=r.get("patient_id")
        if pid in seen_pid: dup_pid+=1
        else: seen_pid.add(pid)
        key=tuple(r.get(c) for c in CHECK_COLS); full_rows[key]=full_rows.get(key,0)+1
        sg=_signature(r)
        if sg: sigs.setdefault(sg,set()).add(str(r.get("level","")).strip().title())
        if not bad: valid_rows+=1
    dup_full=sum(v-1 for v in full_rows.values() if v>1)
    uniq_sig=len(sigs); dup_sig_rows=total-uniq_sig
    conflicts=sum(1 for s in sigs.values() if len(s)>1)
    checked_cells=total*len(CHECK_COLS)
    valid_row_pct=round(valid_rows/total*100,2) if total else 0.0
    field_completeness=round((1-missing_cells/checked_cells)*100,2) if checked_cells else 0.0
    checks=[("invalid_age",inv_age),("invalid_gender",inv_gender),("invalid_risk_scale",inv_scale),
            ("invalid_level",inv_level),("duplicate_patient_id",dup_pid),
            ("duplicate_full_row",dup_full),("signature_label_conflicts",conflicts)]
    return {"row_count_raw":total,"row_count_valid":valid_rows,"row_count_invalid":total-valid_rows,
            "valid_row_pct":valid_row_pct,"field_completeness_pct":field_completeness,
            "column_count":len(CHECK_COLS),"missing_cells":missing_cells,
            "duplicate_patient_id":dup_pid,"duplicate_full_row":dup_full,
            "unique_feature_signature":uniq_sig,"duplicated_feature_rows":dup_sig_rows,
            "signature_label_conflicts":conflicts,"invalid_age":inv_age,"invalid_gender":inv_gender,
            "invalid_risk_scale":inv_scale,"invalid_level":inv_level,
            "checks_table":[{"name":n,"count":c} for n,c in checks]}


app = FastAPI(title="Cancer BigData - Stats & Quality API (snake_case)")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["GET"], allow_headers=["*"])

def _db():
    from pymongo import MongoClient
    return MongoClient(MONGO_URI)[MONGO_DB]

@app.get("/stats")
def get_stats():
    db=_db(); recs=list(db["patients"].find({},{"_id":0}))
    res=compute_stats(recs); db["stats"].update_one({"_id":"dashboard_stats"},{"$set":res},upsert=True); return res

@app.get("/quality")
def get_quality():
    db=_db(); recs=list(db["patients"].find({},{"_id":0}))
    res=compute_quality(recs); db["data_quality"].update_one({"_id":"quality_report"},{"$set":res},upsert=True); return res

@app.get("/")
def root(): return {"status":"ok","schema":"snake_case","endpoints":["/stats","/quality"]}
