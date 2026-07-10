import asyncio

from backtesting import strategy_lab
from database.models import init_db
from execution.console_overview import attach_live_runner_shadow_gate_to_readiness, build_execution_overview
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
    assert gates["circuit_breaker_gate"]["release_ready"] is False
    assert gates["circuit_breaker_gate"]["next_validation_artifact"] == "data/circuit_breaker_audit.json"
    assert gates["circuit_breaker_gate"]["release_evidence_lane"]["status"] == "needs_more_resolved_wins"
    assert gates["circuit_breaker_gate"]["release_evidence_lane"]["wins_needed"] == 7
    assert gates["circuit_breaker_gate"]["release_evidence_lane"]["order_submission_enabled"] is False
    assert gates["venue_gate"]["status"] == "blocked"
    assert gates["live_canary_policy_gate"]["status"] == "blocked"
    assert "execution.mode must be live" in gates["live_canary_policy_gate"]["blockers"]
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
    assert "shadow_buy" in " ".join(readiness["alternative_solution_review"]["allowed_today"])
    assert "啟動 paper-shadow" in " ".join(readiness["alternative_solution_review"]["allowed_today"])
    assert "買入 / 加倉" in " ".join(readiness["alternative_solution_review"]["not_allowed"])
    milestone = readiness["milestone_progression"]
    assert milestone["status"] == "safe_lane_active"
    assert milestone["current_milestone"] == "M5"
    assert milestone["active_lane"] == "paper_shadow_buy"
    assert milestone["auto_adjustment_applied"] is True
    assert milestone["preferred_entrypoint"]["endpoint"] == "/api/trade"
    assert milestone["preferred_entrypoint"]["payload"] == {"side": "shadow_buy", "symbol": "BTC-USDT", "qty": 0.00001}
    assert milestone["preferred_entrypoint"]["live_order_submitted"] is False

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
    assert venue_proof["fill_simulation"]["runtime_backed"] is False
    assert venue_proof["reconciliation_check"]["runtime_backed"] is False

    answers = payload["canary_gap_answers"]
    assert answers["canary_ready"] is False
    assert answers["blocking_gate"] == "熔斷 gate"
    assert any("還差 48" in item for item in answers["distance_to_canary"])
    assert any("還差 7" in item for item in answers["distance_to_canary"])
    assert any("time-to-evidence" in item for item in answers["distance_to_canary"])
    assert any("Live-canary policy gate" in item for item in answers["distance_to_canary"])
    assert answers["time_to_evidence"]["status"] == "indeterminate_stalled_support"
    assert answers["alternative_solution_review"]["status"] == "required"
    assert answers["milestone_progression"]["active_lane"] == "paper_shadow_buy"
    assert answers["milestone_progression"]["preferred_entrypoint"]["payload"]["side"] == "shadow_buy"
    readiness_text = str(readiness) + str(answers)
    for raw_token in ["broader bucket", "reference support", "risk-on", "live automation", "deployable"]:
        assert raw_token not in readiness_text
    assert "寬範圍分桶" in readiness_text
    assert "風險進攻" in readiness_text
    assert answers["first_canary_plan_if_all_gates_pass"]["exposure_pct_max"] == 0.01
    assert answers["first_canary_plan_if_all_gates_pass"]["add_exposure_enabled"] is False


