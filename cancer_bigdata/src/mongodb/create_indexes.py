# -*- coding: utf-8 -*-
"""Tạo index cho patients & predictions. Idempotent (đặt tên cố định, chạy lại không lỗi).
Bắt buộc: unique index `ux_patient_id` (verify_database.py kiểm tra tên này)."""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from common.schema import SCALE_1_9_COLUMNS  # noqa: E402
from mongodb.client import get_db  # noqa: E402


def main():
    db = get_db()

    # patients: unique theo patient_id + các index truy vấn thường dùng
    db.patients.create_index("patient_id", unique=True, name="ux_patient_id")
    db.patients.create_index("level", name="ix_level")
    db.patients.create_index("gender", name="ix_gender")
    db.patients.create_index("age", name="ix_age")
    db.patients.create_index("feature_signature", name="ix_signature")

    # predictions: tra cứu theo prediction_id / patient_id / thời gian
    db.predictions.create_index("prediction_id", name="ux_prediction_id", unique=True, sparse=True)
    db.predictions.create_index("patient_id", name="ix_pred_patient")
    db.predictions.create_index([("created_at", -1)], name="ix_pred_created")

    print("[OK] indexes:")
    for i in db.patients.list_indexes():
        print("   patients:", i["name"])
    for i in db.predictions.list_indexes():
        print("   predictions:", i["name"])


if __name__ == "__main__":
    main()
