# -*- coding: utf-8 -*-
"""Xây Mongo filter cho /patients theo WHITELIST — không cho field/operator tùy ý vào query."""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from common.schema import FEATURE_COLUMNS, SCALE_1_9_COLUMNS, LABELS  # noqa: E402

FILTERABLE_INDICATORS = set(SCALE_1_9_COLUMNS)
OPERATORS = {"eq", "gte", "lte", "between"}
SORTABLE = set(["patient_id", "age", "level", "gender"] + SCALE_1_9_COLUMNS)


def build_patient_query(*, patient_id=None, level=None, gender=None,
                        age_min=None, age_max=None,
                        feature=None, operator=None, value=None,
                        min_value=None, max_value=None) -> dict:
    q: dict = {}
    if patient_id:
        q["patient_id"] = str(patient_id)
    if level:
        lv = str(level).title()
        if lv not in LABELS:
            raise ValueError(f"level không hợp lệ: {level}")
        q["level"] = lv
    if gender is not None:
        g = int(gender)
        if g not in (1, 2):
            raise ValueError("gender phải là 1 hoặc 2")
        q["gender"] = g
    age = {}
    if age_min is not None:
        age["$gte"] = int(age_min)
    if age_max is not None:
        age["$lte"] = int(age_max)
    if age:
        q["age"] = age
    if feature:
        if feature not in FILTERABLE_INDICATORS:
            raise ValueError(f"feature không nằm trong whitelist: {feature}")
        if operator not in OPERATORS:
            raise ValueError(f"operator không hợp lệ: {operator}")
        if operator == "eq":
            q[feature] = int(value)
        elif operator == "gte":
            q[feature] = {"$gte": int(value)}
        elif operator == "lte":
            q[feature] = {"$lte": int(value)}
        elif operator == "between":
            q[feature] = {"$gte": int(min_value), "$lte": int(max_value)}
    return q


def build_sort(sort_by=None, sort_dir="asc"):
    if not sort_by:
        return [("patient_id", 1)]
    if sort_by not in SORTABLE:
        raise ValueError(f"sort_by không hợp lệ: {sort_by}")
    return [(sort_by, -1 if str(sort_dir).lower() == "desc" else 1)]
