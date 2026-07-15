#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAPPER (Hadoop Streaming) — CHỈ tính phân bố dữ liệu (không train ML).
Đọc CSV snake_case CÓ header từ stdin, emit 'key<TAB>1' cho:
  level|<Low/Medium/High>, gender|<1/2>, age_group|<...>,
  indicator|<tên>|<giá trị 1..9>, cross|level_age|<lv>|<ag>, cross|level_gender|<lv>|<g>
"""
import sys, csv

INDICATORS = ["air_pollution","alcohol_use","dust_allergy","occupational_hazards","genetic_risk",
 "chronic_lung_disease","balanced_diet","obesity","smoking","passive_smoker","chest_pain",
 "coughing_of_blood","fatigue","weight_loss","shortness_of_breath","wheezing",
 "swallowing_difficulty","clubbing_of_finger_nails","frequent_cold","dry_cough","snoring"]

def age_group(a):
    try: n=float(a)
    except: return "N/A"
    for lo,hi,lab in [(0,19,"<20"),(20,29,"20-29"),(30,39,"30-39"),(40,49,"40-49"),(50,59,"50-59"),(60,200,">=60")]:
        if lo<=n<=hi: return lab
    return ">=60"

def emit(k): sys.stdout.write(f"{k}\t1\n")

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
bad = 0
for row_list in reader:
    if not row_list or row_list[0] == "patient_id" or row_list[-1] == "level":
        continue  # Bỏ qua dòng trống hoặc dòng header
        
    if len(row_list) != len(COLUMNS):
        bad += 1
        continue
        
    row = dict(zip(COLUMNS, row_list))
    lv=(row.get("level") or "").strip().title()
    if lv not in ("Low","Medium","High"):
        bad+=1; continue
    ag=age_group(row.get("age"))
    g=(row.get("gender") or "").strip()
    emit(f"level|{lv}"); emit(f"gender|{g}"); emit(f"age_group|{ag}")
    emit(f"cross|level_age|{lv}|{ag}"); emit(f"cross|level_gender|{lv}|{g}")
    for c in INDICATORS:
        v=(row.get(c) or "").strip()
        if v: emit(f"indicator|{c}|{v}")
if bad: sys.stderr.write(f"reporter:counter:quality,bad_rows,{bad}\n")
