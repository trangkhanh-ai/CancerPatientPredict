# -*- coding: utf-8 -*-
"""
FastAPI app chính. Lifespan nạp MongoClient + SparkSession + PipelineModel MỘT LẦN.
Chạy (1 worker cho demo vì mỗi worker sẽ tạo SparkSession riêng):
  uvicorn src.api.main:app --host 127.0.0.1 --port 8000
"""
import sys, os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from api.settings import settings  # noqa: E402
from api.services.model_service import model_service  # noqa: E402
from api.routers.api_router import router  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: nạp model 1 lần (Mongo client lazy qua get_db)
    model_service.load()
    print(f"[startup] model_loaded={model_service.loaded}")
    yield
    # shutdown
    model_service.close()


app = FastAPI(title="Cancer BigData API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS,
                   allow_methods=["GET", "POST"], allow_headers=["*"])
app.include_router(router, prefix=settings.API_PREFIX)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    # không trả stack trace ra client
    print(f"[error] {request.url.path}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Lỗi máy chủ nội bộ."})


@app.get("/")
def root():
    return {"service": "cancer-bigdata-api", "docs": "/docs", "prefix": settings.API_PREFIX}
