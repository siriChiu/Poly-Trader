import asyncio
import json
from copy import deepcopy
from types import SimpleNamespace
from typing import Any

from backtesting import strategy_lab
from database.models import init_db
from execution import control_plane as control_plane_module
from execution import live_runner as live_runner_module
from execution import strategy_bundle as strategy_bundle_module
from server.routes import api as api_module
from sqlalchemy import text


def _local_request() -> Any:
    return SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))


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
            "guardrails": {
                "kill_switch": False,
                "daily_loss_halt": False,
                "failure_halt": False,
                "last_order": {
                    "venue": "okx",
                    "symbol": "BTCUSDT",
                    "side": "buy",
                    "qty": 0.05,
                    "status": "open",
                    "order_id": "ord-123",
                },
            },
            "live_runtime_truth": {
                "confidence": 0.61,
                "regime_label": "bull",
                "regime_gate": "ALLOW",
                "structure_bucket": "ALLOW|trend|q65",
                "allowed_layers": 2,
                "allowed_layers_reason": "entry_quality_B_two_layers",
                "runtime_closure_state": "runtime_visible_preview",
                "runtime_closure_summary": "目前 runtime truth 與 reconciliation 已可見，但 per-bot ledger 尚未綁定。",
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
            },
        },
        "account": {
            "captured_at": "2026-04-18T12:00:05Z",
            "degraded": False,
            "operator_message": "account snapshot fresh",
            "recovery_hint": "none",
            "requested_symbol": "BTCUSDT",
            "normalized_symbol": "BTC/USDT",
            "balance": {"total": 1000.0, "free": 820.0, "currency": "USDT"},
            "positions": [{
                "symbol": "BTC/USDT",
                "side": "long",
                "size": 0.1,
                "entryPrice": 67250.0,
                "markPrice": 68000.0,
                "unrealizedPnl": 125.0,
            }],
            "open_orders": [{"symbol": "BTCUSDT", "side": "buy", "qty": 0.01, "price": 69000.0}],
        },
        "execution_reconciliation": {
            "status": "attention",
            "summary": "shared symbol reconciliation available",
            "checked_at": "2026-04-18T12:00:06Z",
            "recovery_state": {
                "status": "operator_review",
                "operator_action": "確認 shared symbol 倉位與 run ownership 邊界。",
            },
            "lifecycle_audit": {
                "stage": "reconciliation_visible",
                "runtime_state": "open_order_detected",
                "trade_history_state": "awaiting_match",
                "restart_replay_required": False,
                "operator_action": "先確認 run 是否只鏡像 shared symbol 狀態。",
            },
        },
    }



def _blocked_high_conviction_status_payload():
    payload = deepcopy(_status_payload())
    live_truth = payload["execution"]["live_runtime_truth"]
    live_truth.update(
        {
            "confidence": 0.73,
            "regime_label": "block",
            "regime_gate": "BLOCK",
            "structure_bucket": "BLOCK|structure_quality_block|q00",
            "allowed_layers": 0,
            "allowed_layers_reason": "current_live_deployment_blocker",
            "deployment_blocker": "under_minimum_exact_live_structure_bucket",
            "execution_guardrail_reason": "under_minimum_exact_live_structure_bucket_blocks_trade",
            "runtime_closure_state": "current_live_deployment_blocked",
            "runtime_closure_summary": "current-live 精準分桶樣本不足；只允許影子觀察，不允許買入/加倉。",
        }
    )
    live_truth["sleeve_routing"] = {
        "current_regime": "block",
        "current_regime_gate": "BLOCK",
        "current_structure_bucket": "BLOCK|structure_quality_block|q00",
        "active_sleeves": [],
        "inactive_sleeves": [
            {"key": "trend", "label": "趨勢承接", "summary": "trend", "why": "current-live 精準樣本不足"},
            {"key": "pullback", "label": "回調承接", "summary": "pullback", "why": "current-live 精準樣本不足"},
            {"key": "rebound", "label": "深跌回補", "summary": "rebound", "why": "current-live 精準樣本不足"},
            {"key": "selective", "label": "高信念精選", "summary": "selective", "why": "OOS 通過但 runtime 仍阻塞"},
        ],
    }
    high_conviction_topk = {
        "deployment_readiness_status": "paper_shadow_only",
        "deployable_count": 0,
        "risk_qualified_count": 6,
        "runtime_blocked_candidate_count": 6,
        "operator_message": "離線驗證 / 風控已過 6 筆；可部署 0 筆。即時阻塞 精準樣本未達最小門檻。",
        "support_context": {
            "deployment_blocker": "under_minimum_exact_live_structure_bucket",
            "current_live_structure_bucket": "BLOCK|structure_quality_block|q00",
            "current_live_structure_bucket_rows": 2,
            "minimum_support_rows": 50,
            "current_live_structure_bucket_gap_to_minimum": 48,
            "support_progress_status": "stalled_under_minimum",
            "stalled_support_accumulation": True,
            "stagnant_run_count": 5,
            "support_delta_vs_previous": 0,
            "support_rows_needed": 48,
            "signal": "HOLD",
            "allowed_layers": 0,
        },
        "nearest_deployable_rows": [
            {
                "model_name": "logistic_regression",
                "threshold_name": "top_2pct",
                "deployment_candidate_tier": "runtime_blocked_oos_pass",
                "blocked_only_by_live_guardrails": True,
                "deployable": False,
                "signal": "HOLD",
                "allowed_layers": 0,
            }
        ],
    }
    payload["execution_surface_contract"]["high_conviction_topk"] = high_conviction_topk
    payload["execution"]["high_conviction_topk"] = high_conviction_topk
    return payload



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



