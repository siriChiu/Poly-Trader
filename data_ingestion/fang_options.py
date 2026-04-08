"""
Fang (獠牙) — Options Put/Call Ratio from Deribit (public, no key)
"""
import json, ssl, math
from datetime import datetime
from urllib.request import urlopen, Request
from utils.logger import setup_logger

logger = setup_logger(__name__)


def get_fang_feature():
    try:
        url = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urlopen(req, context=ssl.create_default_context(), timeout=12)
        data = json.loads(resp.read().decode())
        instruments = data.get("result", [])
        puts = [i for i in instruments if i.get("instrument_name","").endswith("-P")]
        calls = [i for i in instruments if i.get("instrument_name","").endswith("-C")]
        put_oi = sum(float(i.get("open_interest",0) or 0) for i in puts)
        call_oi = sum(float(i.get("open_interest",0) or 0) for i in calls)
        pcr = put_oi / call_oi if call_oi > 0 else 1.0
        put_iv = sum(float(i.get("mark_iv",0) or 0) for i in puts) / max(len(puts), 1)
        call_iv = sum(float(i.get("mark_iv",0) or 0) for i in calls) / max(len(calls), 1)
        iv_skew = put_iv - call_iv
        # PCR>1 = fear (good for SHORT)
        feat = math.tanh((pcr - 1.0) * 2.0)  # -1..+1
        return {
            "feat_fang_pcr": float(feat),
            "feat_fang_skew": float(iv_skew / 10.0),
            "fang_raw_pcr": pcr,
            "fang_iv_skew_raw": iv_skew,
        }
    except Exception as e:
        logger.debug(f"Fang fetch failed: {e}")
    return {"feat_fang_pcr": None, "feat_fang_skew": None,
            "fang_raw_pcr": None, "fang_iv_skew_raw": None}
