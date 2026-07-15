# -*- coding: utf-8 -*-
"""Kết nối MongoDB dùng chung. get_db() trả về database; COLLECTIONS liệt kê collection cần tạo."""
import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "cancer_project")

# Các collection của hệ thống
COLLECTIONS = ["patients", "predictions", "stats_mapreduce", "dataset_versions"]

_client = None


def get_client() -> MongoClient:
    """MongoClient singleton (tái sử dụng connection pool)."""
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    """Database mặc định (MONGO_DB)."""
    return get_client()[MONGO_DB]
