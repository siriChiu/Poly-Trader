"""
Nest (巢) — Polymarket BTC direction probability from Gamma API
"""
import json
import ssl
from urllib.request import urlopen, Request
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _score_market(question: str) -> int:
    q = (question or '').lower()
    score = 0
    if 'bitcoin' in q or 'btc' in q:
        score += 5
    if 'today' in q or 'this week' in q or 'april' in q:
        score += 2
    if 'above' in q or 'below' in q or 'close' in q or 'touch' in q:
        score += 1
    return score


def _ensure_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return parsed
    return []


def get_nest_feature():
    try:
        # Search a broader active market set and tolerate Gamma's stringified list fields.
        url = "https://gamma-api.polymarket.com/markets?closed=false&limit=500"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urlopen(req, context=ssl.create_default_context(), timeout=10)
        data = json.loads(resp.read().decode())
        btc_down_prob = None
        ranked = sorted(data, key=lambda m: _score_market(m.get('question', '')), reverse=True)
        for m in ranked:
            title = m.get("question", "")
            if _score_market(title) < 5:
                continue
            prices = _ensure_list(m.get("outcomePrices"))
            outcomes = [str(o).lower() for o in _ensure_list(m.get("outcomes"))]
            if len(prices) < 2:
                continue
            parsed = [float(p) for p in prices]
            down_idx = None
            for idx, outcome in enumerate(outcomes):
                if any(word in outcome for word in ["no", "down", "below"]):
                    down_idx = idx
                    break
            if down_idx is None:
                down_idx = 1
            btc_down_prob = parsed[down_idx]
            break

        if btc_down_prob is not None:
            return {
                "feat_nest_pred": float(btc_down_prob - 0.5),
                "nest_raw_prob": float(btc_down_prob),
                "_meta": {"status": "ok"},
            }
    except Exception as e:
        logger.debug(f"Nest fetch failed: {e}")
        return {
            "feat_nest_pred": None,
            "nest_raw_prob": None,
            "_meta": {"status": "fetch_error", "message": str(e)},
        }
    return {
        "feat_nest_pred": None,
        "nest_raw_prob": None,
        "_meta": {"status": "market_not_found", "message": "No active BTC market with parseable outcome prices."},
    }