def test_execution_readiness_requires_live_canary_policy_after_runtime_gates_pass():
    status_payload = _status_payload()
    status_payload["execution_surface_contract"]["live_ready"] = True
    status_payload["execution_surface_contract"]["live_ready_blockers"] = []
    live_truth = status_payload["execution"]["live_runtime_truth"]
    live_truth.update(
        {
            "deployment_blocker": None,
            "runtime_closure_state": "ready",
            "allowed_layers": 1,
            "forecast_edge_bps": 42.0,
            "current_live_structure_bucket": "ALLOW|trend|q65",
            "current_live_structure_bucket_rows": 50,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 0,
            "support_route_verdict": "exact_bucket_supported",
            "support_progress": {
                "current_rows": 50,
                "minimum_support_rows": 50,
                "gap_to_minimum": 0,
            },
            "deployment_blocker_details": {
                "release_condition": {
                    "recent_window": 50,
                    "current_recent_window_wins": 16,
                    "required_recent_window_wins": 15,
                    "additional_recent_window_wins_needed": 0,
                    "release_ready": True,
                }
            },
        }
    )
    high_conviction_topk = {
        "deployment_readiness_status": "deployable_candidates_available",
        "risk_qualified_count": 1,
        "runtime_blocked_candidate_count": 0,
        "deployable_count": 1,
        "nearest_deployable_rows": [{"model_name": "random_forest", "threshold_name": "top_2pct"}],
    }
    status_payload["execution_surface_contract"]["high_conviction_topk"] = high_conviction_topk
    status_payload["execution"]["high_conviction_topk"] = high_conviction_topk
    status_payload["venue_dry_run_proof"] = {
        "artifact": "venue_dry_run_proof",
        "status": "runtime_backed_proof_complete",
        "credential_present": True,
        "secrets_redacted": True,
        "runtime_ready": True,
        "runtime_ready_count": 1,
        "venues_checked": 1,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "dry_run_only": True,
        "runtime_ready_blockers": [],
        "order_preview": {"status": "ready", "order_submission_enabled": False},
        "ack_simulation": {"status": "ready", "runtime_backed": True},
        "cancel_simulation": {"status": "ready", "runtime_backed": True},
        "fill_simulation": {"status": "ready", "runtime_backed": True},
        "reconciliation_check": {"status": "ready", "runtime_backed": True},
    }

    missing_policy_payload = build_execution_overview(
        status_payload,
        config={
            "execution": {
                "mode": "paper",
                "enable_live_trading": False,
                "cost_aware_edge": {
                    "taker_fee_bps": 8,
                    "spread_bps": 2,
                    "slippage_bps": 3,
                    "volatility_buffer_bps": 5,
                    "drawdown_buffer_bps": 4,
                },
            }
        },
    )
    missing_policy_readiness = missing_policy_payload["execution_readiness"]
    missing_policy_gates = {gate["key"]: gate for gate in missing_policy_readiness["gates"]}
    assert missing_policy_readiness["canary_ready"] is False
    assert missing_policy_readiness["blocking_gate_key"] == "live_canary_policy_gate"
    assert missing_policy_gates["live_canary_policy_gate"]["status"] == "blocked"
    assert "execution.mode must be live" in missing_policy_gates["live_canary_policy_gate"]["blockers"]

    too_wide_policy_payload = build_execution_overview(
        status_payload,
        config={
            "trading": {"dry_run": False},
            "execution": {
                "mode": "live",
                "enable_live_trading": True,
                "cost_aware_edge": {
                    "taker_fee_bps": 8,
                    "spread_bps": 2,
                    "slippage_bps": 3,
                    "volatility_buffer_bps": 5,
                    "drawdown_buffer_bps": 4,
                },
                "live_canary": {
                    "enabled": True,
                    "allowed_symbols": ["BTC/USDT"],
                    "max_base_qty_by_symbol": {"BTC/USDT": 0.001},
                },
            },
        },
    )
    too_wide_gates = {gate["key"]: gate for gate in too_wide_policy_payload["execution_readiness"]["gates"]}
    assert too_wide_policy_payload["execution_readiness"]["canary_ready"] is False
    assert too_wide_gates["live_canary_policy_gate"]["status"] == "blocked"
    assert "symbol max_base_qty_by_symbol cap must be <= 0.0001" in too_wide_gates["live_canary_policy_gate"]["blockers"]

    ready_policy_payload = build_execution_overview(
        status_payload,
        config={
            "trading": {"dry_run": False},
            "execution": {
                "mode": "live",
                "enable_live_trading": True,
                "cost_aware_edge": {
                    "taker_fee_bps": 8,
                    "spread_bps": 2,
                    "slippage_bps": 3,
                    "volatility_buffer_bps": 5,
                    "drawdown_buffer_bps": 4,
                },
                "live_canary": {
                    "enabled": True,
                    "allowed_symbols": ["BTC/USDT"],
                    "max_base_qty_by_symbol": {"BTC/USDT": 0.0001},
                },
            },
        },
    )
    ready_readiness = ready_policy_payload["execution_readiness"]
    ready_gates = {gate["key"]: gate for gate in ready_readiness["gates"]}
    assert ready_gates["live_canary_policy_gate"]["status"] == "passed"
    assert ready_readiness["canary_ready"] is True
    assert ready_readiness["status"] == "canary_ready"
    assert ready_readiness["milestone_progression"]["status"] == "bounded_canary_ready"
    assert ready_readiness["milestone_progression"]["active_lane"] == "bounded_live_canary"