def _seed_live_runner_shadow_decision(session, tmp_path, monkeypatch):
    live_root = tmp_path / "live_trading"
    live_root.mkdir()
    monkeypatch.setattr(control_plane_module, "LIVE_TRADING_ROOT", live_root)
    live_runner_module.ensure_audit_tables(session)
    run_id = "live-runner-shadow-qa"
    decision_payload = {
        "run_id": run_id,
        "strategy_name": "Trend QA Strategy",
        "strategy_hash": "live-runner-hash",
        "symbol": "BTCUSDT",
        "venue": "okx",
        "feature_timestamp": "2026-04-17T12:00:00Z",
        "price": 68000.0,
        "signal": "BUY",
        "action": "BUY_LAYER",
        "side": "buy",
        "qty": 0.001,
        "quote_amount": 68.0,
        "order_submitted": 0,
        "dry_run": 1,
        "model_confidence": 0.82,
        "entry_quality": 0.74,
        "allowed_layers": 1,
        "regime_gate": "ALLOW",
        "structure_bucket": "ALLOW|trend|q65",
        "reason": "shadow_candidate_for_24h_gate",
        "payload_json": json.dumps({"layer": {"index": 1}, "execution_reject": {"code": "paper_shadow_no_submit"}}, ensure_ascii=False),
        "created_at": "2026-04-17T12:05:00Z",
    }
    session.execute(
        text(
            """
            INSERT INTO live_runner_runs(
                id, strategy_name, strategy_hash, symbol, venue, mode, model_artifact_path,
                status, config_json, started_at, stopped_at, last_heartbeat_at
            ) VALUES (
                :id, 'Trend QA Strategy', 'live-runner-hash', 'BTCUSDT', 'okx', 'paper',
                'data/live_models/qa.pkl', 'running', :config_json,
                '2026-04-17T12:00:00Z', NULL, '2026-04-17T12:05:00Z'
            )
            """
        ),
        {
            "id": run_id,
            "config_json": json.dumps(
                {"trading": {"dry_run": True}, "execution": {"mode": "paper", "live_canary": {"enabled": False}}},
                ensure_ascii=False,
            ),
        },
    )
    session.execute(
        text(
            """
            INSERT INTO live_runner_decisions(
                run_id, strategy_name, strategy_hash, symbol, venue, feature_timestamp, price,
                signal, action, side, qty, quote_amount, order_id, client_order_id,
                order_submitted, dry_run, model_confidence, entry_quality, allowed_layers,
                regime_gate, structure_bucket, reason, payload_json, created_at
            ) VALUES (
                :run_id, :strategy_name, :strategy_hash, :symbol, :venue, :feature_timestamp, :price,
                :signal, :action, :side, :qty, :quote_amount, NULL, NULL,
                :order_submitted, :dry_run, :model_confidence, :entry_quality, :allowed_layers,
                :regime_gate, :structure_bucket, :reason, :payload_json, :created_at
            )
            """
        ),
        decision_payload,
    )
    session.commit()
    (live_root / f"{run_id}.jsonl").write_text(json.dumps(decision_payload, ensure_ascii=False) + "\n", encoding="utf-8")
    return run_id



