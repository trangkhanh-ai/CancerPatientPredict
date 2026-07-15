# -*- coding: utf-8 -*-
"""Pydantic v2 models cho request/response."""
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, field_validator
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from common.schema import SCALE_1_9_COLUMNS  # noqa: E402


class PredictRequest(BaseModel):
    patient_id: Optional[str] = None
    age: int = Field(..., ge=0, le=120)
    gender: int
    air_pollution: int; alcohol_use: int; dust_allergy: int; occupational_hazards: int
    genetic_risk: int; chronic_lung_disease: int; balanced_diet: int; obesity: int
    smoking: int; passive_smoker: int; chest_pain: int; coughing_of_blood: int
    fatigue: int; weight_loss: int; shortness_of_breath: int; wheezing: int
    swallowing_difficulty: int; clubbing_of_finger_nails: int; frequent_cold: int
    dry_cough: int; snoring: int

    model_config = {"extra": "forbid"}   # từ chối field lạ; không nhận 'level'

    @field_validator("gender")
    @classmethod
    def _gender(cls, v):
        if v not in (1, 2):
            raise ValueError("gender phải là 1 hoặc 2")
        return v

    @field_validator(*SCALE_1_9_COLUMNS)
    @classmethod
    def _scale(cls, v):
        if not (1 <= v <= 9):
            raise ValueError("chỉ số phải trong [1..9]")
        return v


class PredictResponse(BaseModel):
    prediction_id: str
    patient_id: Optional[str]
    predicted_level: str
    predicted_index: int
    probabilities: Dict[str, float]
    model_run_id: Optional[str]
    dataset_version: Optional[str]
    latency_ms: float
    created_at: str
    disclaimer: str = "Kết quả phục vụ mục đích học thuật, không thay thế chẩn đoán y khoa."


class PatientOut(BaseModel):
    patient_id: str
    age: Optional[int] = None
    gender: Optional[int] = None
    level: Optional[str] = None
    age_group: Optional[str] = None
    model_config = {"extra": "allow"}


class PaginatedPatients(BaseModel):
    items: List[dict]
    page: int
    page_size: int
    total: int
    total_pages: int
