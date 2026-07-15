# -*- coding: utf-8 -*-
"""Dịch vụ mô hình: nạp SparkSession + PipelineModel MỘT LẦN; predict 1 dòng, có khoá."""
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
                if not os.path.exists(settings.MODEL_METADATA_PATH):
                    raise RuntimeError("Missing MODEL_METADATA_PATH. Cannot map labels.")
                self.metadata = json.load(open(settings.MODEL_METADATA_PATH, encoding="utf-8"))
                
                # Verify that metadata has index_to_label
                if "index_to_label" not in self.metadata:
                    raise RuntimeError("metadata.json missing 'index_to_label' (P0-01).")
                
                # Check fitted model labels vs metadata
                try:
                    fitted_labels = self.model.stages[0].labels
                    idx_to_label = {str(i): lb for i, lb in enumerate(fitted_labels)}
                    if self.metadata["index_to_label"] != idx_to_label:
                        print("[model_service] WARNING: metadata.json mapping differs from fitted model. Trusting metadata.")
                except Exception:
                    pass

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
            
            # P0-01: Sử dụng mapping từ metadata (đảm bảo đúng nhãn)
            idx_to_label = self.metadata.get("index_to_label", {})
            idx_str = str(idx)
            predicted_label = idx_to_label.get(idx_str, idx_str)
            
            prob_map = {idx_to_label.get(str(i), str(i)): round(float(p), 4) for i, p in enumerate(probs)}
            
            return {
                "predicted_level": predicted_label,
                "predicted_index": idx,
                "probabilities": {l: prob_map.get(l, 0.0) for l in LABELS},
                "latency_ms": round((time.time() - t0) * 1000, 2),
                "model_run_id": self.metadata.get("model_run_id"),
                "dataset_version": self.metadata.get("dataset_version"),
            }


model_service = ModelService()
