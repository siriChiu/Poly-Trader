"""
Scales (鱗片) — Stablecoin Supply Ratio proxy from OKX
SSR = Total BTC Supply / Stablecoin Market Cap
Low SSR = lots of stablecoins ready to buy = bullish
High SSR = stablecoins depleted = bearish (good for SHORT)
DataSource: OKX public stablecoin data + CoinGecko free API
"""
import json, ssl
from datetime import datetime
from urllib.request import urlopen, Request
from utils.logger import setup_logger

logger = setup_logger(__name__)


def get_scales_feature():
    try:
        # Get top stablecoin market caps from CoinGecko (free)
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&category=stablecoins&order=market_cap_desc&per_page=5&page=1"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urlopen(req, context=ssl.create_default_context(), timeout=10)
        data = json.loads(resp.read().decode())
        total_stable = sum(float(c.get("market_cap", 0) or 0) for c in data)
        # BTC circulating supply ~19.7M, but we just use a proxy ratio
        # SSR proxy: stablecoin mcap / 1B (normalized)
        ssr = total_stable / 1_000_000_000_000  # normalize to ~0.1-0.2
        feat = ssr - 0.15  # centered, higher = more stablecoins = less SHORT signal
        return {
            "feat_scales_ssr": float(-feat),  # flip: higher SSR (less stablecoins) = more SHORT
            "scales_total_stablecap_m": total_stable / 1_000_000,
        }
    except Exception as e:
        logger.debug(f"Scales fetch failed: {e}")
    return {"feat_scales_ssr": None, "scales_total_stablecap_m": None}