def test_live_runner_24h_shadow_gate_is_hard_canary_readiness_and_milestone_gate():
    milestone = {
        "status": "bounded_canary_ready",
        "current_milestone": "M5",
        "active_lane": "bounded_live_canary",
        "active_lane_label": "M5 bounded live-canary",
        "milestones": [{"key": "M5_bounded_canary_or_safe_lane", "status": "passed"}],
    }
    overview = {
        "symbol": "BTCUSDT",
        "execution_readiness": {
            "status": "canary_ready",
            "stage_label": "Canary-ready",
            "canary_ready": True,
            "risk_on_order_enabled": False,
            "order_submission_enabled": False,
            "gates": [{"key": "live_canary_policy_gate", "label": "Live-canary policy", "status": "passed", "passed": True}],
            "what_can_do_now": [],
            "milestone_progression": dict(milestone),
        },
        "canary_gap_answers": {
            "canary_ready": True,
            "milestone_progression": dict(milestone),
            "first_canary_plan_if_all_gates_pass": {"stop_conditions": ["gate regression"]},
        },
    }

    blocked = attach_live_runner_shadow_gate_to_readiness(
        overview,
        {
            "status": "needs_live_runner_shadow_run",
            "summary": {"candidate_decisions": 0, "jsonl_backed": False, "live_order_submitted": False},
            "shadow_evidence_gate": {"status": "needs_live_runner_shadow_run", "candidate_decisions": 0, "resolved_outcomes": 0},
        },
    )
    blocked_readiness = blocked["execution_readiness"]
    blocked_gates = {gate["key"]: gate for gate in blocked_readiness["gates"]}
    assert blocked_readiness["canary_ready"] is False
    assert blocked_readiness["blocking_gate_key"] == "live_runner_24h_shadow_gate"
    assert blocked_gates["live_runner_24h_shadow_gate"]["status"] == "blocked"
    assert blocked_readiness["milestone_progression"]["active_lane"] == "standalone_live_runner_shadow_candidate"
    assert blocked_readiness["milestone_progression"]["preferred_entrypoint"]["command"].endswith("--dry-run --no-submit --shadow-candidate")
    roadmap = {item["key"]: item for item in blocked_readiness["milestone_progression"]["milestones"]}
    assert roadmap["M4_5_live_runner_24h_shadow_evidence"]["status"] == "blocked"

    passed = attach_live_runner_shadow_gate_to_readiness(
        overview,
        {
            "status": "runner_24h_resolved_evidence_ready",
            "summary": {"candidate_decisions": 2, "jsonl_backed": True, "live_order_submitted": False},
            "shadow_evidence_gate": {
                "status": "runner_24h_resolved_evidence_ready",
                "candidate_decisions": 2,
                "resolved_outcomes": 1,
                "pending_outcomes": 0,
                "awaiting_label_replay": 0,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "live_order_submitted": False,
            },
        },
    )
    passed_readiness = passed["execution_readiness"]
    passed_gates = {gate["key"]: gate for gate in passed_readiness["gates"]}
    assert passed_readiness["canary_ready"] is True
    assert passed_gates["live_runner_24h_shadow_gate"]["status"] == "passed"
    assert passed_gates["live_runner_24h_shadow_gate"]["resolved_outcomes"] == 1
    passed_roadmap = {item["key"]: item for item in passed_readiness["milestone_progression"]["milestones"]}
    assert passed_roadmap["M4_5_live_runner_24h_shadow_evidence"]["status"] == "passed"
    assert passed["canary_gap_answers"]["first_canary_plan_if_all_gates_pass"]["required_shadow_evidence_gate"] == "standalone runner 24h shadow evidence resolved ≥ 1 且 JSONL/DB 對齊"



