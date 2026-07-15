# -*- coding: utf-8 -*-
"""
Module 2 — Phân tích tương quan yếu tố nguy cơ (KHÔNG dùng ML, chỉ aggregation).
Tính:
  - mean từng chỉ số theo từng mức độ
  - impact = mean(High) - mean(Low)  → xếp hạng yếu tố nguy cơ
  - crosstab: bucket (thấp 1-3 / TB 4-6 / cao 7-9) × mức độ  → % trong mỗi bucket
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from common.schema import SCALE_1_9_COLUMNS, LABELS  # noqa: E402

BUCKETS = ["thap", "trungbinh", "cao"]
BUCKET_LABEL = {"thap": "Thấp (1-3)", "trungbinh": "Trung bình (4-6)", "cao": "Cao (7-9)"}


def _bucket(v):
    return "thap" if v <= 3 else ("trungbinh" if v <= 6 else "cao")


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def compute_correlation(records):
    sums = {c: {l: 0.0 for l in LABELS} for c in SCALE_1_9_COLUMNS}
    cnts = {c: {l: 0 for l in LABELS} for c in SCALE_1_9_COLUMNS}
    xtab = {c: {b: {l: 0 for l in LABELS} for b in BUCKETS} for c in SCALE_1_9_COLUMNS}
    n_level = {l: 0 for l in LABELS}

    for r in records:
        lv = str(r.get("level", "")).strip().title()
        if lv not in LABELS:
            continue
        n_level[lv] += 1
        for c in SCALE_1_9_COLUMNS:
            v = _num(r.get(c))
            if v is None:
                continue
            sums[c][lv] += v
            cnts[c][lv] += 1
            xtab[c][_bucket(v)][lv] += 1

    factors = []
    for c in SCALE_1_9_COLUMNS:
        means = {l: round(sums[c][l] / cnts[c][l], 2) if cnts[c][l] else 0.0 for l in LABELS}
        impact = round(means["High"] - means["Low"], 2)
        # % bệnh nhân High trong nhóm có chỉ số CAO (7-9) — dễ hiểu cho người dùng
        cao = xtab[c]["cao"]
        cao_total = sum(cao.values())
        pct_high_when_cao = round(cao["High"] / cao_total * 100, 1) if cao_total else 0.0
        factors.append({
            "indicator": c, "mean_by_level": means, "impact": impact,
            "pct_high_when_high_value": pct_high_when_cao,
            "crosstab": {b: dict(xtab[c][b]) for b in BUCKETS},
        })

    factors.sort(key=lambda f: -f["impact"])
    for i, f in enumerate(factors, 1):
        f["rank"] = i

    return {
        "n_by_level": n_level,
        "total": sum(n_level.values()),
        "bucket_labels": BUCKET_LABEL,
        "factors": factors,
        "top_risk_factors": [f["indicator"] for f in factors[:5]],
        "method": "Spark/MapReduce aggregation (không dùng ML)",
        "note": "impact = mean(High) - mean(Low): chênh lệch trung bình chỉ số giữa nhóm nặng nhất và nhẹ nhất.",
    }
