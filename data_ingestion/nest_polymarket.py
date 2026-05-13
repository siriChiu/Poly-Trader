"""
Nest (巢) — Polymarket BTC direction probability from Gamma API
"""
import json
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import urlopen, Request
from utils.logger import setup_logger

logger = setup_logger(__name__)

NEST_MARKETS_URL = "https://gamma-api.polymarket.com/markets?closed=false&limit=500"
NEST_SOURCE = "polymarket_gamma"
TLS_VERIFY_REQUIRED_POLICY = "tls_verify_required_no_insecure_fallback"


def _failure_response(status: str, message: str, **meta):
    safe_meta = {
        "status": status,
        "message": message,
        "source": NEST_SOURCE,
        "endpoint": NEST_MARKETS_URL,
        "trust_policy": TLS_VERIFY_REQUIRED_POLICY,
        **meta,
    }
    return {
        "feat_nest_pred": None,
        "nest_raw_prob": None,
        "_meta": safe_meta,
    }


def _is_tls_verify_failure(exc: BaseException) -> bool:
    reason = getattr(exc, "reason", None)
    if isinstance(exc, ssl.SSLCertVerificationError) or isinstance(reason, ssl.SSLCertVerificationError):
        return True
    text_parts = [str(exc)]
    if reason is not None:
        text_parts.append(str(reason))
    text = " ".join(text_parts).lower()
    return any(
        marker in text
        for marker in (
            "certificate_verify_failed",
            "certificate verify failed",
            "self-signed certificate",
            "unable to get local issuer certificate",
        )
    )


def _tls_verify_failure_response(exc: BaseException):
    detail = str(exc)
    return _failure_response(
        "tls_verify_failed",
        (
            "Polymarket Gamma TLS verification failed; refusing insecure fallback. "
            f"Detail: {detail}"
        ),
        operator_action=(
            "Fix the trusted CA / proxy root for Python and curl, or route the heartbeat through "
            "a verified network path. Do not disable TLS verification in production."
        ),
        tls_verification="required",
    )


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
        req = Request(NEST_MARKETS_URL, headers={"User-Agent": "Mozilla/5.0"})
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
                "_meta": {"status": "ok", "source": NEST_SOURCE, "trust_policy": TLS_VERIFY_REQUIRED_POLICY},
            }
    except HTTPError as e:
        logger.debug(f"Nest HTTP error: {e}")
        return _failure_response("http_error", f"HTTP {e.code}: {e.reason}")
    except (URLError, ssl.SSLError) as e:
        logger.debug(f"Nest fetch failed: {e}")
        if _is_tls_verify_failure(e):
            return _tls_verify_failure_response(e)
        return _failure_response("fetch_error", str(e))
    except Exception as e:
        logger.debug(f"Nest fetch failed: {e}")
        return _failure_response("fetch_error", str(e))
    return _failure_response(
        "market_not_found",
        "No active BTC market with parseable outcome prices.",
    )