def test_build_execution_overview_prefers_standalone_venue_dry_run_proof_artifact():
    status_payload = _status_payload()
    status_payload["execution_metadata_smoke"] = {
        "venues": [
            {
                "venue": "okx",
                "credentials_configured": True,
                "proof_state": "runtime_backed_proof_complete",
                "blockers": [],
                "operator_next_action": "metadata fallback should not win",
            }
        ]
    }
    status_payload["venue_dry_run_proof"] = {
        "artifact": "venue_dry_run_proof",
        "artifact_path": "data/venue_dry_run_proof.json",
        "status": "blocked_missing_runtime_backed_proof",
        "symbol": "BTC/USDT",
        "runtime_ready": False,
        "runtime_ready_count": 0,
        "venues_checked": 2,
        "credential_present": False,
        "secrets_redacted": True,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "dry_run_only": True,
        "runtime_ready_blockers": ["runtime-backed fill proof missing"],
        "api_key": "should_not_leak",
        "password": "should_not_leak",
        "venues": [
            {
                "venue": "okx",
                "credentials_configured": False,
                "credential_present": False,
                "proof_state": "public_metadata_only",
                "runtime_ready": False,
                "blockers": ["runtime-backed fill proof missing"],
                "order_preview": {
                    "status": "blocked_missing_credentials",
                    "order_submission_enabled": False,
                    "api_key": "should_not_leak",
                },
                "ack_simulation": {"status": "blocked_missing_credentials", "runtime_backed": False},
                "cancel_simulation": {"status": "blocked_missing_credentials", "runtime_backed": False},
                "fill_simulation": {"status": "blocked_missing_credentials", "runtime_backed": False},
                "reconciliation_check": {"status": "blocked_missing_credentials", "runtime_backed": False},
                "operator_next_action": "standalone artifact action",
            }
        ],
        "operator_next_action": "standalone artifact action",
        "verify_next": "python scripts/venue_dry_run_proof.py",
    }

    payload = build_execution_overview(status_payload, config={"trading": {"max_position_ratio": 0.10}})

    venue_proof = payload["venue_dry_run_proof"]
    assert venue_proof["artifact"] == "venue_dry_run_proof"
    assert venue_proof["artifact_path"] == "data/venue_dry_run_proof.json"
    assert venue_proof["status"] == "blocked_missing_runtime_backed_proof"
    assert venue_proof["runtime_ready"] is False
    assert venue_proof["runtime_ready_count"] == 0
    assert venue_proof["venues_checked"] == 2
    assert venue_proof["credential_present"] is False
    assert venue_proof["secrets_redacted"] is True
    assert venue_proof["order_preview"]["status"] == "blocked_missing_credentials"
    assert venue_proof["ack_simulation"]["status"] == "blocked_missing_credentials"
    assert venue_proof["cancel_simulation"]["status"] == "blocked_missing_credentials"
    assert venue_proof["fill_simulation"]["status"] == "blocked_missing_credentials"
    assert venue_proof["reconciliation_check"]["status"] == "blocked_missing_credentials"
    assert venue_proof["operator_next_action"] == "standalone artifact action"
    assert "api_key" not in str(venue_proof).lower()
    assert "password" not in str(venue_proof).lower()
    assert "token" not in str(venue_proof).lower()

    gates = {gate["key"]: gate for gate in payload["execution_readiness"]["gates"]}
    assert gates["venue_gate"]["status"] == "blocked"
    assert gates["venue_gate"]["summary"] == "venue dry-run proof blocked_missing_runtime_backed_proof；runtime_ready 0/2"
    assert gates["venue_gate"]["next_action"] == "standalone artifact action"



