# -*- coding: utf-8 -*-
"""Dịch vụ mô hình: nạp SparkSession + PipelineModel MỘT LẦN; predict 1 dòng, có khoá.

===================== MỤC LỤC FILE =====================
[QUAN TRỌNG] load() — gọi 1 lần trong lifespan startup của FastAPI: tạo SparkSession
             + PipelineModel.load(). Nạp mỗi request thì mỗi lần predict tốn thêm ~chục giây.
             Nếu thiếu Spark/model: loaded=False (API vẫn sống, /predict trả 503).
[QUAN TRỌNG] async with self._lock — Spark transform KHÔNG an toàn khi chạy song song
             trong 1 session; khoá để các request predict xếp hàng tuần tự.
[QUAN TRỌNG] decode nhãn: lấy labels từ StringIndexer TRONG model (model tự khai thứ tự
             index→label của nó); chỉ fallback về INDEX_TO_LABEL cố định khi model không có.
Phần còn lại: đo latency_ms, đóng gói probabilities theo thứ tự Low/Medium/High,
model_service = ModelService() (singleton dùng chung toàn app).
=========================================================
"""
import os, json, asyncio, time, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from common.schema import FEATURE_COLUMNS, INDEX_TO_LABEL, LABELS  # noqa: E402
from api.settings import settings  # noqa: E402


class ModelService:
    def __init__(self):
        self.spark = None
        self.model = None
        self.metadata = {}
        self.loaded = False
        self._lock = asyncio.Lock()

    def load(self):
        """Gọi trong lifespan startup. An toàn nếu thiếu Spark/model (loaded=False)."""
        try:
            from pyspark.sql import SparkSession
            from pyspark.ml import PipelineModel
            self.spark = (SparkSession.builder
                          .appName("cancer_api").master(settings.SPARK_MASTER)
                          .config("spark.ui.enabled", "false").getOrCreate())
            self.spark.sparkContext.setLogLevel("ERROR")
            if os.path.exists(settings.MODEL_PATH):
                self.model = PipelineModel.load(settings.MODEL_PATH)
                if os.path.exists(settings.MODEL_METADATA_PATH):
                    self.metadata = json.load(open(settings.MODEL_METADATA_PATH, encoding="utf-8"))
                self.loaded = True
        except Exception as e:  # noqa: BLE001
            print(f"[model_service] NOT LOADED: {e}")
            self.loaded = False

    def close(self):
        if self.spark is not None:
            self.spark.stop()

    async def predict(self, features: dict) -> dict:
        if not self.loaded:
            raise RuntimeError("Model chưa được nạp (thiếu Spark hoặc model artifact).")
        async with self._lock:                       # tránh chạy song song Spark transform
            t0 = time.time()
            row = {c: float(features[c]) for c in FEATURE_COLUMNS}
            sdf = self.spark.createDataFrame([row])
            pred = self.model.transform(sdf).select("prediction", "probability").first()
            idx = int(pred["prediction"])
            probs = list(pred["probability"])
            # ánh xạ index -> label theo StringIndexer trong model nếu có, else cố định
            try:
                labels = self.model.stages[0].labels
                idx_to_label = {i: lb for i, lb in enumerate(labels)}
            except Exception:  # noqa: BLE001
                idx_to_label = INDEX_TO_LABEL
            prob_map = {idx_to_label.get(i, str(i)): round(float(p), 4) for i, p in enumerate(probs)}
            return {
                "predicted_level": idx_to_label.get(idx, str(idx)),
                "predicted_index": idx,
                "probabilities": {l: prob_map.get(l, 0.0) for l in LABELS},
                "latency_ms": round((time.time() - t0) * 1000, 2),
                "model_run_id": self.metadata.get("model_run_id"),
                "dataset_version": self.metadata.get("dataset_version"),
            }


model_service = ModelService()
