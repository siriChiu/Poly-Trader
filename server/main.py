"""
FastAPI 主應用入口
"""

import sys
import threading
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Allow both `uvicorn server.main:app` and direct `python server/main.py` execution.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from server.dependencies import get_db, init_dependencies, set_runtime_status
from server.routes.api import (
    router as api_router,
    run_execution_metadata_smoke_background_governance,
)
from server.routes.ws import router as ws_router
from data_ingestion.collector import repair_recent_raw_continuity
from feature_engine.preprocessor import repair_recent_feature_continuity
from utils.logger import setup_logger

logger = setup_logger(__name__)

_EXECUTION_METADATA_BACKGROUND_INTERVAL_SECONDS = 60.0


def _execution_metadata_background_monitor_loop(
    stop_event: threading.Event,
    cfg: dict,
    symbol: str,
    *,
    interval_seconds: float = _EXECUTION_METADATA_BACKGROUND_INTERVAL_SECONDS,
    run_once: bool = False,
) -> None:
    while not stop_event.is_set():
        try:
            run_execution_metadata_smoke_background_governance(
                cfg,
                symbol,
                reason="server_background_monitor",
                interval_seconds=interval_seconds,
            )
        except Exception:
            logger.exception("execution metadata background monitor tick 失敗")
        if run_once:
            break
        if stop_event.wait(interval_seconds):
            break


def _start_execution_metadata_background_monitor(
    app: FastAPI,
    cfg: dict,
    symbol: str,
    *,
    interval_seconds: float = _EXECUTION_METADATA_BACKGROUND_INTERVAL_SECONDS,
) -> threading.Thread:
    stop_event = threading.Event()
    thread = threading.Thread(
        target=_execution_metadata_background_monitor_loop,
        args=(stop_event, cfg, symbol),
        kwargs={"interval_seconds": interval_seconds},
        daemon=True,
        name="execution-metadata-background-monitor",
    )
    app.state.execution_metadata_background_stop_event = stop_event
    app.state.execution_metadata_background_thread = thread
    set_runtime_status(
        "execution_metadata_smoke_background_thread",
        {
            "status": "started",
            "interval_seconds": interval_seconds,
            "symbol": symbol,
        },
    )
    thread.start()
    return thread


def _stop_execution_metadata_background_monitor(app: FastAPI) -> None:
    stop_event = getattr(app.state, "execution_metadata_background_stop_event", None)
    thread = getattr(app.state, "execution_metadata_background_thread", None)
    if stop_event is not None:
        stop_event.set()
    if thread is not None and thread.is_alive():
        thread.join(timeout=2.0)
    set_runtime_status(
        "execution_metadata_smoke_background_thread",
        {
            "status": "stopped",
            "interval_seconds": _EXECUTION_METADATA_BACKGROUND_INTERVAL_SECONDS,
        },
    )


def _run_startup_raw_continuity_check(app: FastAPI) -> dict:
    try:
        session = get_db()
        raw_repair_meta = repair_recent_raw_continuity(session, "BTCUSDT", return_details=True)
        raw_status = "repaired" if int(raw_repair_meta.get("inserted_total") or 0) > 0 else "clean"
        raw_payload = {
            "status": raw_status,
            "checked_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "continuity_repair": raw_repair_meta,
        }
        app.state.raw_continuity_status = raw_payload
        set_runtime_status("raw_continuity", raw_payload)
        if raw_status == "repaired":
            logger.warning("啟動檢查發現 raw 資料斷點，已自動回填：%s", raw_repair_meta)
        else:
            logger.info("啟動檢查完成：近期 raw data 無需回填")

        feature_repair_meta = repair_recent_feature_continuity(session, "BTCUSDT", return_details=True)
        feature_status = "repaired" if int(feature_repair_meta.get("inserted_total") or 0) > 0 else "clean"
        if int(feature_repair_meta.get("remaining_missing") or 0) > 0:
            feature_status = "error"
        feature_payload = {
            "status": feature_status,
            "checked_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "continuity_repair": feature_repair_meta,
        }
        app.state.feature_continuity_status = feature_payload
        set_runtime_status("feature_continuity", feature_payload)
        if feature_status == "repaired":
            logger.warning("啟動檢查發現 feature 斷點，已自動補回：%s", feature_repair_meta)
        elif feature_status == "error":
            logger.error("啟動檢查後仍有 feature 斷點未補齊：%s", feature_repair_meta)
        else:
            logger.info("啟動檢查完成：近期 feature data 無需回填")
        return raw_payload
    except Exception as exc:
        payload = {
            "status": "error",
            "checked_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "error": str(exc),
        }
        app.state.raw_continuity_status = payload
        app.state.feature_continuity_status = payload
        set_runtime_status("raw_continuity", payload)
        set_runtime_status("feature_continuity", payload)
        logger.exception("啟動檢查 recent continuity 失敗")
        return payload


@asynccontextmanager
async def lifespan(app: FastAPI):
    """啟動時初始化 DB 與依賴，關閉時清理。"""
    logger.info("Poly-Trader API 啟動中...")
    init_dependencies()
    _run_startup_raw_continuity_check(app)
    from server.dependencies import get_config

    cfg = get_config()
    symbol = (cfg.get("trading", {}) or {}).get("symbol", "BTCUSDT")
    _start_execution_metadata_background_monitor(app, cfg, symbol)
    logger.info("Poly-Trader API 就緒")
    try:
        yield
    finally:
        _stop_execution_metadata_background_monitor(app)
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
    return {
        "status": "ok",
        "raw_continuity": getattr(app.state, "raw_continuity_status", None),
        "feature_continuity": getattr(app.state, "feature_continuity_status", None),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server.main:app", host="127.0.0.1", port=8000, reload=False)
