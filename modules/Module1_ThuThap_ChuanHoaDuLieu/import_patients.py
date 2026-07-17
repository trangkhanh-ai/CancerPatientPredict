# -*- coding: utf-8 -*-
"""
Nạp bệnh nhân từ CSV sạch vào MongoDB — IDEMPOTENT (bulk upsert theo patient_id).
Chạy lại không tạo trùng. Có tạo feature_signature, level_encoded, age_group, timestamps.
Chạy: python -m src.mongodb.import_patients --input data/processed/cancer_patients_ml_ready.csv

===================== MỤC LỤC FILE =====================
[QUAN TRỌNG] bulk_write(UpdateOne(..., upsert=True)) — IDEMPOTENT: chạy 10 lần
             vẫn đúng 1000 document (khớp theo patient_id, có thì $set, chưa có thì insert).
[QUAN TRỌNG] encoding="utf-8-sig" — CSV có UTF-8 BOM; đọc bằng utf-8 thường thì
             cột đầu tiên thành '﻿patient_id' và mọi thứ hỏng âm thầm.
[QUAN TRỌNG] build_doc() — nơi sinh 3 cột dẫn xuất: feature_signature (cho ML split),
             age_group (cho thống kê), level_encoded (Low=0/Medium=1/High=2).
Phần còn lại: to_int() ép kiểu an toàn, argparse, ghi sổ dataset_versions.
=========================================================
"""
import sys, os, argparse, csv, datetime
from pymongo import UpdateOne
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from common.schema import (FEATURE_COLUMNS, SCALE_1_9_COLUMNS, LABEL_TO_INDEX,  # noqa: E402
                           age_group_of, feature_signature)
from mongodb.client import get_db  # noqa: E402


def to_int(v):
    """Hàm phụ trợ ép kiểu an toàn sang số nguyên. Trả về None nếu dữ liệu trống/lỗi."""
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def build_doc(row, dataset_version, now):
    """
    Xây dựng một JSON Document từ mỗi dòng trong tệp CSV để chuẩn bị nạp vào MongoDB.
    """
    # 1. Khởi tạo trường khóa chính của bệnh nhân (patient_id)
    doc = {"patient_id": str(row["patient_id"]).strip()}
    
    # 2. Ép kiểu an toàn cho tuổi và giới tính
    doc["age"] = to_int(row.get("age"))
    doc["gender"] = to_int(row.get("gender"))
    
    # 3. Ép kiểu cho 21 cột chỉ số nguy cơ thang đo 1-9
    for c in SCALE_1_9_COLUMNS:
        doc[c] = to_int(row.get(c))
        
    # 4. Chuẩn hóa nhãn nguy cơ (viết hoa chữ cái đầu)
    doc["level"] = str(row.get("level", "")).strip().title()
    
    # 5. Sinh cột dẫn xuất phân nhóm tuổi (phục vụ biểu đồ)
    doc["age_group"] = age_group_of(doc["age"])
    
    # 6. Ánh xạ nhãn mức độ sang số nguyên (Low=0, Medium=1, High=2)
    doc["level_encoded"] = int(LABEL_TO_INDEX.get(doc["level"], -1))
    
    # 7. Tạo chữ ký đặc trưng dùng SHA-256 (để chống Data Leakage khi chia tập dữ liệu)
    doc["feature_signature"] = feature_signature(doc)
    
    # 8. Ghi nhận phiên bản tập dữ liệu và thời gian cập nhật
    doc["dataset_version"] = dataset_version
    doc["updated_at"] = now
    return doc


def main():
    # Khởi tạo bộ phân tích tham số dòng lệnh CLI
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--dataset-version", default=None)
    args = ap.parse_args()
    
    now = datetime.datetime.utcnow()
    # Nếu không truyền phiên bản, mặc định lấy ngày hiện tại (định dạng vYYYYMMDD)
    dsv = args.dataset_version or now.strftime("v%Y%m%d")

    # Lấy đối tượng kết nối MongoDB
    db = get_db()
    ops, total = [], 0
    
    # Đọc tệp CSV đã làm sạch (sử dụng encoding utf-8-sig để loại bỏ ký tự BOM đầu file)
    with open(args.input, encoding="utf-8-sig") as f:   
        for row in csv.DictReader(f):
            # Tạo document MongoDB từ dòng CSV hiện tại
            doc = build_doc(row, dsv, now)
            
            # Sử dụng UpdateOne kết hợp upsert=True:
            # - Tìm kiếm theo patient_id.
            # - Nếu tìm thấy, thực hiện ghi đè dữ liệu mới ($set).
            # - Nếu không tìm thấy, thực hiện tạo mới bản ghi và gán trường created_at ($setOnInsert).
            ops.append(UpdateOne({"patient_id": doc["patient_id"]},
                                 {"$set": doc, "$setOnInsert": {"created_at": now}}, upsert=True))
            total += 1
            
    # THỰC THI GHI HÀNG LOẠT (BULK WRITE) - giúp đẩy nhanh tốc độ nạp dữ liệu lên MongoDB
    res = db.patients.bulk_write(ops, ordered=False)
    
    print(f"[OK] total={total} upserted={res.upserted_count} modified={res.modified_count} "
          f"matched={res.matched_count}")
          
    # Cập nhật thông tin tổng kết phiên bản dữ liệu vào collection dataset_versions
    db.dataset_versions.update_one({"_id": dsv},
                                   {"$set": {"rows": total, "created_at": now}}, upsert=True)


if __name__ == "__main__":
    main()
