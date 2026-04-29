from execution.metadata_smoke import run_metadata_smoke


class FakeAdapter:
    venue = "fake"

    def __init__(self, config, dry_run=True):
        self.config = config or {}
        self.dry_run = dry_run

    def credentials_configured(self):
        return bool(self.config.get("api_key"))

    def market_rules(self, symbol):
        return {
            "symbol": symbol,
            "base": "BTC",
            "quote": "USDT",
            "min_qty": 0.001,
            "min_cost": 10.0,
            "amount_precision": 3,
            "price_precision": 2,
            "step_size": "0.001",
            "tick_size": "0.10",
            "qty_contract": {"step_size": "0.001", "precision": 3, "min_qty": 0.001},
            "price_contract": {"tick_size": "0.10", "precision": 2},
        }


class BrokenAdapter(FakeAdapter):
    venue = "broken"

    def market_rules(self, symbol):
        raise RuntimeError(f"metadata unavailable for {symbol}")


def test_run_metadata_smoke_collects_contract_for_public_venues(monkeypatch):
    monkeypatch.setattr(
        "execution.metadata_smoke.ADAPTER_FACTORIES",
        {"binance": FakeAdapter, "okx": FakeAdapter},
    )

    payload = run_metadata_smoke(
        {
            "execution": {
                "venues": {
                    "binance": {"enabled": True, "api_key": "k"},
                    "okx": {"enabled": False},
                }
            }
        },
        symbol="BTCUSDT",
        venues=["binance", "okx"],
    )

    assert payload["symbol"] == "BTC/USDT"
    assert payload["ok_count"] == 2
    assert payload["all_ok"] is True
    assert payload["results"]["binance"]["contract"]["step_size"] == "0.001"
    assert payload["results"]["okx"]["enabled_in_config"] is False
    assert payload["results"]["binance"]["credentials_configured"] is True
    assert payload["results"]["binance"]["proof_state"] == "credentials_configured_missing_runtime_lifecycle"
    assert payload["results"]["binance"]["readiness_scope"] == "venue_runtime_proof_required"
    assert payload["results"]["binance"]["blockers"] == [
        "order ack lifecycle 尚未驗證",
        "fill lifecycle 尚未驗證",
    ]
    assert payload["results"]["binance"]["operator_next_action"].startswith("使用 binance 沙盒")
    assert "委託確認 / 成交 / 取消證據" in payload["results"]["binance"]["verify_next"]
    assert payload["results"]["okx"]["proof_state"] == "config_disabled_metadata_only"
    assert "場館設定停用" in payload["results"]["okx"]["blockers"]
    assert "live exchange credential 尚未驗證" in payload["results"]["okx"]["blockers"]


def test_run_metadata_smoke_surfaces_failures_without_hiding_venue(monkeypatch):
    monkeypatch.setattr(
        "execution.metadata_smoke.ADAPTER_FACTORIES",
        {"binance": FakeAdapter, "okx": BrokenAdapter},
    )

    payload = run_metadata_smoke(
        {"execution": {"venues": {"binance": {"enabled": True}, "okx": {"enabled": True}}}},
        symbol="BTCUSDT",
        venues=["binance", "okx"],
    )

    assert payload["ok_count"] == 1
    assert payload["all_ok"] is False
    assert payload["results"]["okx"]["ok"] is False
    assert "metadata unavailable" in payload["results"]["okx"]["error"]
    assert payload["results"]["okx"]["proof_state"] == "metadata_contract_failed"
    assert payload["results"]["okx"]["readiness_scope"] == "venue_runtime_proof_required"
    assert "元資料契約尚未通過" in payload["results"]["okx"]["blockers"]
    assert "order ack lifecycle 尚未驗證" in payload["results"]["okx"]["blockers"]
    assert payload["results"]["okx"]["operator_next_action"].startswith("先修復 okx 元資料檢查")
