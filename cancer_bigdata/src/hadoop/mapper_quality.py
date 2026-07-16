#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAPPER — Module 1: Kiểm định chất lượng dữ liệu (MapReduce Streaming).

╔══════════════════════════════════════════════════════════════════════╗
║  MỤC ĐÍCH:                                                        ║
║  Đọc từng dòng CSV từ stdin, kiểm tra 4 tiêu chí chất lượng:     ║
║    1. gender ∈ {1, 2}                 → nếu sai: emit invalid_gender ║
║    2. age ∈ [0, 120]                  → nếu sai: emit invalid_age    ║
║    3. level ∈ {Low, Medium, High}     → nếu sai: emit invalid_level  ║
║    4. 21 chỉ số nguy cơ ∈ [1, 9]     → nếu sai: emit invalid_risk_scale ║
║  Mỗi dòng LUÔN emit (rows_total, 1) để đếm tổng.                ║
║                                                                    ║
║  OUTPUT FORMAT: key<TAB>1                                          ║
║    - rows_total\t1          (mỗi dòng dữ liệu hợp lệ/không)     ║
║    - invalid_gender\t1      (nếu gender không phải 1 hoặc 2)      ║
║    - invalid_age\t1         (nếu tuổi ngoài [0,120])              ║
║    - invalid_level\t1       (nếu level không phải Low/Medium/High) ║
║    - invalid_risk_scale\t1  (nếu bất kỳ chỉ số nào ngoài [1,9])  ║
║                                                                    ║
║  → Dòng sạch: chỉ phát (rows_total, 1), KHÔNG phát key invalid   ║
║  → Reducer sẽ gom theo check_name rồi Σ đếm.                     ║
║                                                                    ║
║  KẾT QUẢ THẬT (đã kiểm chứng):                                   ║
║    rows_total   1000                                               ║
║    (0 dòng invalid — dữ liệu sạch 1000/1000)                     ║
║                                                                    ║
║  CHẠY CỤC BỘ (Streaming-compatible):                              ║
║    cat cancer_patients_ml_ready.csv                                ║
║      | python mapper_quality.py | sort                             ║
║      | python reducer_quality.py > quality_report.tsv              ║
║                                                                    ║
║  KHỚP SƠ ĐỒ: module1_JOB_kiem_dinh_chat_luong_TOPOLOGY.png       ║
║    HDFS → Split → M1/M2/M3 (Map kiểm định) → Shuffle → Reduce Σ  ║
╚══════════════════════════════════════════════════════════════════════╝

Tác giả: Nhóm đồ án Big Data — HUFLIT
Ngày: 2026-07-15
"""
import sys
import csv

# ─── 21 CỘT CHỈ SỐ NGUY CƠ (thang 1–9) ───────────────────────────
# Đây là danh sách 21 thuộc tính sức khoẻ / lối sống / triệu chứng
# trong dataset cancer_patients. Mỗi giá trị hợp lệ nằm trong [1, 9].
SCALE_COLS = [
    "air_pollution",           # Mức ô nhiễm không khí
    "alcohol_use",             # Mức sử dụng rượu bia
    "dust_allergy",            # Dị ứng bụi
    "occupational_hazards",    # Nguy cơ nghề nghiệp
    "genetic_risk",            # Nguy cơ di truyền
    "chronic_lung_disease",    # Bệnh phổi mãn tính
    "balanced_diet",           # Chế độ ăn cân bằng
    "obesity",                 # Béo phì
    "smoking",                 # Hút thuốc
    "passive_smoker",          # Hút thuốc thụ động
    "chest_pain",              # Đau ngực
    "coughing_of_blood",       # Ho ra máu
    "fatigue",                 # Mệt mỏi
    "weight_loss",             # Sụt cân
    "shortness_of_breath",     # Khó thở
    "wheezing",                # Thở khò khè
    "swallowing_difficulty",   # Khó nuốt
    "clubbing_of_finger_nails",# Ngón tay dùi trống
    "frequent_cold",           # Cảm lạnh thường xuyên
    "dry_cough",               # Ho khan
    "snoring",                 # Ngáy
]

# Các giá trị hợp lệ cho cột 'level' (mức độ mắc bệnh ung thư)
LEVELS = {"Low", "Medium", "High"}


def emit(k):
    """
    Phát một cặp (key, 1) ra stdout theo format Hadoop Streaming.
    Reducer sẽ đọc key<TAB>value và cộng dồn.
    """
    sys.stdout.write(f"{k}\t1\n")


def num(v):
    """
    Chuyển chuỗi thành số thực. Trả None nếu không parse được.
    Dùng cho kiểm tra gender, age, và các chỉ số scale.
    """
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main():
    """
    Vòng lặp chính — đọc CSV từ stdin, kiểm tra từng dòng.
    
    Luồng xử lý cho MỖI DÒNG:
      1. Luôn emit("rows_total") → đếm tổng số dòng
      2. Kiểm tra gender: phải là 1 (Nam) hoặc 2 (Nữ)
      3. Kiểm tra age: phải trong khoảng [0, 120]
      4. Kiểm tra level: phải là Low, Medium, hoặc High
      5. Kiểm tra 21 chỉ số: mỗi giá trị phải trong [1, 9]
         → Nếu BẤT KỲ chỉ số nào sai, emit 1 lần invalid_risk_scale rồi break
    
    Tương ứng với sơ đồ Module 1:
      M1/M2/M3 → Map: chạy 4 phép kiểm mỗi dòng,
      emit (check_name, 1) nếu VI PHẠM + emit (rows_total, 1)
    """
    for row in csv.DictReader(sys.stdin):
        # ── Bước 1: Đếm tổng (luôn phát, bất kể hợp lệ hay không) ──
        emit("rows_total")

        # ── Bước 2: Kiểm tra giới tính ──
        # Dataset mã hoá: 1 = Nam, 2 = Nữ
        if num(row.get("gender")) not in (1.0, 2.0):
            emit("invalid_gender")

        # ── Bước 3: Kiểm tra tuổi ──
        # Tuổi hợp lệ: 0 ≤ age ≤ 120
        a = num(row.get("age"))
        if a is None or not (0 <= a <= 120):
            emit("invalid_age")

        # ── Bước 4: Kiểm tra nhãn mức độ ──
        # Phải là Low, Medium, hoặc High (title-case)
        if str(row.get("level", "")).strip().title() not in LEVELS:
            emit("invalid_level")

        # ── Bước 5: Kiểm tra 21 chỉ số nguy cơ ──
        # Tất cả phải nằm trong thang [1, 9]
        # Nếu bất kỳ chỉ số nào vi phạm → emit 1 lần rồi dừng (break)
        # để tránh đếm trùng nhiều lần cho cùng 1 dòng
        for c in SCALE_COLS:
            v = num(row.get(c))
            if v is None or not (1 <= v <= 9):
                emit("invalid_risk_scale")
                break  # Chỉ emit 1 lần per row


if __name__ == "__main__":
    main()
