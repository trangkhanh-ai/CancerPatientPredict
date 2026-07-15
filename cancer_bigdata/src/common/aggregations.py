# -*- coding: utf-8 -*-
"""
Tổng hợp thống kê (/stats) và đánh giá chất lượng dữ liệu (/quality) từ các bản ghi
patients (list[dict]). Dùng chung schema canonical snake_case (common.schema).

- compute_stats: phân bố level/gender/age + trung bình chỉ số theo level & tổng thể.
- compute_quality: tách rõ valid_row_pct (dòng hợp lệ) vs field_completeness_pct (ô đủ),
  đồng thời đếm trùng patient_id / trùng dòng / trùng feature_signature và xung đột nhãn.
"""
import sys, os, hashlib
from typing import List, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from common.schema import (FEATURE_COLUMNS, SCALE_1_9_COLUMNS, LABELS,  # noqa: E402
                           AGE_BINS)

INDICATORS = SCALE_1_9_COLUMNS
SCALE_COLS = SCALE_1_9_COLUMNS
CHART_INDICATORS = ["smoking", "coughing_of_blood", "obesity", "alcohol_use", "genetic_risk"]
CHECK_COLS = FEATURE_COLUMNS + ["level"]   # cột được kiểm completeness


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _age_group(a):
    n = _num(a)
    if n is None:
        return "N/A"
    for lo, hi, lab in AGE_BINS:
        if lo <= n <= hi:
            return lab
    return ">=60"


def _signature(r):
    try:
        return hashlib.sha256("|".join(str(int(float(r[c]))) for c in FEATURE_COLUMNS).encode()).hexdigest()
    except (KeyError, TypeError, ValueError):
        return None


def compute_stats(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(records)
    level = {l: 0 for l in LABELS}
    gender = {"Nam": 0, "Nữ": 0, "Khác": 0}
    age = {b[2]: 0 for b in AGE_BINS}
    sums = {l: {c: 0.0 for c in INDICATORS} for l in LABELS}
    cnt = {l: 0 for l in LABELS}
    alls = {c: 0.0 for c in INDICATORS}
    for r in records:
        lv = str(r.get("level", "")).strip().title()
        if lv in level:
            level[lv] += 1
            cnt[lv] += 1
            for c in INDICATORS:
                v = _num(r.get(c))
                sums[lv][c] += v if v is not None else 0
        g = _num(r.get("gender"))
        gender["Nam" if g == 1 else "Nữ" if g == 2 else "Khác"] += 1
        age[_age_group(r.get("age"))] = age.get(_age_group(r.get("age")), 0) + 1
        for c in INDICATORS:
            v = _num(r.get(c))
            alls[c] += v if v is not None else 0
    avg_lv = {c: {l: round(sums[l][c] / cnt[l], 2) if cnt[l] else 0.0 for l in LABELS} for c in INDICATORS}
    return {"total": total, "level_distribution": level,
            "gender_distribution": {k: v for k, v in gender.items() if v or k != "Khác"},
            "age_group_distribution": age, "avg_indicators_by_level": avg_lv,
            "avg_indicators_overall": {c: round(alls[c] / total, 2) if total else 0.0 for c in INDICATORS},
            "chart_indicators": CHART_INDICATORS, "source": "mongodb.patients"}


def compute_quality(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(records)
    inv_age = inv_gender = inv_scale = inv_level = missing_cells = 0
    valid_rows = 0
    seen_pid = set()
    dup_pid = 0
    full_rows = {}
    sigs = {}
    for r in records:
        bad = False
        if _num(r.get("gender")) not in (1.0, 2.0):
            inv_gender += 1; bad = True
        a = _num(r.get("age"))
        if a is None or not (0 <= a <= 120):
            inv_age += 1; bad = True
        if str(r.get("level", "")).strip().title() not in LABELS:
            inv_level += 1; bad = True
        for c in SCALE_COLS:
            v = _num(r.get(c))
            if v is None or not (1 <= v <= 9):
                inv_scale += 1; bad = True
        for c in CHECK_COLS:
            val = r.get(c)
            if val is None or str(val).strip() == "":
                missing_cells += 1
        pid = r.get("patient_id")
        if pid in seen_pid:
            dup_pid += 1
        else:
            seen_pid.add(pid)
        key = tuple(r.get(c) for c in CHECK_COLS)
        full_rows[key] = full_rows.get(key, 0) + 1
        sg = _signature(r)
        if sg:
            sigs.setdefault(sg, set()).add(str(r.get("level", "")).strip().title())
        if not bad:
            valid_rows += 1
    dup_full = sum(v - 1 for v in full_rows.values() if v > 1)
    uniq_sig = len(sigs)
    dup_sig_rows = total - uniq_sig
    conflicts = sum(1 for s in sigs.values() if len(s) > 1)
    checked_cells = total * len(CHECK_COLS)
    valid_row_pct = round(valid_rows / total * 100, 2) if total else 0.0
    field_completeness = round((1 - missing_cells / checked_cells) * 100, 2) if checked_cells else 0.0
    checks = [("invalid_age", inv_age), ("invalid_gender", inv_gender), ("invalid_risk_scale", inv_scale),
              ("invalid_level", inv_level), ("duplicate_patient_id", dup_pid),
              ("duplicate_full_row", dup_full), ("signature_label_conflicts", conflicts)]
    return {"row_count_raw": total, "row_count_valid": valid_rows, "row_count_invalid": total - valid_rows,
            "valid_row_pct": valid_row_pct, "field_completeness_pct": field_completeness,
            "column_count": len(CHECK_COLS), "missing_cells": missing_cells,
            "duplicate_patient_id": dup_pid, "duplicate_full_row": dup_full,
            "unique_feature_signature": uniq_sig, "duplicated_feature_rows": dup_sig_rows,
            "signature_label_conflicts": conflicts, "invalid_age": inv_age, "invalid_gender": inv_gender,
            "invalid_risk_scale": inv_scale, "invalid_level": inv_level,
            "checks_table": [{"name": n, "count": c} for n, c in checks]}
