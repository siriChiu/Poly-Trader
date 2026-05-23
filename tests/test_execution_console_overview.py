import asyncio

from backtesting import strategy_lab
from database.models import init_db
from execution.console_overview import build_execution_overview
from server.routes import api as api_module


def _status_payload():
    return {
        "symbol": "BTCUSDT",
        "timestamp": "2026-04-18T12:00:00Z",
        "execution_surface_contract": {
            "live_ready": False,
            "live_ready_blockers": ["order ack lifecycle 尚未驗證"],
        },
        "execution": {
            "mode": "paper",
            "venue": "okx",
            "live_runtime_truth": {
                "confidence": 0.60,
                "regime_label": "bull",
                "regime_gate": "ALLOW",
                "structure_bucket": "ALLOW|trend|q65",
                "allowed_layers": 2,
                "allowed_layers_reason": "entry_quality_B_two_layers",
                "sleeve_routing": {
                    "current_regime": "bull",
                    "current_regime_gate": "ALLOW",
                    "current_structure_bucket": "ALLOW|trend|q65",
                    "active_sleeves": [
                        {"key": "trend", "label": "趨勢承接", "summary": "trend", "why": "bull allow"},
                        {"key": "pullback", "label": "回調承接", "summary": "pullback", "why": "bull/chop lane"},
                        {"key": "selective", "label": "高信念精選", "summary": "selective", "why": "quality lane"},
                    ],
                    "inactive_sleeves": [
                        {"key": "rebound", "label": "深跌回補", "summary": "rebound", "why": "not stress lane"},
                    ],
                },
            }
        },
        "account": {
            "requested_symbol": "BTCUSDT",
            "normalized_symbol": "BTC/USDT",
            "balance": {"total": 1000.0, "free": 820.0, "currency": "USDT"},
            "positions": [{"symbol": "BTC/USDT", "size": 0.1}],
            "open_orders": [{"symbol": "BTCUSDT", "qty": 0.01}],
        },
    }



def _seed_execution_strategy_catalog(tmp_path, monkeypatch):
    strategies_dir = tmp_path / "strategies"
    strategies_dir.mkdir()
    monkeypatch.setattr(strategy_lab, "STRATEGIES_DIR", strategies_dir)
    strategy_lab.save_strategy(
        "Trend QA Strategy",
        {
            "type": "hybrid",
            "params": {
                "model_name": "random_forest",
                "entry": {
                    "bias50_max": 0.1,
                },
            },
        },
        {
            "roi": 0.083,
            "profit_factor": 1.21,
            "avg_decision_quality_score": 0.61,
            "avg_expected_win_rate": 0.57,
            "total_trades": 14,
        },
    )


def test_build_execution_overview_exposes_stateful_run_control_beta_contract():
    payload = build_execution_overview(
        _status_payload(),
        config={"trading": {"max_position_ratio": 0.10}},
    )

    assert payload["controls_mode"] == "stateful_run_control_beta"
    assert payload["summary"]["total_profiles"] == 4
    assert payload["summary"]["active_profiles"] == 3
    assert payload["summary"]["monitoring_profiles"] == 3
    assert payload["summary"]["running_runs"] == 0
    assert payload["summary"]["allocation_rule"] == "equal_split_active_sleeves"
    assert payload["operator_message"] == "Bot 營運現在已具備可持久化的運行控制；啟動 / 暫停 / 停止都會保留事件紀錄，且每條運行已可鏡像同商品的執行期 / 對帳摘要，但每個 Bot 的資金 / 持倉 / 委託帳本仍未完全接上。"
    assert payload["upgrade_prerequisite"] == "下一步必須把每個 Bot 的資金 / 持倉 / 委託歸因綁到各自運行，否則這仍只是可持久化的運行控制測試版，不是完整的 Bot 執行期。"
    assert payload["summary"]["operator_message"] == payload["operator_message"]
    assert payload["capital_plan"]["allocation_rule"] == "equal_split_active_sleeves"
    assert payload["capital_plan"]["operator_message"] == "可部署資金目前仍先依風險控管頭寸公式估算，再由啟用倉位腿均分；運行控制雖已可持久化，但每個 Bot 的資金帳本仍未落地。"
    assert payload["capital_plan"]["symbol_scoped_position_count"] == 1
    assert payload["capital_plan"]["symbol_scoped_open_order_count"] == 1
    assert round(payload["capital_plan"]["deployable_capital"], 4) == 60.4
    assert round(payload["capital_plan"]["per_active_profile_budget"], 4) == round(60.4 / 3.0, 4)

    cards = {card["key"]: card for card in payload["profile_cards"]}
    assert cards["trend"]["profile_id"] == "trend"
    assert cards["trend"]["activation_status"] == "active"
    assert cards["trend"]["lifecycle_status"] == "monitoring_shared_symbol"
    assert cards["trend"]["control_contract"]["start_status"] == "ready_control_plane"
    assert cards["trend"]["control_contract"]["mode"] == "stateful_run_control_beta"
    assert cards["trend"]["current_run"] is None
    assert round(cards["trend"]["planned_budget_amount"], 4) == round(60.4 / 3.0, 4)
    assert cards["rebound"]["activation_status"] == "inactive"
    assert cards["rebound"]["lifecycle_status"] == "standby"
    assert cards["rebound"]["planned_budget_amount"] == 0.0



