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
    """
    Phân loại tuổi của bệnh nhân vào các nhóm tuổi cách nhau 10 năm.
    Giúp Hadoop MapReduce dễ dàng thống kê phân bố theo nhóm tuổi thay vì tuổi đơn lẻ.
    """
    try: n=float(a)
    except: return "N/A"
    for lo,hi,lab in [(0,19,"<20"),(20,29,"20-29"),(30,39,"30-39"),(40,49,"40-49"),(50,59,"50-59"),(60,200,">=60")]:
        if lo<=n<=hi: return lab
    return ">=60"

def emit(k): 
    """Phát (emit) kết quả dạng 'khóa\t1' ra stdout để Hadoop thu thập."""
    sys.stdout.write(f"{k}\t1\n")

# P0-07: Định nghĩa cấu trúc cột cố định để đọc dữ liệu an toàn khi Hadoop chia nhỏ (split) file CSV
COLUMNS = [
    "patient_id", "age", "gender", "air_pollution", "alcohol_use", "dust_allergy",
    "occupational_hazards", "genetic_risk", "chronic_lung_disease", "balanced_diet",
    "obesity", "smoking", "passive_smoker", "chest_pain", "coughing_of_blood",
    "fatigue", "weight_loss", "shortness_of_breath", "wheezing",
    "swallowing_difficulty", "clubbing_of_finger_nails", "frequent_cold",
    "dry_cough", "snoring", "level_encoded", "level"
]

# Đọc dữ liệu dạng CSV truyền vào từ stdin (HDFS chuyển tới)
reader = csv.reader(sys.stdin)
bad = 0
for row_list in reader:
    # 1. Bỏ qua dòng tiêu đề (header) hoặc dòng rỗng
    if not row_list or row_list[0] == "patient_id" or row_list[-1] == "level":
        continue  
        
    # 2. Bỏ qua dòng bị lệch số lượng cột (dữ liệu lỗi cấu trúc)
    if len(row_list) != len(COLUMNS):
        bad += 1
        continue
        
    # 3. Ghép danh sách cột với giá trị tương ứng thành từ điển
    row = dict(zip(COLUMNS, row_list))
    
    # 4. Trích xuất và chuẩn hóa nhãn nguy cơ ung thư (Low, Medium, High)
    lv=(row.get("level") or "").strip().title()
    if lv not in ("Low","Medium","High"):
        bad+=1; continue
        
    # 5. Xác định nhóm tuổi và giới tính
    ag=age_group(row.get("age"))
    g=(row.get("gender") or "").strip()
    
    # 6. Phát ra các thống kê đơn lẻ
    emit(f"level|{lv}")         # Đếm phân bố mức độ bệnh
    emit(f"gender|{g}")         # Đếm phân bố giới tính
    emit(f"age_group|{ag}")     # Đếm phân bố nhóm tuổi
    
    # 7. Phát ra các thống kê kết hợp (Cross-tabulation)
    emit(f"cross|level_age|{lv}|{ag}")       # Thống kê chéo: Mức độ × Nhóm tuổi
    emit(f"cross|level_gender|{lv}|{g}")      # Thống kê chéo: Mức độ × Giới tính
    
    # 8. Phát ra tần suất thang đo (1-9) cho 21 chỉ số đặc trưng
    for c in INDICATORS:
        v=(row.get(c) or "").strip()
        if v: emit(f"indicator|{c}|{v}")

# Ghi nhận số dòng lỗi vào logs hệ thống của Hadoop (stderr)
if bad: sys.stderr.write(f"reporter:counter:quality,bad_rows,{bad}\n")
