"""
FastAPI 主應用入口
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    description="五感量化交易系統 API",
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


@app.get("/health")
async def health_check():
    return {"status": "ok"}