def test_build_execution_overview_surfaces_range_chop_shadow_reduce_playbook():
    status_payload = _status_payload()
    live_truth = status_payload["execution"]["live_runtime_truth"]
    live_truth.update(
        {
            "regime_label": "chop",
            "regime_gate": "BLOCK",
            "structure_bucket": "BLOCK|structure_quality_block|q00",
            "runtime_closure_state": "current_live_deployment_blocked",
            "deployment_blocker": "under_minimum_exact_live_structure_bucket",
            "deployment_blocker_reason": "current-live 精準分桶樣本不足",
            "allowed_layers": 0,
        }
    )
    live_truth["sleeve_routing"] = {
        "current_regime": "chop",
        "current_regime_gate": "BLOCK",
        "current_structure_bucket": "BLOCK|structure_quality_block|q00",
        "active_sleeves": [],
        "inactive_sleeves": [
            {"key": "trend", "label": "趨勢承接", "summary": "trend", "why": "高低震盪，趨勢腿暫停"},
            {"key": "pullback", "label": "回調承接", "summary": "pullback", "why": "盤整回調只允許影子觀察"},
            {"key": "rebound", "label": "深跌回補", "summary": "rebound", "why": "盤整反彈只允許影子觀察"},
            {"key": "selective", "label": "高信念精選", "summary": "selective", "why": "等待精準支持"},
        ],
    }
    high_conviction_topk = {
        "support_context": {
            "current_live_structure_bucket_rows": 2,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 48,
            "support_progress_status": "stalled_under_minimum",
            "stalled_support_accumulation": True,
            "stagnant_run_count": 5,
        }
    }
    status_payload["execution_surface_contract"]["high_conviction_topk"] = high_conviction_topk
    status_payload["execution"]["high_conviction_topk"] = high_conviction_topk

    payload = build_execution_overview(status_payload, config={"trading": {"max_position_ratio": 0.10}})

    playbook = payload["range_chop_playbook"]
    assert playbook["status"] == "shadow_reduce_only"
    assert playbook["shadow_available"] is True
    assert playbook["risk_reduction_allowed"] is True
    assert playbook["buy_add_requires_current_live_gate"] is True
    assert playbook["risk_on_order_enabled"] is False
    assert playbook["order_submission_enabled"] is False
    assert "不是永遠不能實戰" in playbook["operator_message"]
    assert "range_shadow_observe" in playbook["allowed_operator_actions"]
    assert "reduce_position" in playbook["allowed_operator_actions"]

    cards = {card["key"]: card for card in payload["profile_cards"]}
    assert cards["pullback"]["control_contract"]["range_chop_playbook"]["status"] == "shadow_reduce_only"
    assert cards["pullback"]["control_contract"]["risk_reduction_allowed"] is True
    assert cards["pullback"]["control_contract"]["risk_on_order_enabled"] is False
    assert cards["rebound"]["control_contract"]["range_chop_playbook"]["shadow_available"] is True
    assert "影子觀察" in cards["pullback"]["next_operator_action"]
    assert "減風險" in cards["pullback"]["next_operator_action"]



