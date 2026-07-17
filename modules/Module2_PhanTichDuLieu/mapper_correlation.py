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
    """
    Phân cụm (Binning/Bucketing) điểm chỉ số nguy cơ (từ 1-9) thành 3 mức độ:
    - 1 đến 3: thap (Thấp)
    - 4 đến 6: trungbinh (Trung bình)
    - 7 đến 9: cao (Cao)
    Giúp tạo bảng tần suất phân chéo đặc trưng (Cross-tabulation) trực quan hơn.
    """
    if v <= 3:
        return "thap"
    if v <= 6:
        return "trungbinh"
    return "cao"


def emit(k, v):
    """Phát (emit) khóa và giá trị phân tán ra stdout cách nhau bởi dấu Tab."""
    sys.stdout.write(f"{k}\t{v}\n")


def main():
    bad = 0
    
    # P0-07: Khai báo cấu trúc cột chuẩn để đọc dữ liệu độc lập với header khi Hadoop phân chia file
    COLUMNS = [
        "patient_id", "age", "gender", "air_pollution", "alcohol_use", "dust_allergy",
        "occupational_hazards", "genetic_risk", "chronic_lung_disease", "balanced_diet",
        "obesity", "smoking", "passive_smoker", "chest_pain", "coughing_of_blood",
        "fatigue", "weight_loss", "shortness_of_breath", "wheezing",
        "swallowing_difficulty", "clubbing_of_finger_nails", "frequent_cold",
        "dry_cough", "snoring", "level_encoded", "level"
    ]
    
    # Đọc dữ liệu từ stdin (Hadoop đẩy vào mapper)
    reader = csv.reader(sys.stdin)
    for row_list in reader:
        # Bỏ qua dòng trống hoặc dòng header
        if not row_list or row_list[0] == "patient_id" or row_list[-1] == "level":
            continue  
            
        # Kiểm tra tính toàn vẹn số lượng cột
        if len(row_list) != len(COLUMNS):
            bad += 1
            continue
            
        # Ghép cột thành từ điển
        row = dict(zip(COLUMNS, row_list))
        
        # Lấy và chuẩn hóa mức độ ung thư
        lv = (row.get("level") or "").strip().title()
        if lv not in LEVELS:
            bad += 1
            continue
            
        # 1. Phát ra biến đếm tổng số bệnh nhân ở mỗi mức độ (để làm mẫu số n)
        emit(f"n|{lv}", 1)
        
        # 2. Duyệt qua 21 chỉ số nguy cơ
        for c in INDICATORS:
            raw = (row.get(c) or "").strip()
            if not raw:
                continue
            try:
                # Ép kiểu an toàn sang số nguyên
                v = int(float(raw))
            except ValueError:
                continue
            # Phát ra khóa 'mean|tên_chỉ_số|mức_độ' cùng giá trị của nó để tính trung bình cộng ở reducer
            emit(f"mean|{c}|{lv}", v)                    
            # Phát ra khóa bảng chéo 'xtab|tên_chỉ_số|mức_độ_chỉ_số|mức_độ_bệnh' để đếm tần suất
            emit(f"xtab|{c}|{bucket(v)}|{lv}", 1)        
            
    # Ghi nhận số dòng lỗi vào logs của Hadoop
    if bad:
        sys.stderr.write(f"reporter:counter:quality,bad_rows,{bad}\n")


if __name__ == "__main__":
    main()
