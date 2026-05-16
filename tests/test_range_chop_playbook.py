from execution.range_chop_playbook import build_range_chop_playbook


def test_range_chop_playbook_keeps_choppy_market_practical_without_unlocking_buy_add():
    live_runtime_truth = {
        "regime_label": "chop",
        "regime_gate": "BLOCK",
        "structure_bucket": "BLOCK|structure_quality_block|q00",
        "runtime_closure_state": "current_live_deployment_blocked",
        "deployment_blocker": "under_minimum_exact_live_structure_bucket",
        "deployment_blocker_reason": "current-live 精準分桶樣本不足",
        "allowed_layers": 0,
        "sleeve_routing": {
            "current_regime": "chop",
            "current_regime_gate": "BLOCK",
            "current_structure_bucket": "BLOCK|structure_quality_block|q00",
        },
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

    playbook = build_range_chop_playbook(live_runtime_truth, high_conviction_topk)

    assert playbook["key"] == "range_chop_playbook"
    assert playbook["status"] == "shadow_reduce_only"
    assert playbook["shadow_available"] is True
    assert playbook["shadow_mode"] == "paper_shadow"
    assert playbook["risk_reduction_allowed"] is True
    assert playbook["buy_add_requires_current_live_gate"] is True
    assert playbook["risk_on_order_enabled"] is False
    assert playbook["order_submission_enabled"] is False
    assert "range_shadow_observe" in playbook["allowed_operator_actions"]
    assert "reduce_position" in playbook["allowed_operator_actions"]
    assert "buy" in playbook["blocked_operator_actions"]
    assert "add_exposure" in playbook["blocked_operator_actions"]
    assert "enable_automation" in playbook["blocked_operator_actions"]
    assert playbook["support_context"]["current_rows"] == 2
    assert playbook["support_context"]["minimum_rows"] == 50
    assert playbook["support_context"]["gap_to_minimum"] == 48
    assert "不是永遠不能實戰" in playbook["operator_message"]
    assert "減風險" in playbook["operator_message"]
    assert "買入 / 加倉" in playbook["operator_message"]
    assert "即時部署門檻" in playbook["operator_message"]
    assert "區間候選只進影子觀察" in playbook["operator_message"]
    assert "range/chop" not in playbook["operator_message"]
    assert "paper_shadow" not in playbook["operator_message"]
    assert "current-live gate" not in playbook["operator_message"]
    assert "range/chop" not in playbook["next_operator_action"]


def test_range_chop_playbook_stays_standby_when_runtime_is_clean_trend_ready():
    playbook = build_range_chop_playbook(
        {
            "regime_label": "bull",
            "regime_gate": "ALLOW",
            "structure_bucket": "ALLOW|trend|q65",
            "runtime_closure_state": "runtime_visible_preview",
            "allowed_layers": 2,
        },
        {},
    )

    assert playbook["status"] == "standby"
    assert playbook["shadow_available"] is False
    assert playbook["risk_reduction_allowed"] is True
    assert playbook["buy_add_requires_current_live_gate"] is True
    assert playbook["order_submission_enabled"] is False