def test_build_execution_overview_exposes_compact_customer_safe_alternative_proof():
    status_payload = _status_payload()
    status_payload["customer_safe_alternative_proof"] = {
        "artifact": "customer_safe_alternative_proof",
        "generated_at": "2026-06-04T08:41:17Z",
        "canary_ready": False,
        "live_exposure_allowed": False,
        "order_submission_enabled": False,
        "risk_on_order_enabled": False,
        "support_rows": 0,
        "minimum_support_rows": 50,
        "support_gap": 50,
        "blocking_gate": "circuit_breaker_gate",
        "primary_blocking_gate": "circuit_breaker_gate",
        "blocking_gates": ["circuit_breaker_gate", "current_live_support_gate", "model_gate", "venue_gate"],
        "breaker_release_ready": False,
        "current_recent_window_wins": 9,
        "required_recent_window_wins": 15,
        "additional_recent_window_wins_needed": 6,
        "topk_deployable_rows": 0,
        "topk_risk_qualified_rows": 6,
        "topk_runtime_blocked_candidate_rows": 6,
        "topk_support_context_status": "fresh_live_probe_overlay",
        "topk_support_context_freshness_status": "fresh",
        "topk_support_context_deployment_blocking": False,
        "topk_live_truth_overlay_blocker": "—",
        "venue_runtime_ready": False,
        "venue_status": "blocked_missing_runtime_backed_proof",
        "blocked_live_lane_count": 1,
        "alternative_solution_required": True,
        "alternative_solution_option_count": 3,
        "alternative_solution_options": 3,
        "selected_alternative_solution": "paper_shadow_decision_support_sleeve",
        "selected_alternative": "paper_shadow_decision_support_sleeve",
        "selected_next_customer_artifact": "data/customer_safe_alternative_proof.json",
        "selected_next_artifact": "data/customer_safe_alternative_proof.json",
        "next_customer_action_count": 1,
        "summary": {
            "operator_summary": "只允許 paper/shadow；真實買入 / 加倉維持 fail-closed。",
        },
        "alternative_solution_portfolio": {
            "pm_challenge_answered": True,
            "option_count": 3,
            "selected_option": "paper_shadow_decision_support_sleeve",
            "selected_next_artifact": "data/customer_safe_alternative_proof.json",
            "time_to_evidence_bucket": "semantic_rebaseline_review_required_before_reference_rows_count",
            "missing_capability_class": "Constraint/Review",
        },
        "alternative_solutions": [
            {
                "id": "paper_shadow_decision_support_sleeve",
                "role": "customer_usable_now",
                "next_artifact": "data/customer_safe_alternative_proof.json",
                "deployable": False,
                "live_exposure_allowed": False,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
            },
            {
                "id": "semantic_rebaseline_review",
                "role": "support_policy_alternative",
                "next_artifact": "OOS + Top-K support audit replay",
                "deployable": False,
                "live_exposure_allowed": False,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
            },
            {
                "id": "venue_dry_run_readiness_proof",
                "role": "delivery_risk_reduction",
                "next_artifact": "venue dry-run lifecycle proof checklist",
                "deployable": False,
                "live_exposure_allowed": False,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
            },
        ],
        "next_customer_actions": [
            {
                "id": "open_execution_paper_shadow",
                "surface": "/execution",
                "mode": "paper_shadow",
                "expected_evidence": "paper/shadow outcome proof",
                "live_exposure_allowed": False,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
            }
        ],
        "blocked_live_lanes": [
            {
                "id": "live_buy_add_exposure",
                "blocking_gate": "circuit_breaker_gate",
                "blocked_actions": ["live_buy", "live_add"],
                "live_exposure_allowed": False,
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "allowed_alternative": "paper/shadow dry-run",
                "release_condition": {
                    "primary_blocking_gate": "circuit_breaker_gate",
                    "breaker_release_ready": False,
                    "current_recent_window_wins": 9,
                    "required_recent_window_wins": 15,
                    "additional_recent_window_wins_needed": 6,
                    "support_rows": 0,
                    "minimum_support_rows": 50,
                    "support_gap": 50,
                    "topk_deployable_rows": 0,
                    "venue_runtime_ready": False,
                    "venue_status": "blocked_missing_runtime_backed_proof",
                },
            }
        ],
        "source_artifacts": {"runtime_context": {"api_key": "should_not_leak"}},
    }

    payload = build_execution_overview(status_payload, config={"trading": {"max_position_ratio": 0.10}})

    proof = payload["customer_safe_alternative_proof"]
    assert proof["artifact"] == "customer_safe_alternative_proof"
    assert proof["live_exposure_allowed"] is False
    assert proof["order_submission_enabled"] is False
    assert proof["risk_on_order_enabled"] is False
    assert proof["support_rows"] == 0
    assert proof["support_gap"] == 50
    assert proof["alternative_solution_options"] == 3
    assert proof["alternative_solution_option_count"] == 3
    assert proof["selected_alternative"] == "paper_shadow_decision_support_sleeve"
    assert proof["selected_alternative"] == proof["selected_alternative_solution"]
    assert proof["selected_next_artifact"] == proof["selected_next_customer_artifact"]
    assert proof["summary"]["selected_alternative"] == proof["selected_alternative"]
    assert proof["summary"]["alternative_solution_options"] == 3
    assert len(proof["alternative_solutions"]) == 3
    assert proof["alternative_solutions"][0]["deployable"] is False
    assert proof["next_customer_actions"][0]["order_submission_enabled"] is False
    assert proof["blocked_live_lanes"][0]["release_condition"]["support_gap"] == 50
    assert "source_artifacts" not in proof
    assert "api_key" not in str(proof).lower()
    assert "should_not_leak" not in str(proof)