def test_execution_run_lifecycle_start_pause_stop_and_detail(monkeypatch, tmp_path):
    async def _fake_status():
        return _status_payload()

    _seed_execution_strategy_catalog(tmp_path, monkeypatch)
    monkeypatch.setattr(strategy_bundle_module, "STRATEGY_BUNDLE_ROOT", tmp_path / "strategy_bundles")
    monkeypatch.setattr(control_plane_module, "PAPER_SHADOW_OUTCOME_ARTIFACT_PATH", tmp_path / "paper_shadow_outcomes.json")
    session = init_db(f"sqlite:///{tmp_path / 'execution_runs.db'}")
    monkeypatch.setattr(api_module, "get_config", lambda: {"trading": {"max_position_ratio": 0.10}})
    monkeypatch.setattr(api_module, "get_db", lambda: session)
    monkeypatch.setattr(api_module, "api_status", _fake_status)

    control_plane_module.ensure_execution_control_plane_schema(session)
    before_get_counts = tuple(
        session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
        for table in ("execution_profiles", "execution_runs", "execution_run_events")
    )
    asyncio.run(api_module.api_execution_overview())
    after_get_counts = tuple(
        session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
        for table in ("execution_profiles", "execution_runs", "execution_run_events")
    )
    assert after_get_counts == before_get_counts

    empty_outcomes = asyncio.run(api_module.api_execution_worker_outcomes())
    empty_proof = empty_outcomes["artifact"]["rehearsal_proof"]
    assert empty_outcomes["artifact"]["status"] == "no_worker_events"
    assert empty_proof["status"] == "needs_paper_shadow_run"
    assert empty_proof["run_counts"]["total"] == 0
    assert empty_proof["order_submission_enabled"] is False
    assert empty_proof["risk_on_order_enabled"] is False

    start_payload = asyncio.run(api_module.api_execution_start_run("trend", request=_local_request()))
    run_id = start_payload["run"]["run_id"]
    assert start_payload["action"] == "start"
    assert start_payload["action_result"] == "started"
    assert start_payload["run"]["state"] == "running"
    assert start_payload["run"]["runtime_binding_status"] == "control_plane_only"
    assert start_payload["run"]["runtime_binding_contract"]["status"] == "symbol_scope_runtime_mirror"
    assert start_payload["run"]["runtime_binding_contract"]["operator_action"] == "確認 shared symbol 倉位與 run ownership 邊界。"
    assert start_payload["run"]["runtime_binding_contract"]["ownership_boundary"]["pnl_attribution"] == "symbol_scoped_preview_only"
    assert start_payload["run"]["runtime_binding_snapshot"]["shared_symbol_ledger_preview"]["budget_alignment_status"] == "warning_over_planned_preview"
    assert start_payload["run"]["runtime_binding_snapshot"]["shared_symbol_ledger_preview"]["gross_position_notional"] == 6800.0
    assert start_payload["run"]["runtime_binding_snapshot"]["shared_symbol_ledger_preview"]["open_order_notional"] == 690.0
    assert start_payload["run"]["runtime_binding_snapshot"]["shared_symbol_ledger_preview"]["unrealized_pnl"] == 125.0
    assert start_payload["run"]["strategy_binding"]["strategy_name"] == "Trend QA Strategy"
    assert start_payload["run"]["strategy_binding"]["strategy_source"] == "strategy_lab_saved"
    assert start_payload["run"]["strategy_binding"]["strategy_hash"]
    assert start_payload["run"]["strategy_bundle_hash"]
    assert start_payload["run"]["strategy_bundle_status"] == "persisted"
    assert start_payload["run"]["strategy_binding"]["strategy_bundle"]["bundle_hash"] == start_payload["run"]["strategy_bundle_hash"]
    assert start_payload["run"]["strategy_binding"]["strategy_bundle"]["live_buy_add_status"] == "fail_closed_live_buy_add"
    assert start_payload["run"]["worker_status"] == "backend_worker_pending"
    assert start_payload["run"]["worker_control"]["order_submission_enabled"] is False
    assert start_payload["run"]["worker_control"]["backend_worker_bound"] is False
    assert (tmp_path / "strategy_bundles").exists()
    assert start_payload["run"]["runtime_binding_snapshot"]["reconciliation"]["status"] == "attention"
    assert start_payload["run"]["runtime_binding_snapshot"]["guardrails"]["last_order"]["order_id"] == "ord-123"
    assert start_payload["snapshot"]["summary"]["running_runs"] == 1
    assert start_payload["snapshot"]["summary"]["configured_running_rows"] == 1
    assert start_payload["snapshot"]["summary"]["manual_poll_running_rows"] == 1
    assert start_payload["snapshot"]["summary"]["healthy_continuous_workers"] == 0

    duplicate_start = asyncio.run(api_module.api_execution_start_run("trend", request=_local_request()))
    assert duplicate_start["action_result"] == "configured_running_without_healthy_worker"
    assert duplicate_start["run"]["runtime_liveness"]["healthy"] is False

    pre_poll_outcomes = asyncio.run(api_module.api_execution_worker_outcomes())
    pre_poll_proof = pre_poll_outcomes["artifact"]["rehearsal_proof"]
    assert pre_poll_outcomes["artifact"]["status"] == "no_worker_events"
    assert pre_poll_proof["status"] == "needs_worker_poll"
    assert pre_poll_proof["can_poll_workers"] is True
    assert pre_poll_proof["run_counts"]["running"] == 1
    assert pre_poll_proof["chain"][1]["key"] == "worker_poll"
    assert pre_poll_proof["chain"][1]["status"] == "ready"

    poll_payload = asyncio.run(api_module.api_execution_worker_poll(request=_local_request()))
    polled_run = poll_payload["runs"][0]
    assert poll_payload["action"] == "worker_poll"
    assert poll_payload["summary"]["processed_runs"] == 1
    assert poll_payload["summary"]["poll_events_recorded"] == 1
    assert poll_payload["summary"]["order_submission_enabled"] is False
    assert polled_run["run_id"] == run_id
    assert polled_run["worker_status"] == "paper_shadow_worker_polled"
    assert polled_run["worker_control"]["backend_worker_bound"] is False
    assert polled_run["worker_control"]["legacy_backend_worker_bound"] is False
    assert polled_run["worker_control"]["poll_handler_available"] is True
    assert polled_run["worker_control"]["continuous_worker"] is False
    assert polled_run["worker_control"]["runtime_liveness"]["status"] == "not_continuously_running"
    assert polled_run["worker_control"]["runtime_liveness"]["healthy"] is False
    assert polled_run["worker_control"]["bundle_hash_match"] is True
    assert polled_run["worker_control"]["latest_order_proposal"]["live_order_submitted"] is False
    assert polled_run["latest_event"]["event_type"] == "paper_shadow_worker_poll"
    assert polled_run["latest_event"]["payload"]["order_submission_enabled"] is False
    assert poll_payload["outcome_reconciliation"]["artifact"]["status"] == "recording_pending_outcomes"
    assert poll_payload["outcome_reconciliation"]["artifact"]["artifact_schema_version"] == 2
    assert poll_payload["outcome_reconciliation"]["artifact"]["pending_outcomes"] == 1
    assert poll_payload["outcome_reconciliation"]["artifact"]["rehearsal_status"] == "pending_observation_window"
    assert poll_payload["outcome_reconciliation"]["artifact"]["quick_read"]["pending_outcomes"] == 1
    assert (
        poll_payload["outcome_reconciliation"]["artifact"]["quick_read"]["poll_blocked_by_pending_outcome"]
        is True
    )
    assert poll_payload["outcome_reconciliation"]["artifact"]["summary"]["pending_outcomes"] == 1
    assert poll_payload["outcome_reconciliation"]["artifact"]["rehearsal_proof"]["status"] == "pending_observation_window"
    assert poll_payload["outcome_reconciliation"]["artifact"]["rehearsal_proof"]["chain"][2]["status"] == "complete"
    assert poll_payload["outcome_reconciliation"]["artifact"]["rehearsal_proof"]["live_order_submitted"] is False
    assert (tmp_path / "paper_shadow_outcomes.json").exists()

    worker_event = session.execute(
        text("SELECT id, payload_json FROM execution_run_events WHERE event_type = 'paper_shadow_worker_poll' LIMIT 1")
    ).mappings().first()
    event_payload = json.loads(worker_event["payload_json"])
    event_payload["order_proposal"]["generated_at"] = "2026-04-17T12:00:00Z"
    event_payload["order_proposal"]["symbol"] = "BTCUSDT"
    session.execute(
        text("UPDATE execution_run_events SET payload_json = :payload_json, created_at = :created_at WHERE id = :event_id"),
        {
            "payload_json": json.dumps(event_payload, ensure_ascii=False),
            "created_at": "2026-04-17T12:00:01Z",
            "event_id": worker_event["id"],
        },
    )
    session.execute(
        text(
            """
            INSERT INTO labels (
                timestamp, symbol, horizon_minutes,
                simulated_pyramid_win, simulated_pyramid_pnl, simulated_pyramid_quality
            ) VALUES (
                :timestamp, :symbol, 1440,
                1, 0.0125, 0.42
            )
            """
        ),
        {"timestamp": "2026-04-17T12:00:00Z", "symbol": "BTCUSDT"},
    )
    session.commit()
    live_runner_run_id = _seed_live_runner_shadow_decision(session, tmp_path, monkeypatch)

    outcome_payload = asyncio.run(api_module.api_execution_worker_reconcile(request=_local_request()))
    outcome_artifact = outcome_payload["artifact"]
    assert outcome_payload["action"] == "worker_reconcile"
    assert outcome_artifact["status"] == "recording_with_resolved_outcomes"
    assert outcome_artifact["rehearsal_status"] == "resolved_evidence_ready"
    assert outcome_artifact["quick_read"]["resolved_outcomes"] == 1
    assert outcome_artifact["quick_read"]["rehearsal_status"] == "resolved_evidence_ready"
    assert outcome_artifact["summary"]["resolved_outcomes"] == 1
    assert outcome_artifact["rehearsal_proof"]["status"] == "resolved_evidence_ready"
    assert outcome_artifact["rehearsal_proof"]["chain"][3]["status"] == "complete"
    assert outcome_artifact["entries"][0]["outcome_24h"]["status"] == "resolved_from_1440m_label"
    assert outcome_artifact["entries"][0]["outcome_24h"]["pyramid_win"] is True
    assert outcome_artifact["entries"][0]["order_submission_enabled"] is False
    assert outcome_artifact["source"] == "execution_run_events.paper_shadow_worker_poll+live_runner_decisions"
    assert outcome_artifact["quick_read"]["live_runner_status"] == "runner_24h_resolved_evidence_ready"
    assert outcome_artifact["quick_read"]["live_runner_resolved_outcomes"] == 1
    assert outcome_artifact["quick_read"]["live_runner_jsonl_backed"] is True
    assert outcome_artifact["summary"]["live_runner_total_runs"] == 1
    assert outcome_artifact["summary"]["live_runner_total_decisions"] == 1
    assert outcome_artifact["summary"]["live_runner_candidate_decisions"] == 1
    assert outcome_artifact["live_runner_shadow_gate"]["status"] == "runner_24h_resolved_evidence_ready"
    assert outcome_artifact["live_runner"]["latest_run"]["run_id"] == live_runner_run_id
    assert outcome_artifact["live_runner"]["latest_decision"]["action"] == "BUY_LAYER"

    def _duplicate_live_runner_scan_forbidden(*_args, **_kwargs):
        raise AssertionError("execution overview must reuse reconciliation live-runner evidence")

    monkeypatch.setattr(api_module, "build_live_runner_overview", _duplicate_live_runner_scan_forbidden)
    overview_payload = asyncio.run(api_module.api_execution_overview())
    trend_card = next(card for card in overview_payload["profile_cards"] if card["key"] == "trend")
    assert trend_card["current_run_state"] == "running"
    assert trend_card["control_contract"]["start_status"] == "already_running"
    assert trend_card["current_run"]["runtime_binding_contract"]["status"] == "symbol_scope_runtime_mirror"
    overview_outcome = overview_payload["paper_shadow_outcome_reconciliation"]
    overview_live_runner = overview_payload["live_runner"]
    assert overview_live_runner["status"] == "runner_24h_resolved_evidence_ready"
    assert overview_live_runner["summary"]["total_runs"] == 1
    assert overview_live_runner["summary"]["total_decisions"] == 1
    assert overview_live_runner["summary"]["jsonl_backed"] is True
    assert overview_live_runner["latest_run"]["run_id"] == live_runner_run_id
    assert overview_live_runner["latest_decision"]["action"] == "BUY_LAYER"
    assert overview_live_runner["shadow_evidence_gate"]["resolved_outcomes"] == 1
    assert overview_live_runner["shadow_evidence_gate"]["order_submission_enabled"] is False
    readiness = overview_payload["execution_readiness"]
    readiness_gates = {gate["key"]: gate for gate in readiness["gates"]}
    assert readiness_gates["live_runner_24h_shadow_gate"]["status"] == "passed"
    assert readiness_gates["live_runner_24h_shadow_gate"]["resolved_outcomes"] == 1
    assert readiness_gates["live_runner_24h_shadow_gate"]["jsonl_backed"] is True
    assert readiness_gates["live_runner_24h_shadow_gate"]["order_submission_enabled"] is False
    milestone = readiness["milestone_progression"]
    roadmap_milestones = {item["key"]: item for item in milestone["milestones"]}
    assert roadmap_milestones["M4_5_live_runner_24h_shadow_evidence"]["status"] == "passed"
    assert milestone["live_runner_24h_shadow_gate"]["passed"] is True
    assert overview_outcome["source"] == "execution_run_events.paper_shadow_worker_poll+live_runner_decisions"
    assert overview_outcome["status"] == "recording_with_resolved_outcomes"
    assert overview_outcome["quick_read"]["resolved_outcomes"] == 1
    assert overview_outcome["quick_read"]["order_submission_enabled"] is False
    assert overview_outcome["summary"]["resolved_outcomes"] == 1
    assert overview_outcome["summary"]["pending_outcomes"] == 0
    assert overview_outcome["summary"]["live_order_submitted"] is False
    assert overview_outcome["rehearsal_proof"]["status"] == "resolved_evidence_ready"
    assert overview_outcome["rehearsal_proof"]["order_submission_enabled"] is False
    assert overview_outcome["rehearsal_proof"]["risk_on_order_enabled"] is False
    assert overview_outcome["rehearsal_proof"]["live_order_submitted"] is False
    assert "entries" not in overview_outcome

    pause_payload = asyncio.run(api_module.api_execution_pause_run(run_id, request=_local_request()))
    assert pause_payload["action"] == "pause"
    assert pause_payload["action_result"] == "paused"
    assert pause_payload["run"]["state"] == "paused"
    assert pause_payload["run"]["action_contract"]["can_resume"] is True
    assert pause_payload["run"]["worker_status"] == "pause_requested_no_backend_worker"
    assert pause_payload["run"]["worker_control"]["order_submission_enabled"] is False

    paused_poll_payload = asyncio.run(api_module.api_execution_worker_poll(request=_local_request()))
    assert paused_poll_payload["status"] == "no_running_runs"
    assert paused_poll_payload["summary"]["processed_runs"] == 0

    resume_payload = asyncio.run(api_module.api_execution_start_run("trend", request=_local_request()))
    assert resume_payload["action_result"] == "resumed"
    assert resume_payload["run"]["state"] == "running"
    assert resume_payload["run"]["worker_status"] == "resume_requested_no_backend_worker"
    assert resume_payload["run"]["worker_control"]["order_submission_enabled"] is False

    stop_payload = asyncio.run(api_module.api_execution_stop_run(run_id, request=_local_request()))
    assert stop_payload["action"] == "stop"
    assert stop_payload["action_result"] == "stopped"
    assert stop_payload["run"]["state"] == "stopped"
    assert stop_payload["run"]["stop_reason"] == "operator_stop"
    assert stop_payload["run"]["worker_status"] == "stop_requested_no_backend_worker"
    assert stop_payload["run"]["worker_control"]["order_submission_enabled"] is False
    assert stop_payload["run"]["worker_control"]["cancel_open_orders_status"] == "not_bound_to_exchange_adapter"

    detail_payload = asyncio.run(api_module.api_execution_run_detail(run_id))
    event_types = [event["event_type"] for event in detail_payload["recent_events"]]
    assert detail_payload["state"] == "stopped"
    assert detail_payload["runtime_binding_contract"]["status"] == "symbol_scope_runtime_mirror"
    assert detail_payload["runtime_binding_contract"]["ownership_boundary"]["ledger_scope"] == "shared_symbol_preview_only"
    assert detail_payload["runtime_binding_contract"]["ownership_boundary"]["pnl_attribution"] == "symbol_scoped_preview_only"
    assert detail_payload["strategy_binding"]["strategy_name"] == "Trend QA Strategy"
    assert detail_payload["strategy_binding"]["strategy_hash"] == start_payload["run"]["strategy_binding"]["strategy_hash"]
    assert detail_payload["strategy_bundle_hash"] == start_payload["run"]["strategy_bundle_hash"]
    assert detail_payload["worker_status"] == "stop_requested_no_backend_worker"
    assert detail_payload["worker_control"]["order_submission_enabled"] is False
    assert detail_payload["runtime_binding_snapshot"]["account_snapshot"]["position_count"] == 1
    assert detail_payload["runtime_binding_snapshot"]["capital_preview"]["allocation_scope"] == "run_budget_vs_shared_balance_preview"
    assert detail_payload["runtime_binding_snapshot"]["capital_preview"]["balance_total"] == 1000.0
    assert detail_payload["runtime_binding_snapshot"]["shared_symbol_preview"]["positions_total_count"] == 1
    assert detail_payload["runtime_binding_snapshot"]["shared_symbol_preview"]["open_orders_total_count"] == 1
    assert detail_payload["runtime_binding_snapshot"]["shared_symbol_preview"]["positions"][0]["symbol"] == "BTC/USDT"
    assert detail_payload["runtime_binding_snapshot"]["shared_symbol_preview"]["open_orders"][0]["symbol"] == "BTCUSDT"
    assert detail_payload["runtime_binding_snapshot"]["shared_symbol_ledger_preview"]["total_known_commitment"] == 7490.0
    assert detail_payload["runtime_binding_snapshot"]["shared_symbol_ledger_preview"]["budget_alignment_status"] == "warning_over_planned_preview"
    assert detail_payload["runtime_binding_snapshot"]["shared_symbol_ledger_preview"]["position_priced_count"] == 1
    assert detail_payload["runtime_binding_snapshot"]["shared_symbol_ledger_preview"]["open_order_priced_count"] == 1
    assert detail_payload["runtime_binding_snapshot"]["shared_symbol_ledger_preview"]["unrealized_pnl"] == 125.0
    assert "started" in event_types
    assert "paper_shadow_worker_poll" in event_types
    assert "paused" in event_types
    assert "resumed" in event_types
    assert "stopped" in event_types

    runs_payload = asyncio.run(api_module.api_execution_runs())
    assert runs_payload["summary"]["running_runs"] == 0
    assert runs_payload["summary"]["paused_runs"] == 0
    assert runs_payload["summary"]["stopped_runs"] == 1
    assert runs_payload["runs"][0]["run_id"] == run_id