def test_build_execution_overview_exposes_m5_execution_readiness_shadow_ledger_and_venue_proof():
    status_payload = _status_payload()
    live_truth = status_payload["execution"]["live_runtime_truth"]
    live_truth.update(
        {
            "deployment_blocker": "under_minimum_exact_live_structure_bucket",
            "deployment_blocker_reason": "即時部署精準支持樣本不足",
            "runtime_closure_state": "current_live_deployment_blocked",
            "allowed_layers": 0,
            "confidence": 0.67,
            "current_live_structure_bucket": "BLOCK|structure_quality_block|q00",
            "current_live_structure_bucket_rows": 2,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 48,
            "support_route_verdict": "exact_bucket_present_but_below_minimum",
            "support_progress": {
                "status": "stalled_under_minimum",
                "current_rows": 2,
                "minimum_support_rows": 50,
                "gap_to_minimum": 48,
                "stagnant_run_count": 5,
                "stalled_support_accumulation": True,
            },
            "deployment_blocker_details": {
                "release_condition": {
                    "recent_window": 50,
                    "current_recent_window_wins": 8,
                    "required_recent_window_wins": 15,
                    "additional_recent_window_wins_needed": 7,
                    "release_ready": False,
                }
            },
        }
    )
    high_conviction_topk = {
        "deployment_readiness_status": "paper_shadow_only",
        "risk_qualified_count": 6,
        "runtime_blocked_candidate_count": 6,
        "deployable_count": 0,
        "support_context": {
            "current_live_structure_bucket_rows": 2,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 48,
            "support_progress_status": "stalled_under_minimum",
            "stalled_support_accumulation": True,
            "stagnant_run_count": 5,
        },
        "nearest_deployable_rows": [
            {
                "model_name": "random_forest",
                "threshold_name": "top_5pct",
                "deployment_candidate_tier": "research_winner_shadow_only",
                "blocked_only_by_live_guardrails": True,
                "deployable": False,
                "signal": "paper_shadow_only",
                "allowed_layers": 0,
                "win_rate": 0.7808,
                "oos_roi": 1.715,
                "max_drawdown": 0.0698,
                "profit_factor": 7.8873,
                "worst_fold": 0.1442,
                "trade_count": 146,
            }
        ],
    }
    status_payload["execution_surface_contract"]["high_conviction_topk"] = high_conviction_topk
    status_payload["execution"]["high_conviction_topk"] = high_conviction_topk
    status_payload["execution_metadata_smoke"] = {
        "venues": [
            {
                "venue": "okx",
                "credentials_configured": False,
                "proof_state": "missing_runtime_backed_order_lifecycle",
                "blockers": ["credential proof missing", "order ack missing", "fill lifecycle missing"],
                "operator_next_action": "用 dry-run preview + ack / cancel simulation 補證據鏈",
                "verify_next": "python scripts/execution_metadata_smoke.py --symbol BTCUSDT --venues okx",
            }
        ]
    }

    payload = build_execution_overview(status_payload, config={"trading": {"max_position_ratio": 0.10}})

    readiness = payload["execution_readiness"]
    gates = {gate["key"]: gate for gate in readiness["gates"]}
    assert readiness["status"] == "shadow_reduce_only"
    assert readiness["canary_ready"] is False
    assert readiness["risk_on_order_enabled"] is False
    assert readiness["blocking_gate_key"] == "circuit_breaker_gate"
    assert gates["model_gate"]["status"] == "shadow_ready"
    assert gates["current_live_support_gate"]["current"] == 2
    assert gates["current_live_support_gate"]["required"] == 50
    assert gates["current_live_support_gate"]["gap"] == 48
    assert gates["circuit_breaker_gate"]["gap"] == 7
    assert gates["venue_gate"]["status"] == "blocked"
    assert gates["shadow_observation_gate"]["status"] == "ready"
    assert "買入 / 加倉" in " ".join(readiness["what_cannot_do_now"])
    assert "影子觀察" in " ".join(readiness["what_can_do_now"])
    assert readiness["time_to_evidence"]["status"] == "indeterminate_stalled_support"
    assert readiness["time_to_evidence"]["gap_to_minimum"] == 48
    assert readiness["time_to_evidence"]["estimated_heartbeats_to_support"] is None
    assert readiness["time_to_evidence"]["alternative_solution_required"] is True
    assert readiness["alternative_solution_review"]["status"] == "required"
    assert readiness["alternative_solution_review"]["live_exposure_allowed"] is False
    assert readiness["alternative_solution_review"]["order_submission_enabled"] is False
    assert "啟動 paper-shadow" in " ".join(readiness["alternative_solution_review"]["allowed_today"])
    assert "買入 / 加倉" in " ".join(readiness["alternative_solution_review"]["not_allowed"])

    ledger = payload["shadow_trade_ledger"]
    assert ledger["status"] == "recording_ready"
    assert ledger["order_submission_enabled"] is False
    assert ledger["entries"][0]["candidate_model"] == "random_forest"
    assert ledger["entries"][0]["confidence"] == 0.67
    assert ledger["entries"][0]["regime"] == "bull / ALLOW / ALLOW|trend|q65"
    assert ledger["entries"][0]["hypothetical_entry"]["order_submission_enabled"] is False
    assert ledger["entries"][0]["outcome_24h"]["status"] == "pending_observation_window"
    assert ledger["entries"][0]["pyramid_win"] is None

    venue_proof = payload["venue_dry_run_proof"]
    assert venue_proof["status"] == "blocked_missing_runtime_backed_proof"
    assert venue_proof["credential_present"] is False
    assert venue_proof["secrets_redacted"] is True
    assert "api_key" not in str(venue_proof).lower()
    assert "password" not in str(venue_proof).lower()
    assert "token" not in str(venue_proof).lower()
    assert venue_proof["order_preview"]["order_submission_enabled"] is False
    assert venue_proof["ack_simulation"]["runtime_backed"] is False
    assert venue_proof["cancel_simulation"]["runtime_backed"] is False
    assert venue_proof["reconciliation_check"]["runtime_backed"] is False

    answers = payload["canary_gap_answers"]
    assert answers["canary_ready"] is False
    assert answers["blocking_gate"] == "熔斷 gate"
    assert any("還差 48" in item for item in answers["distance_to_canary"])
    assert any("還差 7" in item for item in answers["distance_to_canary"])
    assert any("time-to-evidence" in item for item in answers["distance_to_canary"])
    assert answers["time_to_evidence"]["status"] == "indeterminate_stalled_support"
    assert answers["alternative_solution_review"]["status"] == "required"
    readiness_text = str(readiness) + str(answers)
    for raw_token in ["broader bucket", "reference support", "risk-on", "live automation", "deployable"]:
        assert raw_token not in readiness_text
    assert "寬範圍分桶" in readiness_text
    assert "風險進攻" in readiness_text
    assert answers["first_canary_plan_if_all_gates_pass"]["exposure_pct_max"] == 0.01
    assert answers["first_canary_plan_if_all_gates_pass"]["add_exposure_enabled"] is False