def test_high_conviction_shadow_contract_preserves_zero_support_rows_needed():
    status_payload = _status_payload()
    status_payload["execution"]["live_runtime_truth"]["deployment_blocker"] = "current_live_deployment_blocker"
    high_conviction_topk = {
        "deployment_readiness_status": "paper_shadow_only",
        "risk_qualified_count": 3,
        "runtime_blocked_candidate_count": 3,
        "deployable_count": 0,
        "support_context": {
            "current_live_structure_bucket_rows": 50,
            "minimum_support_rows": 50,
            "support_rows_needed": 0,
            # Stale fallback from an older artifact must not override the explicit zero.
            "current_live_structure_bucket_gap_to_minimum": 48,
        },
        "nearest_deployable_rows": [
            {
                "model_name": "random_forest",
                "deployment_candidate_tier": "runtime_blocked_oos_pass",
                "blocked_only_by_live_guardrails": True,
                "deployable": False,
            }
        ],
    }
    status_payload["execution_surface_contract"]["high_conviction_topk"] = high_conviction_topk
    status_payload["execution"]["high_conviction_topk"] = high_conviction_topk

    payload = build_execution_overview(status_payload, config={"trading": {"max_position_ratio": 0.10}})

    cards = {card["key"]: card for card in payload["profile_cards"]}
    selective_contract = cards["selective"]["control_contract"]["high_conviction_topk"]
    assert selective_contract["support_context"]["support_rows_needed"] == 0
    assert selective_contract["support_summary"] == "支持 50/50 · 缺 0"
    assert "缺 0" in selective_contract["start_reason"]
    assert "缺 48" not in selective_contract["start_reason"]



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
    assert readiness["blocking_gate_key"] == "current_lane_actionability_gate"
    assert gates["current_lane_actionability_gate"]["status"] == "shadow_observation_ready_live_blocked"
    assert gates["current_lane_actionability_gate"]["passed"] is False
    assert gates["current_lane_actionability_gate"]["shadow_ready"] is True
    assert gates["current_lane_actionability_gate"]["sub_gates"][0]["key"] == "strict_exact_support_subgate"
    assert gates["current_lane_actionability_gate"]["sub_gates"][0]["current"] == 0
    assert gates["current_lane_actionability_gate"]["sub_gates"][0]["gap"] == 50
    assert gates["current_lane_actionability_gate"]["sub_gates"][2]["key"] == "cost_aware_edge_subgate"
    assert gates["current_lane_actionability_gate"]["sub_gates"][2]["status"] == "needs_forecast_edge"
    assert gates["current_lane_actionability_gate"]["sub_gates"][2]["required_edge_bps"] == 15.0
    assert gates["current_lane_actionability_gate"]["sub_gates"][2]["cost_components_bps"] == {
        "fee_bps": 5.0,
        "spread_bps": 3.0,
        "slippage_bps": 2.0,
        "volatility_buffer_bps": 5.0,
        "drawdown_buffer_bps": 0.0,
    }
    assert gates["current_live_support_gate"]["status"] == "blocked"
    assert gates["current_live_support_gate"]["current"] == 0
    assert gates["current_live_support_gate"]["gap"] == 50
    assert gates["circuit_breaker_gate"]["status"] == "passed"
    assert gates["circuit_breaker_gate"]["current"] == 50
    assert gates["circuit_breaker_gate"]["required"] == 15
    assert gates["circuit_breaker_gate"]["gap"] == 0
    assert "熔斷已解除" in gates["circuit_breaker_gate"]["next_action"]
    assert "當前 lane 可行動 gate" in payload["canary_gap_answers"]["blocking_gate"]