def test_selective_high_conviction_shadow_run_can_start_under_current_live_blocker(monkeypatch, tmp_path):
    async def _fake_status():
        return _blocked_high_conviction_status_payload()

    session = init_db(f"sqlite:///{tmp_path / 'execution_runs_shadow.db'}")
    control_plane_module.ensure_execution_control_plane_schema(session)
    monkeypatch.setattr(strategy_bundle_module, "STRATEGY_BUNDLE_ROOT", tmp_path / "strategy_bundles")
    monkeypatch.setattr(control_plane_module, "PAPER_SHADOW_OUTCOME_ARTIFACT_PATH", tmp_path / "paper_shadow_outcomes.json")
    monkeypatch.setattr(api_module, "get_config", lambda: {"trading": {"max_position_ratio": 0.10}})
    monkeypatch.setattr(api_module, "get_db", lambda: session)
    monkeypatch.setattr(api_module, "api_status", _fake_status)

    overview_payload = asyncio.run(api_module.api_execution_overview())
    selective_card = next(card for card in overview_payload["profile_cards"] if card["key"] == "selective")
    assert selective_card["lifecycle_status"] == "shadow_monitoring"
    assert selective_card["control_contract"]["start_status"] == "shadow_start_available"
    assert selective_card["control_contract"]["shadow_only"] is True
    assert selective_card["control_contract"]["risk_on_order_enabled"] is False
    assert selective_card["control_contract"]["high_conviction_topk"]["risk_qualified_count"] == 6
    assert selective_card["control_contract"]["high_conviction_topk"]["support_context"]["support_rows_needed"] == 48
    assert "不送單" in selective_card["control_contract"]["start_reason"]
    assert "影子觀察" in selective_card["next_operator_action"]

    start_payload = asyncio.run(api_module.api_execution_start_run("selective", request=_local_request()))
    run = start_payload["run"]
    assert start_payload["action_result"] == "shadow_started"
    assert start_payload["operator_message"] == "高信念精選影子觀察已啟動；不送單、不加倉。"
    assert run["profile_id"] == "selective"
    assert run["mode"] == "paper_shadow"
    assert run["state"] == "running"
    assert run["runtime_binding_status"] == "paper_shadow_runtime_blocked"
    assert run["action_contract"]["shadow_only"] is True
    assert run["action_contract"]["risk_on_order_enabled"] is False
    assert run["runtime_binding_contract"]["shadow_only"] is True
    assert run["runtime_binding_contract"]["high_conviction_topk"]["support_context"]["current_live_structure_bucket_rows"] == 2
    assert run["runtime_binding_snapshot"]["mode"] == "paper_shadow"
    assert run["strategy_binding"]["status"] == "synthetic_paper_shadow_bound"
    assert run["strategy_binding"]["strategy_source"] == "high_conviction_topk_shadow"
    assert run["strategy_bundle_status"] == "persisted"
    assert run["strategy_bundle_hash"]
    assert run["strategy_binding"]["strategy_bundle"]["freeze_status"] == "paper_shadow_topk_bundle_frozen"
    assert run["strategy_binding"]["strategy_bundle"]["live_buy_add_status"] == "fail_closed_live_buy_add"
    assert "不送單" in run["last_event_message"]
    assert run["last_event_type"] == "shadow_started"
    assert run["latest_event"]["event_type"] == "shadow_started"
    assert run["latest_event"]["payload"]["risk_on_order_enabled"] is False
    assert run["latest_event"]["payload"]["strategy_bundle_status"] == "persisted"

    pre_poll_outcomes = asyncio.run(api_module.api_execution_worker_outcomes())
    assert pre_poll_outcomes["artifact"]["rehearsal_proof"]["status"] == "needs_worker_poll"
    assert pre_poll_outcomes["artifact"]["rehearsal_proof"]["can_poll_workers"] is True

    poll_payload = asyncio.run(api_module.api_execution_worker_poll(request=_local_request()))
    assert poll_payload["summary"]["processed_runs"] == 1
    assert poll_payload["summary"]["poll_events_recorded"] == 1
    assert poll_payload["summary"]["parity_blocked_runs"] == 0
    assert poll_payload["runs"][0]["worker_status"] == "paper_shadow_worker_polled"
    assert poll_payload["runs"][0]["worker_control"]["bundle_hash_match"] is True
    assert poll_payload["runs"][0]["worker_control"]["latest_order_proposal"]["live_order_submitted"] is False
    assert poll_payload["outcome_reconciliation"]["artifact"]["status"] == "recording_pending_outcomes"
    assert poll_payload["outcome_reconciliation"]["artifact"]["rehearsal_proof"]["status"] == "pending_observation_window"
    assert poll_payload["outcome_reconciliation"]["artifact"]["rehearsal_proof"]["can_poll_workers"] is False
    assert poll_payload["outcome_reconciliation"]["artifact"]["rehearsal_proof"]["poll_blocked_by_pending_outcome"] is True
    assert poll_payload["outcome_reconciliation"]["artifact"]["rehearsal_proof"]["next_reconcile_at"]
    assert poll_payload["outcome_reconciliation"]["artifact"]["rehearsal_proof"]["pending_hours_remaining_min"] > 0
    assert poll_payload["outcome_reconciliation"]["artifact"]["summary"]["pending_outcomes"] == 1

    duplicate_poll_payload = asyncio.run(api_module.api_execution_worker_poll(request=_local_request()))
    assert duplicate_poll_payload["status"] == "pending_outcome_blocked"
    assert duplicate_poll_payload["summary"]["processed_runs"] == 0
    assert duplicate_poll_payload["summary"]["poll_events_recorded"] == 0
    assert duplicate_poll_payload["summary"]["pending_outcome_blocked_runs"] == 1
    assert duplicate_poll_payload["pending_outcome_gates"][0]["status"] == "pending_observation_window"
    assert duplicate_poll_payload["outcome_reconciliation"]["artifact"]["summary"]["pending_outcomes"] == 1
    worker_poll_event_count = session.execute(
        text("SELECT COUNT(*) FROM execution_run_events WHERE event_type = 'paper_shadow_worker_poll'")
    ).scalar_one()
    assert worker_poll_event_count == 1

    runs_payload = asyncio.run(api_module.api_execution_runs())
    selective_run = next(record for record in runs_payload["runs"] if record["profile_id"] == "selective")
    assert selective_run["mode"] == "paper_shadow"
    assert selective_run["runtime_binding_status"] == "paper_shadow_runtime_blocked"
    assert selective_run["worker_status"] == "paper_shadow_worker_polled"



