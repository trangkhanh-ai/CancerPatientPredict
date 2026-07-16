#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAPPER (Hadoop Streaming) — Module 2 · JOB 1: Đếm phân bố dữ liệu.

Đọc CSV snake_case CÓ header từ stdin, emit 'key<TAB>1' cho mỗi dòng:
  level|<Low/Medium/High>                     → đếm phân bố nhãn
  gender|<1/2>                                → đếm theo giới tính
  age_group|<nhóm tuổi>                       → đếm theo nhóm tuổi
  indicator|<tên chỉ số>|<giá trị 1..9>       → phân bố từng chỉ số
  cross|level_age|<lv>|<ag>                   → bảng chéo nhãn × tuổi
  cross|level_gender|<lv>|<g>                 → bảng chéo nhãn × giới tính

Value LUÔN là 1 → Reducer chỉ cần cộng dồn (Σ đếm).

KHỚP SƠ ĐỒ: module2_JOB1_dem_phan_bo_TOPOLOGY.png
  HDFS (1000 dòng) → Split 1-3 → M1/M2/M3 (Map phân bố)
  → ~26 cặp (key, 1) mỗi dòng → Shuffle → Reduce Σ đếm
  → distributions.tsv (199 dòng) → API /stats → Tab Thống kê

KẾT QUẢ THẬT (khớp Tab Thống kê):
  level|Low → 303, level|Medium → 332, level|High → 365
  gender|1 → 598 (Nam), gender|2 → 402 (Nữ)
  age_group|<20 → 67, 20-29 → 234, 30-39 → 358, 40-49 → 207, 50-59 → 63, >=60 → 71
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
