"""
多特徵數據整合收集器 v4
- 支援 raw_events 紀錄
- 支援 market / social / prediction / macro 擴充
- 保留舊 raw_market_data 寫入路徑
"""

import sys
from pathlib import Path
_PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from datetime import datetime
from typing import Optional, Dict
from sqlalchemy.orm import Session

from data_ingestion.body_liquidation import get_body_feature
from data_ingestion.tongue_sentiment import get_tongue_feature
from data_ingestion.nose_futures import get_nose_feature
from data_ingestion.eye_binance import get_eye_feature
from data_ingestion.ear_polymarket import get_ear_feature
from data_ingestion.binance_derivatives import get_derivatives_features
from data_ingestion.macro_data import fetch_macro_latest, compute_nq_features
from data_ingestion.claw_liquidation import get_claw_feature
from data_ingestion.fang_options import get_fang_feature
from data_ingestion.fin_etf import get_fin_feature
from data_ingestion.web_whale import get_web_feature
from data_ingestion.scales_ssr import get_scales_feature
from data_ingestion.nest_polymarket import get_nest_feature
from database.models import RawMarketData, RawEvent
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _raw_event(source: str, entity: str, subtype: str, value, confidence=0.5, quality_score=0.5, payload_json=None, language=None, region=None):
    return RawEvent(
        timestamp=datetime.utcnow(),
        source=source,
        entity=entity,
        subtype=subtype,
        value=value,
        confidence=confidence,
        quality_score=quality_score,
        payload_json=payload_json,
        language=language,
        region=region,
    )


def collect_all_senses(symbol: str = "BTCUSDT") -> Optional[Dict]:
    logger.info("開始多特徵數據收集 v4...")

    body = get_body_feature() or {}
    tongue = get_tongue_feature() or {}
    nose = get_nose_feature() or {}
    eye = get_eye_feature() or {}
    ear = get_ear_feature() or {}
    derivatives = get_derivatives_features(symbol) or {}

    eye_dist_val = eye.get("feat_eye_up") or eye.get("feat_eye_down")
    ear_prob_val = ear.get("prob")
    stablecoin_roc = body.get("raw_roc")
    body_label = body.get("body_label")
    oi_roc = body.get("oi_roc")
    tongue_sentiment = tongue.get("feat_tongue_sentiment")
    volatility = tongue.get("volatility")

    # Fetch VIX/DXY macro data
    macro = fetch_macro_latest()

    record = RawMarketData(
        timestamp=datetime.utcnow(),
        symbol=symbol,
        close_price=eye.get("current_price"),
        volume=eye.get("volume"),
        funding_rate=nose.get("funding_rate_raw"),
        fear_greed_index=tongue.get("fear_greed_index"),
        stablecoin_mcap=stablecoin_roc,
        polymarket_prob=ear_prob_val,
        eye_dist=eye_dist_val,
        ear_prob=ear_prob_val,
        tongue_sentiment=tongue_sentiment,
        volatility=volatility,
        oi_roc=oi_roc,
        body_label=body_label,
        vix_value=macro.get("vix_value"),
        dxy_value=macro.get("dxy_value"),
        nq_value=macro.get("nq_value"),
        # P0/P1: New feature data
        claw_liq_ratio=None,
        claw_liq_total=None,
        fang_pcr=None,
        fang_iv_skew=None,
        fin_etf_netflow=None,
        fin_etf_trend=None,
        web_whale_pressure=None,
        web_large_trades_count=None,
        scales_ssr=None,
        nest_pred=None,
    )
    record._derivatives = derivatives
    # P0/P1: Store new feature in _new_feature for preprocessor
    claw = get_claw_feature()
    fang = get_fang_feature()
    fin = get_fin_feature()
    web = get_web_feature()
    scales = get_scales_feature()
    nest = get_nest_feature()
    nq_feats = compute_nq_features(macro.get('nq_history', []))
    record._new_feature = {
        **claw, **fang, **fin, **web, **scales, **nest, **nq_feats,
    }

    # Actually map new feature to RawMarketData columns
    record.claw_liq_ratio = claw.get("claw_ratio")
    record.claw_liq_total = claw.get("claw_long_liq", 0) + claw.get("claw_short_liq", 0)
    record.fang_pcr = fang.get("fang_raw_pcr")
    record.fang_iv_skew = fang.get("fang_iv_skew_raw")
    fin_val = fin.get("fin_raw_netflow")
    record.fin_etf_netflow = fin_val
    record.fin_etf_trend = None  # need trend calc separately
    record.web_whale_pressure = web.get("web_sell_ratio")
    record.web_large_trades_count = web.get("web_large_trades")
    record.scales_ssr = scales.get("feat_scales_ssr")
    record.nest_pred = nest.get("nest_raw_prob")

    record._raw_events = [
        _raw_event("exchange", symbol, "price", eye.get("current_price"), confidence=0.9, payload_json=str(eye)),
        _raw_event("exchange", symbol, "volume", eye.get("volume"), confidence=0.9, payload_json=str(eye)),
        _raw_event("exchange", symbol, "funding", nose.get("funding_rate_raw"), confidence=0.9, payload_json=str(nose)),
        _raw_event("prediction", symbol, "polymarket_prob", ear_prob_val, confidence=0.8, payload_json=str(ear)),
        _raw_event("sentiment", symbol, "fear_greed", tongue.get("fear_greed_index"), confidence=0.7, payload_json=str(tongue)),
        _raw_event("derivatives", symbol, "oi_roc", oi_roc, confidence=0.8, payload_json=str(derivatives)),
    ]

    logger.info(
        f"收集完成 v5: price={eye.get('current_price')}, LSR={derivatives.get('lsr_ratio')}, "
        f"GSR={derivatives.get('gsr_ratio')}, Taker={derivatives.get('taker_ratio')}, OI={derivatives.get('oi_value')}"
    )
    return record


def run_collection_and_save(session: Session, symbol: str = "BTCUSDT") -> bool:
    try:
        record = collect_all_senses(symbol)
        if record is None:
            logger.error("收集失敗")
            return False

        session.add(record)
        raw_events = getattr(record, '_raw_events', [])
        for evt in raw_events:
            session.add(evt)
        session.commit()
        logger.info(f"Raw data 已保存，id={record.id}, raw_events={len(raw_events)}")
        return True
    except Exception as e:
        session.rollback()
        logger.exception(f"保存 raw data 失敗: {e}")
        return False
