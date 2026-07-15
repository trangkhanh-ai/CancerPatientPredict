# -*- coding: utf-8 -*-
"""Tạo collections và JSON Schema validator cho `patients`. Idempotent."""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from common.schema import FEATURE_COLUMNS, SCALE_1_9_COLUMNS, LABELS  # noqa: E402
from mongodb.client import get_db, COLLECTIONS  # noqa: E402

PATIENT_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["patient_id", "age", "gender", "level"] + SCALE_1_9_COLUMNS,
        "properties": {
            "patient_id": {"bsonType": "string"},
            "age": {"bsonType": ["int", "double"], "minimum": 0, "maximum": 120},
            "gender": {"enum": [1, 2]},
            "level": {"enum": LABELS},
            **{c: {"bsonType": ["int", "double"], "minimum": 1, "maximum": 9} for c in SCALE_1_9_COLUMNS},
        },
    }
}


def main():
    db = get_db()
    existing = set(db.list_collection_names())
    for name in COLLECTIONS:
        if name not in existing:
            db.create_collection(name)
            print(f"[+] created collection: {name}")
        else:
            print(f"[=] exists: {name}")
    db.command({"collMod": "patients", "validator": PATIENT_VALIDATOR,
                "validationLevel": "moderate"})
    print("[OK] validator áp cho patients")


if __name__ == "__main__":
    main()
