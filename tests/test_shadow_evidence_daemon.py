import asyncio
import json
from datetime import datetime, timezone

from database.models import init_db
from execution import live_runner as live_runner_module
from execution.shadow_evidence_daemon import (
    acknowledge_shadow_evidence_operator_review,
    build_shadow_evidence_daemon_artifact,
    shadow_evidence_runtime_config,
)
from server.routes import api as api_module
from sqlalchemy import text


def _seed_live_runner_shadow_decision(session):
    live_runner_module.ensure_audit_tables(session)
    session.execute(
        text(
            """
            INSERT INTO live_runner_runs(
                id, strategy_name, strategy_hash, symbol, venue, mode, model_artifact_path,
                status, config_json, started_at, stopped_at, last_heartbeat_at
            ) VALUES (
                'shadow-evidence-daemon', 'Evidence QA Strategy', 'evidence-hash', 'BTCUSDT', 'okx', 'paper',
                'data/live_models/evidence.pkl', 'running', :config_json,
                '2026-07-10T00:00:00Z', NULL, '2026-07-10T00:05:00Z'
            )
            """
        ),
        {
            "config_json": json.dumps(
                {
                    "trading": {"dry_run": True},
                    "execution": {"mode": "paper", "enable_live_trading": False, "live_canary": {"enabled": False}},
                    "live_runner": {"shadow_evidence_mode": True},
                },
                ensure_ascii=False,
            )
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
                'shadow-evidence-daemon', 'Evidence QA Strategy', 'evidence-hash', 'BTCUSDT', 'okx',
                '2026-07-10T00:00:00Z', 68000.0,
                'SHADOW_BUY', 'SHADOW_BUY', 'buy', 0.00001, 0.68, NULL, NULL,
                0, 1, 0.82, 0.74, 1,
                'ALLOW', 'ALLOW|trend|q65', 'shadow_candidate_for_24h_gate', :payload_json, '2026-07-10T00:05:00Z'
            )
            """
        ),
        {
            "payload_json": json.dumps(
                {
                    "shadow_candidate_contract": {
                        "status": "recording_no_submit_shadow_candidate",
                        "order_submission_enabled": False,
                        "risk_on_order_enabled": False,
                        "live_order_submitted": False,
                    }
                },
                ensure_ascii=False,
            )
        },
    )
    session.commit()


def test_shadow_evidence_runtime_config_forces_fail_closed_paper_mode():
    cfg = shadow_evidence_runtime_config(
        {
            "trading": {"dry_run": False},
            "execution": {"mode": "live", "enable_live_trading": True, "live_canary": {"enabled": True}},
        },
        interval_seconds=30,
    )
    assert cfg["trading"]["dry_run"] is True
    assert cfg["execution"]["mode"] == "paper"
    assert cfg["execution"]["enable_live_trading"] is False
    assert cfg["execution"]["live_canary"]["enabled"] is False
    assert cfg["live_runner"]["shadow_candidate_enabled"] is True
    assert cfg["live_runner"]["shadow_evidence_mode"] is True
    assert cfg["live_runner"]["interval_seconds"] == 30


def test_shadow_evidence_daemon_artifact_is_dashboard_compact_and_no_submit(tmp_path):
    session = init_db(f"sqlite:///{tmp_path / 'shadow_evidence.db'}")
    _seed_live_runner_shadow_decision(session)
    live_runner_overview = api_module.build_live_runner_overview(session)
    outcome = api_module.build_paper_shadow_outcome_reconciliation(session, persist=False)

    artifact = build_shadow_evidence_daemon_artifact(
        previous_artifact={},
        live_runner_overview=live_runner_overview,
        outcome_reconciliation=outcome,
        latest_cycle_decision={"action": "SHADOW_BUY", "reason": "shadow_candidate_for_24h_gate"},
        now=datetime(2026, 7, 10, 0, 10, tzinfo=timezone.utc),
        interval_seconds=900,
        review_interval_hours=6,
        artifact_path=tmp_path / "shadow_evidence_daemon.json",
        log_path=tmp_path / "shadow_evidence_daemon.jsonl",
    )

    assert artifact["summary"]["cycles_completed"] == 1
    assert artifact["summary"]["total_decisions"] == 1
    assert artifact["summary"]["candidate_decisions"] == 1
    assert artifact["summary"]["order_submission_enabled"] is False
    assert artifact["summary"]["risk_on_order_enabled"] is False
    assert artifact["summary"]["live_order_submitted"] is False
    assert artifact["guardrail"]["order_submission_enabled"] is False
    assert artifact["latest_decision"]["action"] == "SHADOW_BUY"
    assert artifact["operator_review"]["next_operator_review_at"]


def test_api_execution_shadow_evidence_exposes_contract(monkeypatch, tmp_path):
    session = init_db(f"sqlite:///{tmp_path / 'shadow_evidence_api.db'}")
    _seed_live_runner_shadow_decision(session)
    monkeypatch.setattr(api_module, "get_db", lambda: session)
    monkeypatch.setattr(
        api_module,
        "load_shadow_evidence_daemon_artifact",
        lambda: {
            "available": True,
            "created_at": "2026-07-10T00:00:00Z",
            "updated_at": "2026-07-10T00:05:00Z",
            "summary": {"cycles_completed": 1},
        },
    )

    payload = asyncio.run(api_module.api_execution_shadow_evidence())

    assert payload["summary"]["total_decisions"] == 1
    assert payload["summary"]["candidate_decisions"] == 1
    assert payload["guardrail"]["order_submission_enabled"] is False
    assert payload["guardrail"]["risk_on_order_enabled"] is False
    assert payload["guardrail"]["live_order_submitted"] is False
    assert payload["live_runner"]["summary"]["total_decisions"] == 1
    assert payload["paper_shadow_outcome_reconciliation"]["order_submission_enabled"] is False


def test_acknowledge_shadow_evidence_review_resets_due_without_enabling_live(tmp_path):
    artifact_path = tmp_path / "shadow_evidence_daemon.json"
    log_path = tmp_path / "shadow_evidence_daemon.jsonl"
    artifact_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "created_at": "2026-07-10T00:00:00Z",
                "updated_at": "2026-07-10T06:01:00Z",
                "status": "operator_confirmation_due",
                "summary": {"cycles_completed": 4, "live_order_submitted": False},
                "operator_review": {"confirmation_due": True},
                "guardrail": {
                    "order_submission_enabled": False,
                    "risk_on_order_enabled": False,
                    "live_order_submitted": False,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    ack = acknowledge_shadow_evidence_operator_review(
        artifact_path=artifact_path,
        log_path=log_path,
        now=datetime(2026, 7, 10, 6, 5, tzinfo=timezone.utc),
        review_interval_hours=6,
    )

    assert ack["status"] == "operator_review_acknowledged"
    assert ack["operator_review"]["confirmation_due"] is False
    assert ack["operator_review"]["last_operator_review_at"] == "2026-07-10T06:05:00Z"
    assert ack["summary"]["last_operator_review_at"] == "2026-07-10T06:05:00Z"
    assert ack["guardrail"]["order_submission_enabled"] is False
    assert ack["guardrail"]["risk_on_order_enabled"] is False
    assert ack["guardrail"]["live_order_submitted"] is False
    assert log_path.exists()


def test_api_execution_shadow_evidence_ack_exposes_no_submit_contract(monkeypatch):
    monkeypatch.setattr(
        api_module,
        "acknowledge_shadow_evidence_operator_review",
        lambda: {
            "status": "operator_review_acknowledged",
            "updated_at": "2026-07-10T06:05:00Z",
            "operator_message": "使用者已確認目前 shadow evidence；daemon 會繼續蒐集，不送單。",
            "operator_review": {"confirmation_due": False},
            "summary": {"last_operator_review_at": "2026-07-10T06:05:00Z"},
            "guardrail": {
                "order_submission_enabled": False,
                "risk_on_order_enabled": False,
                "live_order_submitted": False,
            },
        },
    )

    payload = asyncio.run(api_module.api_execution_shadow_evidence_ack())

    assert payload["ok"] is True
    assert payload["status"] == "operator_review_acknowledged"
    assert payload["operator_review"]["confirmation_due"] is False
    assert payload["guardrail"]["order_submission_enabled"] is False
    assert payload["guardrail"]["risk_on_order_enabled"] is False
    assert payload["guardrail"]["live_order_submitted"] is False
