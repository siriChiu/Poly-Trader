#!/usr/bin/env python3
"""Independently verify the public microstructure source/contract artifacts."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "microstructure_source_probe.json"
DEFAULT_CONTRACT = ROOT / "data" / "microstructure_contract.json"
MAX_SOURCE_AGE_SECONDS = 300.0
REQUIRED_FEATURES = {
    "orderbook_imbalance_l1",
    "orderbook_imbalance_l5",
    "spread_bps",
    "depth_50bps",
    "depth_200bps",
    "microprice_deviation",
    "trade_flow_imbalance",
    "liquidity_stress_score",
}


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError(f"{path} root must be an object")
    return payload


def _parse_time(value: Any) -> datetime:
    if not value:
        raise AssertionError("missing timestamp")
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _finite_number(value: Any, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise AssertionError(f"{label} must be a finite number")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def verify(source_path: Path, contract_path: Path, *, now: datetime | None = None) -> dict[str, Any]:
    source = _load(source_path)
    contract = _load(contract_path)
    checked_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    source_info = _dict(source.get("source"))
    coverage = _dict(source.get("coverage"))
    forecast = _dict(source.get("forecast"))
    features = _dict(source.get("features"))

    assert source_info.get("name") == "okx_public_market_api", source_info
    assert source_info.get("configured") is True
    assert source_info.get("available") is True
    assert source_info.get("freshness_status") == "fresh"
    observed_at = _parse_time(source_info.get("observed_at"))
    age_seconds = max((checked_at - observed_at).total_seconds(), 0.0)
    assert age_seconds <= MAX_SOURCE_AGE_SECONDS, f"source is stale: {age_seconds:.1f}s"
    assert coverage.get("coverage_ratio", 0) > 0
    assert int(coverage.get("trades_observed", 0)) > 0
    assert set(features) >= REQUIRED_FEATURES
    for name in REQUIRED_FEATURES:
        item = features.get(name)
        if not isinstance(item, dict):
            raise AssertionError(f"feature {name} must be an object")
        _finite_number(item.get("value"), f"feature {name}")
        assert item.get("source") == "okx_public_market_api:BTC-USDT"
        assert item.get("formula"), name

    assert forecast.get("available") is False
    assert forecast.get("lineage_status") == "not_calibrated_from_source_snapshot"
    assert source.get("forecast_edge_bps") is None

    contract_source = _dict(contract.get("source"))
    contract_decision = _dict(contract.get("decision_contract"))
    assert contract_source.get("name") == "okx_public_market_api"
    assert contract_source.get("available") is True
    assert contract.get("forecast_edge_bps") is None
    assert contract_decision.get("observation_only") is True
    assert contract_decision.get("paper_shadow_risk_on_allowed") is False
    assert contract_decision.get("live_risk_on_allowed") is False

    return {
        "source_backed": True,
        "source": source_info.get("name"),
        "observed_at": source_info.get("observed_at"),
        "age_seconds": round(age_seconds, 3),
        "coverage_ratio": coverage.get("coverage_ratio"),
        "feature_count": len(REQUIRED_FEATURES),
        "forecast_edge_bps": contract.get("forecast_edge_bps"),
        "forecast_calibration": "missing",
        "observation_only": contract_decision.get("observation_only"),
        "paper_shadow_risk_on_allowed": contract_decision.get("paper_shadow_risk_on_allowed"),
        "live_risk_on_allowed": contract_decision.get("live_risk_on_allowed"),
        "single_failed_gate": "forecast_calibration_artifact",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    args = parser.parse_args(argv)
    result = verify(args.source, args.contract)
    print("microstructure_source_verifier: " + json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
