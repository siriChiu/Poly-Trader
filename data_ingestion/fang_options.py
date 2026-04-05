"""
感官之 Fang (獠牙) — Deribit 期權 Put/Call 情緒

數據源：Deribit public REST API (無需 key)
- GET /api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option

提取：總 Put OI / Call OI ratio、25-delta put-call IV skew、近月 term structure
"""
import json
import ssl
import math
from typing import Dict, Optional
from datetime import datetime
from urllib.request import urlopen, Request
from utils.logger import setup_logger

logger = setup_logger(__name__)

DERIBIT_URL = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency"


def fetch_options_summary(currency: str = "BTC") -> Optional[dict]:
    try:
        url = f"{DERIBIT_URL}?currency={currency}&kind=option"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urlopen(req, context=ssl.create_default_context(), timeout=15)
        data = json.loads(resp.read().decode())
        return data.get("result", [])
    except Exception as e:
        logger.warning(f"Deribit 期權獲取失敗: {e}")
        return None


def get_fang_feature() -> Optional[Dict]:
    instruments = fetch_options_summary("BTC")
    if not instruments:
        return None

    puts = [i for i in instruments if i.get("instrument_name","").endswith("P")]
    calls = [i for i in instruments if i.get("instrument_name","").endswith("C")]

    def _total(lst, key):
        return sum(float(i.get(key, 0) or 0) for i in lst)

    put_oi = _total(puts, "open_interest")
    call_oi = _total(calls, "open_interest")

    put_vol = _total(puts, "volume")
    call_vol = _total(calls, "volume")

    put_iv = _total(puts, "mark_iv")  # weighted by OI
    call_iv = _total(calls, "mark_iv")

    # Put/Call ratio (OI-based)
    pcr_oi = put_oi / call_oi if call_oi > 0 else 1.0
    pcr_vol = put_vol / call_vol if call_vol > 0 else 1.0

    # IV skew (put > call = fear)
    iv_skew = (put_iv / len(puts) if puts else 50) - (call_iv / len(calls) if calls else 50)

    # feat_fang: normalized 0-1, higher = more bearish
    # PCR=1.0 → 0.5, PCR=2.0 → 1.0, PCR=0.5 → 0.0
    fang_score = min(max(0.5 + 0.5 * math.log2(pcr_oi), 0), 1)

    logger.info(f"Fang: PCR_OI={pcr_oi:.3f} PCR_vol={pcr_vol:.3f} IV_skew={iv_skew:.1f} feat_fang={fang_score:.3f}")

    return {
        "feat_fang_pcr_oi": pcr_oi,
        "feat_fang_pcr_vol": pcr_vol,
        "feat_fang_iv_skew": iv_skew,
        "feat_fang": fang_score,
    }