def test_execution_readiness_uses_circuit_breaker_audit_when_exact_support_is_active_blocker():
    status_payload = _status_payload()
    live_truth = status_payload["execution"]["live_runtime_truth"]
    live_truth.update(
        {
            "deployment_blocker": "unsupported_exact_live_structure_bucket",
            "allowed_layers": 0,
            "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q35",
            "current_live_structure_bucket_rows": 0,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 50,
            "support_route_verdict": "exact_bucket_missing",
            "support_progress": {
                "current_rows": 0,
                "minimum_support_rows": 50,
                "gap_to_minimum": 50,
                "stagnant_run_count": 7,
                "stalled_support_accumulation": True,
            },
            "deployment_blocker_details": {
                "support_progress": {
                    "current_rows": 0,
                    "minimum_support_rows": 50,
                    "gap_to_minimum": 50,
                }
            },
        }
    )
    status_payload["circuit_breaker_audit"] = {
        "verdict": "breaker_clear",
        "release_condition": {
            "recent_window": 50,
            "current_recent_window_wins": 50,
            "required_recent_window_wins": 15,
            "additional_recent_window_wins_needed": 0,
            "release_ready": True,
        },
    }

    payload = build_execution_overview(status_payload, config={"trading": {"max_position_ratio": 0.10}})

    readiness = payload["execution_readiness"]
    gates = {gate["key"]: gate for gate in readiness["gates"]}
    assert readiness["canary_ready"] is False
    assert readiness["blocking_gate_key"] == "current_live_support_gate"
    assert gates["current_live_support_gate"]["status"] == "blocked"
    assert gates["current_live_support_gate"]["current"] == 0
    assert gates["current_live_support_gate"]["gap"] == 50
    assert gates["circuit_breaker_gate"]["status"] == "passed"
    assert gates["circuit_breaker_gate"]["current"] == 50
    assert gates["circuit_breaker_gate"]["required"] == 15
    assert gates["circuit_breaker_gate"]["gap"] == 0
    assert "熔斷已解除" in gates["circuit_breaker_gate"]["next_action"]
    assert "即時支持 gate" in payload["canary_gap_answers"]["blocking_gate"]



