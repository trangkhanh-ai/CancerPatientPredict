#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAPPER — Phân tích TƯƠNG QUAN YẾU TỐ NGUY CƠ (Module 2).
Không dùng ML — chỉ aggregation kiểu MapReduce.

Đọc CSV snake_case CÓ header từ stdin, emit 'key<TAB>value':
  mean|<indicator>|<level>      -> <giá trị>     (để reduce tính trung bình)
  xtab|<indicator>|<bucket>|<level> -> 1         (bảng chéo: thấp/TB/cao × mức độ)
  n|<level>                     -> 1             (đếm số bệnh nhân mỗi mức độ)

bucket: 1-3 = "thap", 4-6 = "trungbinh", 7-9 = "cao"
"""
import sys, csv

INDICATORS = ["air_pollution","alcohol_use","dust_allergy","occupational_hazards","genetic_risk",
 "chronic_lung_disease","balanced_diet","obesity","smoking","passive_smoker","chest_pain",
 "coughing_of_blood","fatigue","weight_loss","shortness_of_breath","wheezing",
 "swallowing_difficulty","clubbing_of_finger_nails","frequent_cold","dry_cough","snoring"]
LEVELS = ("Low", "Medium", "High")


def bucket(v):
    if v <= 3:
        return "thap"
    if v <= 6:
        return "trungbinh"
    return "cao"


def emit(k, v):
    sys.stdout.write(f"{k}\t{v}\n")


def main():
    bad = 0
    for row in csv.DictReader(sys.stdin):
        lv = (row.get("level") or "").strip().title()
        if lv not in LEVELS:
            bad += 1
            continue
        emit(f"n|{lv}", 1)
        for c in INDICATORS:
            raw = (row.get(c) or "").strip()
            if not raw:
                continue
            try:
                v = int(float(raw))
            except ValueError:
                continue
            emit(f"mean|{c}|{lv}", v)                    # để tính trung bình
            emit(f"xtab|{c}|{bucket(v)}|{lv}", 1)        # bảng chéo
    if bad:
        sys.stderr.write(f"reporter:counter:quality,bad_rows,{bad}\n")


if __name__ == "__main__":
    main()
