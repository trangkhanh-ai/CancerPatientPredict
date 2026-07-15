# -*- coding: utf-8 -*-
"""
BACKEND API PHỤC VỤ MÔ HÌNH SPARK MLlib
Hướng A: giữ một SparkSession ngay trong API để nạp thẳng PipelineModel.
Cách chạy: uvicorn main:app --host 0.0.0.0 --port 8000
"""
from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel
from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pymongo import MongoClient

app = FastAPI(title="Cancer Risk API")

# 23 đặc trưng theo ĐÚNG thứ tự lúc huấn luyện (phải khớp với train_spark.py)
FEATURES = ["age", "gender", "air_pollution", "alcohol_use", "dust_allergy",
            "occupational_hazards", "genetic_risk", "chronic_lung_disease",
            "balanced_diet", "obesity", "smoking", "passive_smoker", "chest_pain",
            "coughing_of_blood", "fatigue", "weight_loss", "shortness_of_breath",
            "wheezing", "swallowing_difficulty", "clubbing_of_finger_nails",
            "frequent_cold", "dry_cough", "snoring"]
LABELS = {0: "Low", 1: "Medium", 2: "High"}

# ----- Khởi tạo MỘT lần khi API bật -----
spark = (SparkSession.builder.appName("CancerAPI").master("local[*]").getOrCreate())
spark.sparkContext.setLogLevel("ERROR")
model = PipelineModel.load("model_spark")               # nạp mô hình Spark đã lưu
db = MongoClient("mongodb://localhost:27017")["cancer"]  # 3 collection: patients/stats/predictions


class Patient(BaseModel):
    # Pydantic kiểm tra đầu vào: thiếu hoặc sai kiểu sẽ tự trả lỗi 422
    age: float; gender: float; air_pollution: float; alcohol_use: float
    dust_allergy: float; occupational_hazards: float; genetic_risk: float
    chronic_lung_disease: float; balanced_diet: float; obesity: float
    smoking: float; passive_smoker: float; chest_pain: float
    coughing_of_blood: float; fatigue: float; weight_loss: float
    shortness_of_breath: float; wheezing: float; swallowing_difficulty: float
    clubbing_of_finger_nails: float; frequent_cold: float; dry_cough: float
    snoring: float


@app.post("/predict")
def predict(patient: Patient):
    # Gói 23 đặc trưng thành DataFrame Spark một dòng rồi cho mô hình dự đoán
    row = {f: float(getattr(patient, f)) for f in FEATURES}
    sdf = spark.createDataFrame([row])
    out = model.transform(sdf).select("prediction", "probability").collect()[0]
    level = LABELS[int(out["prediction"])]
    confidence = round(float(max(out["probability"])) * 100, 1)
    # Lưu lại lần dự đoán để dashboard thống kê theo thời gian
    db["predictions"].insert_one({**row, "predicted_level": level,
                                  "confidence": confidence,
                                  "created_at": datetime.utcnow()})
    return {"level": level, "confidence": confidence}


@app.get("/patients")
def patients(limit: int = 100):
    docs = list(db["patients"].find({}, {"_id": 0}).limit(limit))
    return {"count": len(docs), "items": docs}


@app.get("/stats")
def stats():
    # Đọc sẵn kết quả MapReduce đã import vào collection stats
    return {"items": list(db["stats"].find({}, {"_id": 0}))}
