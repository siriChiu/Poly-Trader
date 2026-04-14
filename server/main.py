"""
FastAPI 主應用入口
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Allow both `uvicorn server.main:app` and direct `python server/main.py` execution.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.dependencies import init_dependencies
from server.routes.api import router as api_router
from server.routes.ws import router as ws_router
from utils.logger import setup_logger

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """啟動時初始化 DB 與依賴，關閉時清理。"""
    logger.info("Poly-Trader API 啟動中...")
    init_dependencies()
    logger.info("Poly-Trader API 就緒")
    yield
    logger.info("Poly-Trader API 關閉")


app = FastAPI(
    title="Poly-Trader API",
    description="多特徵量化交易系統 API",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS 中間件 — 允許前端 dev server 連接
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載路由
app.include_router(api_router, prefix="/api")
app.include_router(ws_router)


@app.get("/")
async def root():
    return {
        "name": "Poly-Trader API",
        "version": "2.0.0",
        "docs": "/docs",
        "api": "/api/status",
        "ws": "/ws/live",
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server.main:app", host="127.0.0.1", port=8000, reload=False)