def test_execution_readiness_cost_aware_edge_subgate_passes_only_with_edge_above_costs():
    status_payload = _status_payload()
    live_truth = status_payload["execution"]["live_runtime_truth"]
    live_truth.update(
        {
            "deployment_blocker": "unsupported_exact_live_structure_bucket",
            "allowed_layers": 0,
            "forecast_edge_bps": 42.0,
            "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q85",
            "current_live_structure_bucket_rows": 0,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 50,
            "support_route_verdict": "exact_bucket_missing",
            "support_progress": {
                "current_rows": 0,
                "minimum_support_rows": 50,
                "gap_to_minimum": 50,
            },
        }
    )
    payload = build_execution_overview(
        status_payload,
        config={
            "trading": {"max_position_ratio": 0.10},
            "execution": {
                "cost_aware_edge": {
                    "taker_fee_bps": 8,
                    "spread_bps": 2,
                    "slippage_bps": 3,
                    "volatility_buffer_bps": 5,
                    "drawdown_buffer_bps": 4,
                }
            },
        },
    )

    gates = {gate["key"]: gate for gate in payload["execution_readiness"]["gates"]}
    current_lane = gates["current_lane_actionability_gate"]
    cost_gate = {gate["key"]: gate for gate in current_lane["sub_gates"]}["cost_aware_edge_subgate"]
    assert current_lane["passed"] is False
    assert current_lane["paper_shadow_available"] is True
    assert current_lane["paper_shadow_buy_candidate_ready"] is True
    assert cost_gate["status"] == "passed"
    assert cost_gate["current"] == 42.0
    assert cost_gate["required"] == 22.0
    assert cost_gate["gap"] == 0.0
    assert cost_gate["order_submission_enabled"] is False
    assert cost_gate["risk_on_order_enabled"] is False


def test_execution_readiness_cost_aware_edge_uses_default_inputs_when_forecast_exists():
    status_payload = _status_payload()
    live_truth = status_payload["execution"]["live_runtime_truth"]
    live_truth.update(
        {
            "deployment_blocker": "unsupported_exact_live_structure_bucket",
            "allowed_layers": 0,
            "forecast_edge_bps": 16.0,
            "current_live_structure_bucket": "CAUTION|base_caution_regime_or_bias|q85",
            "current_live_structure_bucket_rows": 0,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 50,
            "support_route_verdict": "exact_bucket_missing",
            "support_progress": {
                "current_rows": 0,
                "minimum_support_rows": 50,
                "gap_to_minimum": 50,
            },
        }
    )
    payload = build_execution_overview(status_payload, config={"trading": {"max_position_ratio": 0.10}})

    gates = {gate["key"]: gate for gate in payload["execution_readiness"]["gates"]}
    current_lane = gates["current_lane_actionability_gate"]
    cost_gate = {gate["key"]: gate for gate in current_lane["sub_gates"]}["cost_aware_edge_subgate"]
    assert current_lane["passed"] is False
    assert current_lane["paper_shadow_buy_candidate_ready"] is True
    assert cost_gate["status"] == "passed"
    assert cost_gate["current"] == 16.0
    assert cost_gate["required"] == 15.0
    assert cost_gate["cost_components_bps"] == {
        "fee_bps": 5.0,
        "spread_bps": 3.0,
        "slippage_bps": 2.0,
        "volatility_buffer_bps": 5.0,
        "drawdown_buffer_bps": 0.0,
    }
    assert cost_gate["gap"] == 0.0


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
        payload = _status_payload()
        payload["venue_dry_run_proof"] = {
            "artifact": "venue_dry_run_proof",
            "artifact_path": "data/venue_dry_run_proof.json",
            "status": "blocked_missing_runtime_backed_proof",
            "credential_present": False,
            "secrets_redacted": True,
            "runtime_ready": False,
            "runtime_ready_count": 0,
            "venues_checked": 2,
            "order_preview": {"status": "blocked_missing_credentials", "order_submission_enabled": False},
            "ack_simulation": {"status": "blocked_missing_credentials", "runtime_backed": False},
            "cancel_simulation": {"status": "blocked_missing_credentials", "runtime_backed": False},
            "fill_simulation": {"status": "blocked_missing_credentials", "runtime_backed": False},
            "reconciliation_check": {"status": "blocked_missing_credentials", "runtime_backed": False},
        }
        return payload

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
    assert payload["venue_dry_run_proof"]["artifact_path"] == "data/venue_dry_run_proof.json"
    assert payload["venue_dry_run_proof"]["fill_simulation"]["status"] == "blocked_missing_credentials"
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
