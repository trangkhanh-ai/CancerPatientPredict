# -*- coding: utf-8 -*-
"""Cấu hình API đọc từ biến môi trường (có default an toàn cho demo local)."""
import os


class Settings:
    # Prefix cho toàn bộ route (khớp base URL WinForms: http://localhost:8000/api/v1)
    API_PREFIX = os.getenv("API_PREFIX", "/api/v1")
    # CORS: danh sách origin cụ thể, KHÔNG dùng '*'
    CORS_ORIGINS = os.getenv("API_CORS_ORIGINS", "http://localhost,http://127.0.0.1").split(",")

    # Spark / model
    SPARK_MASTER = os.getenv("SPARK_MASTER", "local[*]")
    MODEL_PATH = os.getenv("MODEL_PATH", "models/current/pipeline_model")
    MODEL_METADATA_PATH = os.getenv("MODEL_METADATA_PATH", "models/current/metadata.json")

    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB = os.getenv("MONGO_DB", "cancer_project")


settings = Settings()