def test_execution_run_start_rejects_inactive_profile(monkeypatch, tmp_path):
    async def _fake_status():
        return _status_payload()

    session = init_db(f"sqlite:///{tmp_path / 'execution_runs_blocked.db'}")
    monkeypatch.setattr(api_module, "get_config", lambda: {"trading": {"max_position_ratio": 0.10}})
    monkeypatch.setattr(api_module, "get_db", lambda: session)
    monkeypatch.setattr(api_module, "api_status", _fake_status)

    try:
        asyncio.run(api_module.api_execution_start_run("rebound", request=_local_request()))
    except Exception as exc:
        detail = getattr(exc, "detail", {})
        assert detail["code"] == "profile_not_startable"
        assert detail["context"]["start_status"] == "inactive_preview"
    else:
        raise AssertionError("inactive profile should not start")


def test_selected_strategy_can_start_exact_paper_shadow_run_while_live_is_blocked(monkeypatch, tmp_path):
    async def _fake_status():
        return _blocked_high_conviction_status_payload()

    _seed_execution_strategy_catalog(tmp_path, monkeypatch)
    monkeypatch.setattr(strategy_bundle_module, "STRATEGY_BUNDLE_ROOT", tmp_path / "strategy_bundles_exact")
    monkeypatch.setattr(control_plane_module, "PAPER_SHADOW_OUTCOME_ARTIFACT_PATH", tmp_path / "paper_shadow_exact.json")
    session = init_db(f"sqlite:///{tmp_path / 'execution_runs_exact_shadow.db'}")
    monkeypatch.setattr(api_module, "get_config", lambda: {"trading": {"max_position_ratio": 0.10}})
    monkeypatch.setattr(api_module, "get_db", lambda: session)
    monkeypatch.setattr(api_module, "api_status", _fake_status)
    exact_cycle_calls = []
    monkeypatch.setattr(
        live_runner_module,
        "ensure_model_artifact",
        lambda **kwargs: SimpleNamespace(metadata={"source": "strategy_lab_backtest", "model_sha256": "model-sha"}),
    )

    def _fake_exact_cycle(**kwargs):
        exact_cycle_calls.append(kwargs)
        return {
            "status": "exact_strategy_cycle_completed",
            "execution_run_id": kwargs["execution_run_id"],
            "strategy_name": kwargs["strategy_name"],
            "model_sha256": "model-sha",
            "decision": {"signal": "HOLD", "action": "HOLD", "order_submitted": 0},
            "order_submission_enabled": False,
            "risk_on_order_enabled": False,
            "live_order_submitted": False,
        }

    monkeypatch.setattr(live_runner_module, "run_exact_strategy_paper_shadow_cycle", _fake_exact_cycle)

    payload = asyncio.run(
        api_module.api_start_strategy_paper_shadow("Trend QA Strategy", request=_local_request())
    )

    assert payload["action"] == "strategy_paper_shadow_start"
    assert payload["strategy_name"] == "Trend QA Strategy"
    assert payload["profile_id"] == "trend"
    assert payload["mode"] == "paper_shadow"
    assert payload["order_submission_enabled"] is False
    assert payload["risk_on_order_enabled"] is False
    assert payload["live_order_submitted"] is False
    assert payload["run"]["strategy_binding"]["strategy_name"] == "Trend QA Strategy"
    assert payload["run"]["strategy_binding"]["model_name"] == "random_forest"
    assert payload["run"]["runtime_binding_status"] == "paper_shadow_runtime_blocked"
    assert payload["worker"]["summary"]["processed_runs"] == 1
    assert payload["worker"]["summary"]["order_submission_enabled"] is False
    assert payload["worker"]["runs"][0]["worker_control"]["bundle_hash_match"] is True
    proposal = payload["worker"]["runs"][0]["worker_control"]["latest_order_proposal"]
    assert proposal["proposal_source"] == "exact_strategy_runtime"
    assert proposal["strategy_name"] == "Trend QA Strategy"
    assert proposal["model_sha256"] == "model-sha"
    promotion = payload["worker"]["runs"][0]["promotion_status"]
    assert promotion["state"] == "paper_shadow_evidence_recorded"
    assert promotion["journey_contract_status"] == "partial_not_promotable"
    assert promotion["journey_complete"] is False
    assert promotion["progress_current"] == 3
    assert promotion["progress_target"] is None
    assert promotion["declared_stage_count"] == 5
    assert promotion["progress_is_release_metric"] is False
    assert promotion["stages"][1]["key"] == "exact_runtime"
    assert promotion["stages"][1]["status"] == "complete"
    assert promotion["stages"][2]["status"] == "evidence_recorded"
    assert promotion["stages"][3]["status"] == "reconciliation_required"
    assert promotion["stages"][4]["status"] == "not_implemented"
    assert promotion["next_action"]["route"] == "/execution"
    assert payload["strategy_runtime"]["status"] == "exact_strategy_cycle_completed"
    assert payload["strategy_runtime"]["model_sha256"] == "model-sha"
    assert payload["strategy_runtime"]["decision"]["order_submitted"] == 0
    assert exact_cycle_calls[0]["strategy_name"] == "Trend QA Strategy"
    assert exact_cycle_calls[0]["execution_run_id"] == payload["run"]["run_id"]
