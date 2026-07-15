# -*- coding: utf-8 -*-
"""Schema canonical (snake_case) dùng chung cho CSV, HDFS, MongoDB, Spark, API, C#.

===================== MỤC LỤC FILE =====================
[QUAN TRỌNG] FEATURE_COLUMNS    — 23 đặc trưng ĐÚNG THỨ TỰ; đổi thứ tự là hỏng
             feature_signature, model input và toàn bộ hệ thống. KHÔNG SỬA.
[QUAN TRỌNG] LABEL_TO_INDEX     — ánh xạ nhãn CỐ ĐỊNH Low=0/Medium=1/High=2
             (không để thư viện tự đánh index theo tần suất — sẽ lệch giữa các lần train).
[QUAN TRỌNG] feature_signature()— SHA-256 của 23 giá trị nối bằng '|' đúng thứ tự;
             là "chứng minh thư" của một cấu hình bệnh nhân, dùng để group-aware split.
Phần còn lại:
  SCALE_1_9_COLUMNS — 21 chỉ số thang 1..9 (suy ra từ FEATURE_COLUMNS, trừ age/gender)
  RAW_TO_CANONICAL  — bảng đổi tên cột Excel gốc ('Patient Id'...) → snake_case;
                      là nơi DUY NHẤT trong src/ được phép chứa tên RAW-case
  AGE_BINS / age_group_of() — chia nhóm tuổi cho thống kê
=========================================================
"""
import hashlib

# 23 đặc trưng ML — ĐÚNG THỨ TỰ (không đổi)
FEATURE_COLUMNS = [
    "age", "gender", "air_pollution", "alcohol_use", "dust_allergy",
    "occupational_hazards", "genetic_risk", "chronic_lung_disease", "balanced_diet",
    "obesity", "smoking", "passive_smoker", "chest_pain", "coughing_of_blood",
    "fatigue", "weight_loss", "shortness_of_breath", "wheezing",
    "swallowing_difficulty", "clubbing_of_finger_nails", "frequent_cold",
    "dry_cough", "snoring",
]
# 21 chỉ số thang 1..9 (không gồm age, gender)
SCALE_1_9_COLUMNS = [c for c in FEATURE_COLUMNS if c not in ("age", "gender")]

LABEL_COL = "level"
LABELS = ["Low", "Medium", "High"]
LABEL_TO_INDEX = {"Low": 0.0, "Medium": 1.0, "High": 2.0}   # ánh xạ CỐ ĐỊNH
INDEX_TO_LABEL = {0: "Low", 1: "Medium", 2: "High"}

AGE_BINS = [(0, 19, "<20"), (20, 29, "20-29"), (30, 39, "30-39"),
            (40, 49, "40-49"), (50, 59, "50-59"), (60, 200, ">=60")]

# Đổi tên cột thô (Excel) -> canonical snake_case
RAW_TO_CANONICAL = {
    "Patient Id": "patient_id", "Age": "age", "Gender": "gender",
    "Air Pollution": "air_pollution", "Alcohol use": "alcohol_use",
    "Dust Allergy": "dust_allergy", "OccuPational Hazards": "occupational_hazards",
    "Genetic Risk": "genetic_risk", "chronic Lung Disease": "chronic_lung_disease",
    "Balanced Diet": "balanced_diet", "Obesity": "obesity", "Smoking": "smoking",
    "Passive Smoker": "passive_smoker", "Chest Pain": "chest_pain",
    "Coughing of Blood": "coughing_of_blood", "Fatigue": "fatigue",
    "Weight Loss": "weight_loss", "Shortness of Breath": "shortness_of_breath",
    "Wheezing": "wheezing", "Swallowing Difficulty": "swallowing_difficulty",
    "Clubbing of Finger Nails": "clubbing_of_finger_nails",
    "Frequent Cold": "frequent_cold", "Dry Cough": "dry_cough",
    "Snoring": "snoring", "Level": "level",
}


def age_group_of(age) -> str:
    try:
        n = float(age)
    except (TypeError, ValueError):
        return "N/A"
    for lo, hi, lab in AGE_BINS:
        if lo <= n <= hi:
            return lab
    return ">=60"


def feature_signature(row: dict) -> str:
    """SHA-256 của 23 đặc trưng, đúng thứ tự, phân tách bằng '|'."""
    joined = "|".join(str(int(float(row[c]))) for c in FEATURE_COLUMNS)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