def test_build_execution_overview_exposes_strategy_snapshot_summary(monkeypatch, tmp_path):
    _seed_execution_strategy_catalog(tmp_path, monkeypatch)

    payload = build_execution_overview(
        _status_payload(),
        config={"trading": {"max_position_ratio": 0.10}},
    )

    cards = {card["key"]: card for card in payload["profile_cards"]}
    trend_binding = cards["trend"]["strategy_binding"]
    pullback_binding = cards["pullback"]["strategy_binding"]

    assert payload["strategy_source_summary"]["strategy_count"] == 1
    assert payload["strategy_source_summary"]["covered_sleeves"] == 1
    assert payload["strategy_source_summary"]["total_sleeves"] == 4
    assert payload["strategy_source_summary"]["missing_sleeves"] == ["pullback", "rebound", "selective"]
    assert payload["strategy_source_summary"]["route"] == "/api/execution/strategies/source"
    assert trend_binding["status"] == "saved_strategy_bound"
    assert trend_binding["strategy_name"] == "Trend QA Strategy"
    assert trend_binding["strategy_source"] == "strategy_lab_saved"
    assert trend_binding["primary_sleeve_key"] == "trend"
    assert trend_binding["strategy_hash"]
    assert pullback_binding["status"] == "missing_saved_strategy"
    assert "尚未找到對應 sleeve 的已儲存策略快照" in pullback_binding["summary"]



def test_api_execution_overview_wraps_status_payload_and_registers_execution_control_routes(monkeypatch, tmp_path):
    async def _fake_status():
        return _status_payload()

    _seed_execution_strategy_catalog(tmp_path, monkeypatch)
    session = init_db(f"sqlite:///{tmp_path / 'execution_console.db'}")
    monkeypatch.setattr(api_module, "get_config", lambda: {"trading": {"max_position_ratio": 0.10}})
    monkeypatch.setattr(api_module, "get_db", lambda: session)
    monkeypatch.setattr(api_module, "api_status", _fake_status)

    payload = asyncio.run(api_module.api_execution_overview())
    strategy_payload = asyncio.run(api_module.api_execution_strategy_source())
    runs_payload = asyncio.run(api_module.api_execution_runs())

    assert payload["symbol"] == "BTCUSDT"
    assert payload["controls_mode"] == "stateful_run_control_beta"
    assert payload["summary"]["active_profiles"] == 3
    assert payload["profile_cards"][0]["controls_mode"] == "stateful_run_control_beta"
    assert payload["profile_cards"][0]["strategy_binding"]["status"] == "saved_strategy_bound"
    assert payload["strategy_source_summary"]["route"] == "/api/execution/strategies/source"
    assert strategy_payload["summary"]["strategy_count"] == 1
    assert strategy_payload["sleeve_bindings"]["trend"]["recommended"]["strategy_name"] == "Trend QA Strategy"
    assert runs_payload["controls_mode"] == "stateful_run_control_beta"
    assert runs_payload["summary"]["total_profiles"] == 4
    assert runs_payload["summary"]["total_runs"] == 0
    route_paths = {getattr(route, "path", None) for route in api_module.router.routes}
    assert "/execution/overview" in route_paths
    assert "/execution/strategies/source" in route_paths
    assert "/execution/profiles" in route_paths
    assert "/execution/runs" in route_paths
    assert "/execution/runs/{profile_id}/start" in route_paths
    assert "/execution/runs/{run_id}/pause" in route_paths
    assert "/execution/runs/{run_id}/stop" in route_paths
    assert "/execution/runs/{run_id}" in route_paths
