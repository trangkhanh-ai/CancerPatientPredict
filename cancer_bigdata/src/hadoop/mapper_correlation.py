#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAPPER — Module 2 · JOB 2: Phân tích TƯƠNG QUAN YẾU TỐ NGUY CƠ (MapReduce).
Không dùng ML — chỉ aggregation kiểu MapReduce.

Đọc CSV snake_case CÓ header từ stdin, emit 'key<TAB>value':
  mean|<indicator>|<level>        -> <giá trị>  (để reducer tính TRUNG BÌNH)
  xtab|<indicator>|<bucket>|<lv>  -> 1          (bảng chéo: thấp/TB/cao × mức độ)
  n|<level>                       -> 1          (đếm số bệnh nhân mỗi mức độ)

KHÁC JOB 1: value = GIÁ TRỊ (không phải 1). Reducer tính mean = Σ giá trị / n.
  bucket: 1-3 = "thap", 4-6 = "trungbinh", 7-9 = "cao"

KHỚP SƠ ĐỒ: module2_JOB2_tuong_quan_TOPOLOGY.png
  HDFS → Split → M1/M2/M3 (Map impact) → Shuffle → Reduce mean/count
  → impact = mean(High) - mean(Low) → xếp hạng nguy cơ

KẾT QUẢ THẬT (khớp Tab Yếu tố nguy cơ):
  Top 5: alcohol_use +4.60, coughing_of_blood +4.58, obesity +4.27,
         passive_smoker +3.90 (100% High khi ≥7), genetic_risk +3.65
  Yếu nhất: snoring +1.09
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
    
    # P0-07: Không phụ thuộc vào header. Chạy an toàn với split của Hadoop.
    COLUMNS = [
        "patient_id", "age", "gender", "air_pollution", "alcohol_use", "dust_allergy",
        "occupational_hazards", "genetic_risk", "chronic_lung_disease", "balanced_diet",
        "obesity", "smoking", "passive_smoker", "chest_pain", "coughing_of_blood",
        "fatigue", "weight_loss", "shortness_of_breath", "wheezing",
        "swallowing_difficulty", "clubbing_of_finger_nails", "frequent_cold",
        "dry_cough", "snoring", "level_encoded", "level"
    ]
    
    reader = csv.reader(sys.stdin)
    for row_list in reader:
        if not row_list or row_list[0] == "patient_id" or row_list[-1] == "level":
            continue  # Bỏ qua dòng trống hoặc dòng header
            
        if len(row_list) != len(COLUMNS):
            bad += 1
            continue
            
        row = dict(zip(COLUMNS, row_list))
        
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
