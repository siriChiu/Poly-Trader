import importlib.util
import json
import os
import time
from pathlib import Path

from model import q35_bias50_calibration as q35_calibration_module

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hb_parallel_runner.py"
spec = importlib.util.spec_from_file_location("hb_parallel_runner_test_module", MODULE_PATH)
hb_parallel_runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(hb_parallel_runner)

Q35_AUDIT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hb_q35_scaling_audit.py"
q35_spec = importlib.util.spec_from_file_location("hb_q35_scaling_audit_test_module", Q35_AUDIT_PATH)
hb_q35_scaling_audit = importlib.util.module_from_spec(q35_spec)
assert q35_spec.loader is not None
q35_spec.loader.exec_module(hb_q35_scaling_audit)


class _DictRow(dict):
    def keys(self):
        return super().keys()


class _CompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_parse_args_allows_fast_without_hb():
    args = hb_parallel_runner.parse_args(["--fast"])

    assert args.fast is True
    assert args.no_collect is False
    assert hb_parallel_runner.resolve_run_label(args) == "fast"


def test_parse_args_requires_hb_for_full_mode():
    try:
        hb_parallel_runner.parse_args([])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("Expected parser error when --hb missing in full mode")


def test_parse_collect_metadata_extracts_continuity_repair_json():
    payload = '{"inserted_total": 3, "bridge_inserted": 1, "used_bridge": true}'
    stdout = f"hello\nCONTINUITY_REPAIR_META: {payload}\nworld"

    parsed = hb_parallel_runner.parse_collect_metadata(stdout)

    assert parsed["inserted_total"] == 3
    assert parsed["bridge_inserted"] == 1
    assert parsed["used_bridge"] is True


def test_q35_audit_current_row_context_uses_piecewise_bias50_calibration(tmp_path, monkeypatch):
    audit_path = tmp_path / "q35_scaling_audit.json"
    audit_path.write_text(
        json.dumps(
            {
                "overall_verdict": "broader_bull_cohort_recalibration_candidate",
                "current_live": {
                    "regime_label": "bull",
                    "regime_gate": "CAUTION",
                    "structure_bucket": "CAUTION|structure_quality_caution|q35",
                },
                "segmented_calibration": {
                    "status": "segmented_calibration_required",
                    "recommended_mode": "piecewise_quantile_calibration",
                    "exact_lane": {
                        "bias50_distribution": {"p90": 3.1054},
                    },
                    "reference_cohort": {
                        "cohort": "bull_all",
                        "bias50_distribution": {"p90": 4.4607},
                    },
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(q35_calibration_module, "DEFAULT_Q35_AUDIT_PATH", audit_path)
    q35_calibration_module._AUDIT_CACHE.update({"path": None, "mtime": None, "data": None})
    monkeypatch.setattr(hb_q35_scaling_audit.live_predictor, "_compute_live_regime_gate_debug", lambda *args, **kwargs: {
        "final_gate": "CAUTION",
        "base_gate": "ALLOW",
        "final_reason": "structure_quality_caution",
        "structure_quality": 0.3804,
    })
    monkeypatch.setattr(
        hb_q35_scaling_audit.live_predictor,
        "_live_structure_bucket_from_debug",
        lambda debug: "CAUTION|structure_quality_caution|q35",
    )
    row = _DictRow(
        timestamp="2026-04-15 02:39:05.273899",
        symbol="BTCUSDT",
        regime_label="bull",
        feat_4h_bias50=3.23,
        feat_4h_bias200=5.934,
        feat_nose=0.417,
        feat_pulse=0.7533,
        feat_ear=-0.0026,
        feat_4h_bb_pct_b=0.4575,
        feat_4h_dist_bb_lower=1.4566,
        feat_4h_dist_swing_low=4.9917,
    )

    current = hb_q35_scaling_audit._build_row_context(row)
    preview = hb_q35_scaling_audit.compute_piecewise_bias50_score(
        row["feat_4h_bias50"],
        regime_label="bull",
        regime_gate="CAUTION",
        structure_bucket="CAUTION|structure_quality_caution|q35",
        audit=json.loads(audit_path.read_text(encoding="utf-8")),
    )

    calibration = current["entry_quality_components"]["bias50_calibration"]
    assert current["regime_gate"] == "CAUTION"
    assert current["structure_bucket"] == "CAUTION|structure_quality_caution|q35"
    assert calibration["applied"] is True
    assert calibration["segment"] == "bull_reference_extension"
    assert calibration["score"] == preview["score"]
    assert calibration["reference_cohort"] == "bull_all"
    assert current["entry_quality"] > 0.5

    segmented = {
        "status": "segmented_calibration_required",
        "recommended_mode": "piecewise_quantile_calibration",
        "exact_lane": {"bias50_distribution": {"p90": 3.1054}},
        "reference_cohort": {"cohort": "bull_all", "bias50_distribution": {"p90": 4.4607}},
    }
    preview_with_context = hb_q35_scaling_audit.compute_piecewise_bias50_score(
        row["feat_4h_bias50"],
        regime_label="bull",
        regime_gate="CAUTION",
        structure_bucket="CAUTION|structure_quality_caution|q35",
        audit={
            "overall_verdict": "broader_bull_cohort_recalibration_candidate",
            "segmented_calibration": segmented,
            "current_live": {
                "regime_label": "bull",
                "regime_gate": "CAUTION",
                "structure_bucket": "CAUTION|structure_quality_caution|q35",
            },
        },
    )
    runtime_status, runtime_reason = hb_q35_scaling_audit._runtime_contract_state(
        {
            **segmented,
            "status": "segmented_calibration_required",
            "exact_lane": {"percentile_band": "overheat", "bias50_distribution": {"p90": 3.1054}},
        },
        preview_with_context,
    )
    assert runtime_status == "piecewise_runtime_active"
    assert "實際套用" in runtime_reason


def test_q35_audit_refreshes_stale_live_probe_for_current_row(tmp_path, monkeypatch):
    probe_path = tmp_path / "live_predict_probe.json"
    probe_path.write_text(
        json.dumps(
            {
                "feature_timestamp": "2026-04-15 17:00:00",
                "structure_bucket": "CAUTION|structure_quality_caution|q35",
                "entry_quality": 0.4196,
                "q35_discriminative_redesign_applied": False,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(hb_q35_scaling_audit, "PROBE_PATH", probe_path)
    refreshed_probe = {
        "feature_timestamp": "2026-04-15 18:04:13.096667",
        "structure_bucket": "CAUTION|structure_quality_caution|q35",
        "entry_quality": 0.5505,
        "q35_discriminative_redesign_applied": True,
        "entry_quality_components": {
            "q35_discriminative_redesign": {"applied": True}
        },
    }
    calls = []

    def _fake_run(cmd, cwd=None, capture_output=None, text=None):
        calls.append({"cmd": cmd, "cwd": cwd})
        return _CompletedProcess(stdout=json.dumps(refreshed_probe))

    monkeypatch.setattr(hb_q35_scaling_audit.subprocess, "run", _fake_run)

    probe = hb_q35_scaling_audit._load_or_refresh_live_predict_probe(
        "2026-04-15 18:04:13.096667",
        "CAUTION|structure_quality_caution|q35",
    )

    assert len(calls) == 1
    assert probe["q35_discriminative_redesign_applied"] is True
    assert json.loads(probe_path.read_text(encoding="utf-8"))["entry_quality"] == 0.5505


def test_q35_audit_main_runs_post_write_second_pass_refresh(monkeypatch, capsys):
    call_state = {"probe_calls": 0, "write_calls": 0, "force_refresh_flags": []}
    current = {
        "timestamp": "2026-04-15 19:35:36.534053",
        "symbol": "BTCUSDT",
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "base_gate": "ALLOW",
        "gate_reason": "structure_quality_caution",
        "structure_bucket": "CAUTION|structure_quality_caution|q35",
        "structure_quality": 0.5751,
        "entry_quality": 0.4059,
        "entry_quality_label": "D",
        "allowed_layers_raw": 0,
        "allowed_layers_reason": "entry_quality_below_trade_floor",
        "entry_quality_components": {"trade_floor": 0.55},
        "raw_features": {"feat_4h_bias50": 3.6719, "feat_4h_bias200": 6.2180},
        "source": "legacy_current_live",
        "q35_discriminative_redesign_applied": False,
    }
    runtime_current = {
        **current,
        "entry_quality": 0.4657,
        "entry_quality_label": "D",
        "entry_quality_components": {"trade_floor": 0.55},
        "source": "calibration_component_runtime",
    }
    refreshed_runtime = {
        **current,
        "entry_quality": 0.6136,
        "entry_quality_label": "C",
        "allowed_layers_raw": 1,
        "allowed_layers_reason": "entry_quality_C_single_layer",
        "entry_quality_components": {
            "trade_floor": 0.55,
            "q35_discriminative_redesign": {"applied": True},
        },
        "source": "live_predict_probe",
        "q35_discriminative_redesign_applied": True,
    }

    class _FakeConn:
        def close(self):
            return None

    monkeypatch.setattr(hb_q35_scaling_audit.sqlite3, "connect", lambda *args, **kwargs: _FakeConn())
    monkeypatch.setattr(hb_q35_scaling_audit, "_current_row", lambda conn: _DictRow(feat_4h_bias50=3.6719))

    def _fake_build_row_context(row, *, bias50_calibration_override=None):
        return runtime_current if bias50_calibration_override and bias50_calibration_override.get("applied") else current

    monkeypatch.setattr(hb_q35_scaling_audit, "_build_row_context", _fake_build_row_context)

    def _fake_load_probe(ts, bucket, force_refresh=False):
        call_state["probe_calls"] += 1
        call_state["force_refresh_flags"].append(force_refresh)
        if call_state["probe_calls"] == 1:
            return {
                "target_col": "simulated_pyramid_win",
                "feature_timestamp": ts,
                "structure_bucket": bucket,
                "entry_quality": 0.4657,
                "allowed_layers_raw": 0,
                "allowed_layers_reason": "entry_quality_below_trade_floor",
                "q35_discriminative_redesign_applied": False,
                "entry_quality_components": {"trade_floor": 0.55},
            }
        return {
            "target_col": "simulated_pyramid_win",
            "feature_timestamp": ts,
            "structure_bucket": bucket,
            "entry_quality": 0.6136,
            "allowed_layers_raw": 1,
            "allowed_layers_reason": "entry_quality_C_single_layer",
            "q35_discriminative_redesign_applied": True,
            "entry_quality_components": {
                "trade_floor": 0.55,
                "q35_discriminative_redesign": {"applied": True},
            },
        }

    monkeypatch.setattr(hb_q35_scaling_audit, "_load_or_refresh_live_predict_probe", _fake_load_probe)
    monkeypatch.setattr(hb_q35_scaling_audit, "_historical_rows", lambda conn, use_legacy_bias50_baseline=True: [])
    monkeypatch.setattr(hb_q35_scaling_audit, "_counterfactuals", lambda current: {
        "gate_allow_only_changes_layers": False,
        "entry_if_gate_allow_only": 0.44,
        "layers_if_gate_allow_only": 0,
        "entry_if_bias50_fully_relaxed": 0.70,
        "layers_if_bias50_fully_relaxed": 2,
        "required_bias50_cap_for_floor": -0.0015,
        "current_bias50_value": 3.6719,
    })
    monkeypatch.setattr(hb_q35_scaling_audit, "_summarize_subset", lambda rows, current_bias50: {
        "rows": 0,
        "win_rate": None,
        "current_bias50_percentile": None,
        "bias50_distribution": {"p75": None, "p90": None},
    })
    monkeypatch.setattr(hb_q35_scaling_audit, "_select_segmented_reference_cohort", lambda *args, **kwargs: {})
    monkeypatch.setattr(hb_q35_scaling_audit, "compute_piecewise_bias50_score", lambda *args, **kwargs: {
        "applied": True,
        "score": 0.1993,
        "legacy_score": 0.0,
        "score_delta_vs_legacy": 0.1993,
        "mode": "exact_lane_formula_review",
        "segment": "exact_lane_supported_within_p75",
    })
    monkeypatch.setattr(hb_q35_scaling_audit, "_build_deployed_runtime_current", lambda baseline, runtime, probe: refreshed_runtime if probe.get("q35_discriminative_redesign_applied") else runtime_current)
    monkeypatch.setattr(hb_q35_scaling_audit, "_build_deployment_grade_component_experiment", lambda baseline, runtime, deployed, preview, counter: {
        "verdict": "runtime_patch_crosses_trade_floor" if deployed.get("allowed_layers_raw") else "runtime_patch_improves_but_still_below_floor",
        "baseline_entry_quality": baseline.get("entry_quality"),
        "calibration_runtime_entry_quality": runtime.get("entry_quality"),
        "runtime_entry_quality": deployed.get("entry_quality"),
        "calibration_runtime_delta_vs_legacy": round(runtime.get("entry_quality") - baseline.get("entry_quality"), 4),
        "entry_quality_delta_vs_legacy": round(deployed.get("entry_quality") - baseline.get("entry_quality"), 4),
        "baseline_allowed_layers_raw": baseline.get("allowed_layers_raw"),
        "calibration_runtime_allowed_layers_raw": runtime.get("allowed_layers_raw"),
        "runtime_allowed_layers_raw": deployed.get("allowed_layers_raw"),
        "runtime_remaining_gap_to_floor": round(0.55 - deployed.get("entry_quality"), 4),
        "machine_read_answer": {
            "entry_quality_ge_0_55": deployed.get("entry_quality") >= 0.55,
            "allowed_layers_gt_0": bool(deployed.get("allowed_layers_raw")),
        },
        "q35_discriminative_redesign_applied": deployed.get("q35_discriminative_redesign_applied"),
        "runtime_source": deployed.get("source"),
    })
    monkeypatch.setattr(hb_q35_scaling_audit, "_build_joint_component_experiment", lambda *args, **kwargs: {"verdict": "noop", "machine_read_answer": {"entry_quality_ge_0_55": False, "allowed_layers_gt_0": False}, "best_scenario": {}})
    monkeypatch.setattr(hb_q35_scaling_audit, "_build_exact_supported_bias50_component_experiment", lambda *args, **kwargs: {"verdict": "noop", "machine_read_answer": {"entry_quality_ge_0_55": False, "allowed_layers_gt_0": False, "used_exact_supported_target": False}, "best_scenario": {}})
    monkeypatch.setattr(hb_q35_scaling_audit, "_build_base_mix_component_experiment", lambda *args, **kwargs: {"verdict": "noop", "machine_read_answer": {"entry_quality_ge_0_55": False, "allowed_layers_gt_0": False}, "best_scenario": {}})
    monkeypatch.setattr(hb_q35_scaling_audit, "_build_base_stack_redesign_experiment", lambda *args, **kwargs: {"verdict": "noop", "machine_read_answer": {"entry_quality_ge_0_55": True, "allowed_layers_gt_0": True, "positive_discriminative_gap": True}, "best_discriminative_candidate": {}, "best_floor_candidate": {}, "unsafe_floor_cross_candidate": None, "rows": 0, "wins": 0, "losses": 0, "reason": "ok"})
    monkeypatch.setattr(hb_q35_scaling_audit, "_runtime_contract_state", lambda *args, **kwargs: ("piecewise_runtime_active", "ok"))

    def _fake_write_outputs(*args, **kwargs):
        call_state["write_calls"] += 1

    monkeypatch.setattr(hb_q35_scaling_audit, "_write_outputs", _fake_write_outputs)

    hb_q35_scaling_audit.main()
    output = json.loads(capsys.readouterr().out)

    assert call_state["probe_calls"] == 2
    assert call_state["force_refresh_flags"] == [False, True]
    assert call_state["write_calls"] == 2
    assert output["deployment_grade_component_experiment"]["runtime_entry_quality"] == 0.6136
    assert output["deployment_grade_component_experiment"]["allowed_layers_gt_0"] is True
    assert output["deployment_grade_component_experiment"]["q35_discriminative_redesign_applied"] is True


def test_q35_audit_reuses_aligned_probe_without_refresh(tmp_path, monkeypatch):
    probe_path = tmp_path / "live_predict_probe.json"
    probe_payload = {
        "feature_timestamp": "2026-04-17 14:02:37.686291",
        "structure_bucket": "CAUTION|structure_quality_caution|q35",
        "entry_quality": 0.4523,
    }
    probe_path.write_text(json.dumps(probe_payload), encoding="utf-8")
    monkeypatch.setattr(hb_q35_scaling_audit, "PROBE_PATH", probe_path)

    def _boom(*args, **kwargs):
        raise AssertionError("subprocess refresh should not run when probe already matches current row")

    monkeypatch.setattr(hb_q35_scaling_audit.subprocess, "run", _boom)

    probe = hb_q35_scaling_audit._load_or_refresh_live_predict_probe(
        "2026-04-17 14:02:37.686291",
        "CAUTION|structure_quality_caution|q35",
    )

    assert probe["entry_quality"] == 0.4523



def test_q35_audit_force_refresh_bypasses_aligned_probe_cache(tmp_path, monkeypatch):
    probe_path = tmp_path / "live_predict_probe.json"
    probe_path.write_text(
        json.dumps(
            {
                "feature_timestamp": "2026-04-18 07:41:19.009526",
                "structure_bucket": "CAUTION|structure_quality_caution|q35",
                "entry_quality": 0.4858,
                "q35_discriminative_redesign_applied": False,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(hb_q35_scaling_audit, "PROBE_PATH", probe_path)

    refreshed_probe = {
        "feature_timestamp": "2026-04-18 07:41:19.009526",
        "structure_bucket": "CAUTION|structure_quality_caution|q35",
        "entry_quality": 0.6955,
        "q35_discriminative_redesign_applied": True,
        "entry_quality_components": {
            "q35_discriminative_redesign": {"applied": True}
        },
    }
    calls = []

    def _fake_run(cmd, cwd=None, capture_output=None, text=None):
        calls.append({"cmd": cmd, "cwd": cwd})
        return _CompletedProcess(stdout=json.dumps(refreshed_probe))

    monkeypatch.setattr(hb_q35_scaling_audit.subprocess, "run", _fake_run)

    probe = hb_q35_scaling_audit._load_or_refresh_live_predict_probe(
        "2026-04-18 07:41:19.009526",
        "CAUTION|structure_quality_caution|q35",
        force_refresh=True,
    )

    assert len(calls) == 1
    assert probe["entry_quality"] == 0.6955
    assert probe["q35_discriminative_redesign_applied"] is True
    assert json.loads(probe_path.read_text(encoding="utf-8"))["entry_quality"] == 0.6955



def test_q35_audit_main_short_circuits_when_circuit_breaker_preempts_runtime(monkeypatch, capsys):
    current = {
        "timestamp": "2026-04-17 13:49:17.419527",
        "symbol": "BTCUSDT",
        "regime_label": "bull",
        "regime_gate": "CAUTION",
        "entry_quality_label": "D",
        "structure_bucket": "CAUTION|structure_quality_caution|q35",
        "entry_quality": 0.3323,
        "allowed_layers_raw": 0,
        "allowed_layers_reason": "entry_quality_below_trade_floor",
        "structure_quality": 0.3804,
        "raw_features": {"feat_4h_bias50": 1.2345},
    }
    probe = {
        "target_col": "simulated_pyramid_win",
        "signal": "CIRCUIT_BREAKER",
        "deployment_blocker": "circuit_breaker_active",
        "deployment_blocker_reason": "Recent 50-sample win rate: 26.00% < 30%",
        "deployment_blocker_source": "circuit_breaker",
        "allowed_layers": 0,
        "allowed_layers_reason": "circuit_breaker_blocks_trade",
        "allowed_layers_raw_reason": "circuit_breaker_preempts_runtime_sizing",
        "runtime_closure_state": "circuit_breaker_active",
        "runtime_closure_summary": "circuit breaker active",
    }
    written = {}

    class _FakeConn:
        row_factory = None

        def close(self):
            return None

    monkeypatch.setattr(hb_q35_scaling_audit.sqlite3, "connect", lambda *args, **kwargs: _FakeConn())
    monkeypatch.setattr(hb_q35_scaling_audit, "_current_row", lambda conn: _DictRow(feat_4h_bias50=1.2345))
    monkeypatch.setattr(hb_q35_scaling_audit, "_build_row_context", lambda row, *, bias50_calibration_override=None: dict(current))
    monkeypatch.setattr(hb_q35_scaling_audit, "_load_or_refresh_live_predict_probe", lambda ts, bucket: dict(probe))
    monkeypatch.setattr(
        hb_q35_scaling_audit,
        "_write_runtime_blocker_preempt_outputs",
        lambda report: written.setdefault("report", report),
    )
    monkeypatch.setattr(
        hb_q35_scaling_audit,
        "_historical_rows",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("historical rows should not be loaded when circuit breaker preempts q35 audit")),
    )

    hb_q35_scaling_audit.main()
    output = json.loads(capsys.readouterr().out)

    assert output["overall_verdict"] == "runtime_blocker_preempts_q35_scaling"
    assert output["runtime_blocker"]["type"] == "circuit_breaker_active"
    assert written["report"]["segmented_calibration"]["status"] == "runtime_blocker_preempts_q35_scaling"
    assert written["report"]["scope_applicability"]["status"] == "current_live_q35_lane_active"


def test_q35_audit_main_short_circuits_when_current_row_is_not_q35(monkeypatch, capsys):
    current = {
        "timestamp": "2026-04-17 14:02:37.686291",
        "symbol": "BTCUSDT",
        "regime_label": "bull",
        "regime_gate": "ALLOW",
        "entry_quality_label": "D",
        "structure_bucket": "ALLOW|base_allow|q65",
        "entry_quality": 0.4523,
        "allowed_layers_raw": 0,
        "allowed_layers_reason": "entry_quality_below_trade_floor",
        "structure_quality": 0.6623,
        "raw_features": {"feat_4h_bias50": 5.5331},
    }
    written = {}

    class _FakeConn:
        row_factory = None

        def close(self):
            return None

    monkeypatch.setattr(hb_q35_scaling_audit.sqlite3, "connect", lambda *args, **kwargs: _FakeConn())
    monkeypatch.setattr(hb_q35_scaling_audit, "_current_row", lambda conn: _DictRow(feat_4h_bias50=5.5331))
    monkeypatch.setattr(hb_q35_scaling_audit, "_build_row_context", lambda row, *, bias50_calibration_override=None: dict(current))
    monkeypatch.setattr(
        hb_q35_scaling_audit,
        "_write_reference_only_outputs",
        lambda report: written.setdefault("report", report),
    )
    monkeypatch.setattr(
        hb_q35_scaling_audit,
        "_load_or_refresh_live_predict_probe",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("probe refresh should not run for reference-only non-q35 rows")),
    )
    monkeypatch.setattr(
        hb_q35_scaling_audit,
        "_historical_rows",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("historical rows should not run for reference-only non-q35 rows")),
    )

    hb_q35_scaling_audit.main()
    output = json.loads(capsys.readouterr().out)

    assert output["overall_verdict"] == "reference_only_current_bucket_outside_q35"
    assert written["report"]["scope_applicability"]["status"] == "reference_only_current_bucket_outside_q35"
    assert written["report"]["recommended_action"].startswith("current live row 已離開 q35 lane")



def test_q35_runtime_contract_state_marks_runtime_ready_when_current_row_is_back_inside_exact_lane():
    runtime_status, runtime_reason = hb_q35_scaling_audit._runtime_contract_state(
        {
            "status": "segmented_calibration_required",
            "exact_lane": {"percentile_band": "elevated_but_within_p90"},
        },
        {
            "applied": False,
            "mode": "legacy_linear",
            "segment": None,
        },
    )

    assert runtime_status == "piecewise_runtime_ready_current_row_outside_extension"
    assert "已經實作" in runtime_reason
    assert "不需要套用" in runtime_reason



def test_q35_runtime_contract_state_marks_formula_review_active_when_exact_lane_score_is_applied():
    runtime_status, runtime_reason = hb_q35_scaling_audit._runtime_contract_state(
        {
            "status": "formula_review_required",
            "exact_lane": {"percentile_band": "elevated_but_within_p90"},
        },
        {
            "applied": True,
            "mode": "exact_lane_formula_review",
            "segment": "exact_lane_elevated_within_p90",
        },
    )

    assert runtime_status == "piecewise_runtime_active"
    assert "實際套用" in runtime_reason


def test_q35_runtime_contract_state_marks_formula_review_active_when_core_band_score_is_applied():
    runtime_status, runtime_reason = hb_q35_scaling_audit._runtime_contract_state(
        {
            "status": "formula_review_required",
            "exact_lane": {"percentile_band": "core_normal"},
        },
        {
            "applied": True,
            "mode": "exact_lane_formula_review",
            "segment": "exact_lane_supported_within_p75",
        },
    )

    assert runtime_status == "piecewise_runtime_active"
    assert "實際套用" in runtime_reason


def test_q35_runtime_contract_state_marks_hold_only_when_reference_band_is_still_overheat():
    runtime_status, runtime_reason = hb_q35_scaling_audit._runtime_contract_state(
        {
            "status": "segmented_calibration_required",
            "exact_lane": {"percentile_band": "overheat"},
        },
        {
            "applied": False,
            "mode": "piecewise_quantile_calibration",
            "segment": "reference_overheat",
        },
    )

    assert runtime_status == "piecewise_runtime_ready_hold_only_current_row"
    assert "hold-only" in runtime_reason


def test_q35_scope_applicability_marks_non_q35_rows_reference_only():
    applicability = hb_q35_scaling_audit._q35_scope_applicability(
        {"structure_bucket": "CAUTION|structure_quality_caution|q15"}
    )

    assert applicability["status"] == "reference_only_current_bucket_outside_q35"
    assert applicability["active_for_current_live_row"] is False
    assert applicability["target_structure_bucket"] == "CAUTION|structure_quality_caution|q35"
    assert "reference-only" in applicability["reason"]


def test_collect_live_predictor_diagnostics_preserves_circuit_breaker_reason():
    payload = {
        "target_col": "simulated_pyramid_win",
        "used_model": "circuit_breaker",
        "model_type": "circuit_breaker",
        "signal": "CIRCUIT_BREAKER",
        "confidence": 0.5,
        "should_trade": False,
        "reason": "Consecutive loss streak: 50 >= 50; Recent 50-sample win rate: 0.00% < 30%",
        "streak": 50,
        "win_rate": 0.0,
        "recent_window_win_rate": 0.0,
        "recent_window_wins": 0,
        "window_size": 50,
        "triggered_by": ["streak", "recent_win_rate"],
        "horizon_minutes": 1440,
        "regime_label": "bull",
        "allowed_layers": 0,
    }

    result = hb_parallel_runner.collect_live_predictor_diagnostics({"stdout": json.dumps(payload)})

    assert result["model_type"] == "circuit_breaker"
    assert result["signal"] == "CIRCUIT_BREAKER"
    assert result["runtime_blocker"] == "circuit_breaker"
    assert result["reason"] == "Consecutive loss streak: 50 >= 50; Recent 50-sample win rate: 0.00% < 30%"
    assert result["streak"] == 50
    assert result["recent_window_win_rate"] == 0.0
    assert result["triggered_by"] == ["streak", "recent_win_rate"]
    assert result["horizon_minutes"] == 1440
    assert result["allowed_layers"] == 0


def test_collect_live_predictor_diagnostics_preserves_deployment_blocker_fields():
    payload = {
        "target_col": "simulated_pyramid_win",
        "used_model": "regime_bull_ensemble",
        "model_type": "RegimeAwarePredictor",
        "signal": "HOLD",
        "confidence": 0.23,
        "should_trade": False,
        "regime_label": "bull",
        "allowed_layers_raw": 0,
        "allowed_layers": 0,
        "deployment_blocker": "bull_q35_no_deploy_governance",
        "deployment_blocker_reason": "safe redesign 失敗，只剩 unsafe floor cross",
        "deployment_blocker_source": "q35_scaling_audit+q15_support_audit",
        "deployment_blocker_details": {
            "support_route_verdict": "exact_bucket_supported",
            "unsafe_floor_cross_candidate": {"weights": {"feat_ear": 1.0}},
        },
    }

    result = hb_parallel_runner.collect_live_predictor_diagnostics({"stdout": json.dumps(payload)})

    assert result["runtime_blocker"] is None
    assert result["deployment_blocker"] == "bull_q35_no_deploy_governance"
    assert result["deployment_blocker_reason"] == "safe redesign 失敗，只剩 unsafe floor cross"
    assert result["deployment_blocker_source"] == "q35_scaling_audit+q15_support_audit"
    assert result["deployment_blocker_details"]["support_route_verdict"] == "exact_bucket_supported"


def test_needs_q15_post_audit_runtime_resync_when_support_ready_but_probe_still_unpatched():
    live_predictor_diagnostics = {
        "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
        "q15_exact_supported_component_patch_applied": False,
        "allowed_layers_raw": 0,
        "allowed_layers": 0,
    }
    q15_support_summary = {
        "scope_applicability": {
            "status": "current_live_q15_lane_active",
            "active_for_current_live_row": True,
            "current_structure_bucket": "CAUTION|structure_quality_caution|q15",
        },
        "support_route": {
            "verdict": "exact_bucket_supported",
            "deployable": True,
        },
        "floor_cross_legality": {
            "verdict": "legal_component_experiment_after_support_ready",
            "legal_to_relax_runtime_gate": True,
        },
        "component_experiment": {
            "verdict": "exact_supported_component_experiment_ready",
            "feature": "feat_4h_bias50",
            "machine_read_answer": {
                "support_ready": True,
                "entry_quality_ge_0_55": True,
                "allowed_layers_gt_0": True,
                "preserves_positive_discrimination": True,
            },
        },
    }

    assert hb_parallel_runner._needs_q15_post_audit_runtime_resync(
        live_predictor_diagnostics,
        q15_support_summary,
    ) is True


def test_q35_joint_component_experiment_quantifies_remaining_bias50_gap():
    runtime_current = {
        "regime_gate": "CAUTION",
        "entry_quality": 0.4919,
        "allowed_layers_raw": 0,
        "entry_quality_components": {
            "base_quality": 0.5263,
            "structure_quality": 0.3887,
            "trade_floor": 0.55,
            "base_components": [
                {"feature": "feat_4h_bias50", "normalized_score": 0.2335},
            ],
            "structure_components": [
                {"feature": "feat_4h_dist_swing_low", "raw_value": 4.9499, "normalized_score": 0.4950},
            ],
        },
    }
    exact_summary = {
        "structure_feature_distributions": {
            "feat_4h_dist_swing_low": {"distribution": {"p75": 5.4}}
        }
    }
    winner_summary = {
        "structure_feature_distributions": {
            "feat_4h_dist_swing_low": {"distribution": {"p50": 5.6592, "p75": 6.1}}
        }
    }

    result = hb_q35_scaling_audit._build_joint_component_experiment(runtime_current, exact_summary, winner_summary)

    assert result["verdict"] == "joint_component_experiment_improves_but_still_below_floor"
    assert result["machine_read_answer"]["entry_quality_ge_0_55"] is False
    assert result["best_scenario"]["scenario"] == "winner_p75"
    assert result["best_scenario"]["entry_quality_after"] > runtime_current["entry_quality"]
    assert result["best_scenario"]["required_bias50_cap_after_swing_uplift"] > 0.2635


def test_q35_exact_supported_bias50_component_experiment_surfaces_remaining_floor_gap():
    runtime_current = {
        "regime_gate": "CAUTION",
        "entry_quality": 0.4332,
        "allowed_layers_raw": 0,
        "entry_quality_components": {
            "base_quality": 0.4593,
            "structure_quality": 0.3551,
            "trade_floor": 0.55,
            "base_components": [
                {"feature": "feat_4h_bias50", "normalized_score": 0.2347, "weight": 0.4},
            ],
        },
    }
    runtime_exact_summary = {
        "base_component_score_distributions": {
            "feat_4h_bias50": {"distribution": {"p75": 0.30, "p90": 0.35}},
        }
    }
    runtime_winner_summary = {
        "base_component_score_distributions": {
            "feat_4h_bias50": {"distribution": {"p50": 0.31, "p75": 0.34}},
        }
    }

    result = hb_q35_scaling_audit._build_exact_supported_bias50_component_experiment(
        runtime_current,
        runtime_exact_summary,
        runtime_winner_summary,
    )

    assert result["verdict"] == "exact_supported_bias50_component_improves_but_still_below_floor"
    assert result["machine_read_answer"]["entry_quality_ge_0_55"] is False
    assert result["machine_read_answer"]["used_exact_supported_target"] is True
    assert result["best_scenario"]["scenario"] == "exact_runtime_p90"
    assert result["best_scenario"]["entry_quality_after"] > runtime_current["entry_quality"]
    assert result["best_scenario"]["remaining_gap_to_floor"] > 0


def test_q35_base_mix_component_experiment_surfaces_base_stack_gap():
    runtime_current = {
        "regime_gate": "CAUTION",
        "entry_quality": 0.3275,
        "allowed_layers_raw": 0,
        "entry_quality_components": {
            "base_quality": 0.3051,
            "structure_quality": 0.3948,
            "trade_floor": 0.55,
            "base_components": [
                {"feature": "feat_4h_bias50", "normalized_score": 0.2206, "weight": 0.4},
                {"feature": "feat_nose", "normalized_score": 0.3070, "weight": 0.18},
                {"feature": "feat_pulse", "normalized_score": 0.0489, "weight": 0.27},
                {"feature": "feat_ear", "normalized_score": 0.9893, "weight": 0.15},
            ],
        },
    }
    exact_summary = {
        "base_component_score_distributions": {
            "feat_4h_bias50": {"distribution": {"p75": 0.28}},
            "feat_pulse": {"distribution": {"p75": 0.19}},
            "feat_nose": {"distribution": {"p75": 0.34}},
        }
    }
    winner_summary = {
        "base_component_score_distributions": {
            "feat_4h_bias50": {"distribution": {"p50": 0.29, "p75": 0.33}},
            "feat_pulse": {"distribution": {"p50": 0.16, "p75": 0.24}},
            "feat_nose": {"distribution": {"p50": 0.36, "p75": 0.42}},
        }
    }

    result = hb_q35_scaling_audit._build_base_mix_component_experiment(runtime_current, exact_summary, winner_summary)

    assert result["verdict"] == "base_mix_component_experiment_improves_but_still_below_floor"
    assert result["machine_read_answer"]["entry_quality_ge_0_55"] is False
    assert result["best_scenario"]["scenario"] == "winner_triplet_p75"
    assert result["best_scenario"]["entry_quality_after"] > runtime_current["entry_quality"]
    assert result["best_scenario"]["required_bias50_cap_after_base_mix"] < 0.2206


def test_q35_base_stack_redesign_experiment_flags_unsafe_ear_heavy_floor_cross():
    runtime_current = {
        "regime_gate": "CAUTION",
        "entry_quality": 0.3725,
        "allowed_layers_raw": 0,
        "entry_quality_components": {
            "structure_quality": 0.4246,
            "trade_floor": 0.55,
            "base_components": [
                {"feature": "feat_4h_bias50", "normalized_score": 0.2314},
                {"feature": "feat_nose", "normalized_score": 0.2696},
                {"feature": "feat_pulse", "normalized_score": 0.2499},
                {"feature": "feat_ear", "normalized_score": 0.9772},
            ],
        },
    }
    runtime_exact_lane = [
        {
            "simulated_pyramid_win": 1,
            "entry_quality_components": {
                "base_components": [
                    {"feature": "feat_4h_bias50", "normalized_score": 0.22},
                    {"feature": "feat_nose", "normalized_score": 0.35},
                    {"feature": "feat_pulse", "normalized_score": 0.82},
                    {"feature": "feat_ear", "normalized_score": 0.30},
                ]
            },
        },
        {
            "simulated_pyramid_win": 1,
            "entry_quality_components": {
                "base_components": [
                    {"feature": "feat_4h_bias50", "normalized_score": 0.24},
                    {"feature": "feat_nose", "normalized_score": 0.33},
                    {"feature": "feat_pulse", "normalized_score": 0.78},
                    {"feature": "feat_ear", "normalized_score": 0.28},
                ]
            },
        },
        {
            "simulated_pyramid_win": 0,
            "entry_quality_components": {
                "base_components": [
                    {"feature": "feat_4h_bias50", "normalized_score": 0.12},
                    {"feature": "feat_nose", "normalized_score": 0.42},
                    {"feature": "feat_pulse", "normalized_score": 0.11},
                    {"feature": "feat_ear", "normalized_score": 0.98},
                ]
            },
        },
        {
            "simulated_pyramid_win": 0,
            "entry_quality_components": {
                "base_components": [
                    {"feature": "feat_4h_bias50", "normalized_score": 0.08},
                    {"feature": "feat_nose", "normalized_score": 0.40},
                    {"feature": "feat_pulse", "normalized_score": 0.15},
                    {"feature": "feat_ear", "normalized_score": 0.96},
                ]
            },
        },
    ]

    result = hb_q35_scaling_audit._build_base_stack_redesign_experiment(runtime_current, runtime_exact_lane)

    assert result["verdict"] == "base_stack_redesign_floor_cross_requires_non_discriminative_reweight"
    assert result["machine_read_answer"]["entry_quality_ge_0_55"] is False
    assert result["machine_read_answer"]["positive_discriminative_gap"] is True
    assert result["best_discriminative_candidate"]["current_entry_quality_after"] < 0.55
    assert result["best_floor_candidate"]["current_entry_quality_after"] > 0.55
    assert result["unsafe_floor_cross_candidate"] is not None


def test_q35_base_stack_redesign_does_not_treat_zero_gap_floor_cross_as_discriminative():
    runtime_current = {
        "regime_gate": "CAUTION",
        "entry_quality": 0.3413,
        "allowed_layers_raw": 0,
        "entry_quality_components": {
            "structure_quality": 0.3814,
            "trade_floor": 0.55,
            "base_components": [
                {"feature": "feat_4h_bias50", "normalized_score": 0.12},
                {"feature": "feat_nose", "normalized_score": 0.18},
                {"feature": "feat_pulse", "normalized_score": 0.21},
                {"feature": "feat_ear", "normalized_score": 0.9949},
            ],
        },
    }
    runtime_exact_lane = [
        {
            "simulated_pyramid_win": 1,
            "entry_quality_components": {
                "base_components": [
                    {"feature": "feat_4h_bias50", "normalized_score": 0.32},
                    {"feature": "feat_nose", "normalized_score": 0.66},
                    {"feature": "feat_pulse", "normalized_score": 0.79},
                    {"feature": "feat_ear", "normalized_score": 0.20},
                ]
            },
        },
        {
            "simulated_pyramid_win": 1,
            "entry_quality_components": {
                "base_components": [
                    {"feature": "feat_4h_bias50", "normalized_score": 0.30},
                    {"feature": "feat_nose", "normalized_score": 0.64},
                    {"feature": "feat_pulse", "normalized_score": 0.77},
                    {"feature": "feat_ear", "normalized_score": 0.18},
                ]
            },
        },
        {
            "simulated_pyramid_win": 0,
            "entry_quality_components": {
                "base_components": [
                    {"feature": "feat_4h_bias50", "normalized_score": 0.08},
                    {"feature": "feat_nose", "normalized_score": 0.52},
                    {"feature": "feat_pulse", "normalized_score": 0.18},
                    {"feature": "feat_ear", "normalized_score": 0.98},
                ]
            },
        },
        {
            "simulated_pyramid_win": 0,
            "entry_quality_components": {
                "base_components": [
                    {"feature": "feat_4h_bias50", "normalized_score": 0.09},
                    {"feature": "feat_nose", "normalized_score": 0.50},
                    {"feature": "feat_pulse", "normalized_score": 0.21},
                    {"feature": "feat_ear", "normalized_score": 0.97},
                ]
            },
        },
    ]

    result = hb_q35_scaling_audit._build_base_stack_redesign_experiment(runtime_current, runtime_exact_lane)

    assert result["verdict"] == "base_stack_redesign_floor_cross_requires_non_discriminative_reweight"
    assert result["machine_read_answer"]["entry_quality_ge_0_55"] is False
    assert result["machine_read_answer"]["positive_discriminative_gap"] is True
    assert result["best_discriminative_candidate"]["current_entry_quality_after"] < 0.55
    assert result["best_floor_candidate"]["current_entry_quality_after"] > 0.55
    assert result["best_floor_candidate"]["positive_discriminative_gap"] is False
    assert result["unsafe_floor_cross_candidate"] == result["best_floor_candidate"]


def test_collect_q35_scaling_audit_diagnostics_includes_deployment_component_experiment(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "q35_scaling_audit.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-15 12:00:00",
                "target_col": "simulated_pyramid_win",
                "overall_verdict": "bias50_formula_may_be_too_harsh",
                "structure_scaling_verdict": "q35_structure_caution_not_root_cause",
                "current_live": {
                    "regime_label": "bull",
                    "regime_gate": "CAUTION",
                    "structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "entry_quality": 0.5667,
                    "entry_quality_label": "C",
                    "allowed_layers_raw": 1,
                    "allowed_layers_reason": "entry_quality_C_single_layer",
                    "raw_features": {"feat_4h_bias50": 2.9272, "feat_4h_bias200": 5.8838},
                    "entry_quality_components": {"bias50_calibration": {"applied": True, "mode": "exact_lane_formula_review"}},
                    "q35_discriminative_redesign_applied": True,
                    "source": "live_predict_probe",
                    "probe_alignment": {"used_live_predict_probe": True},
                },
                "baseline_current_live": {
                    "regime_label": "bull",
                    "regime_gate": "CAUTION",
                    "structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "entry_quality": 0.4161,
                    "entry_quality_label": "D",
                    "allowed_layers_raw": 0,
                    "allowed_layers_reason": "entry_quality_below_trade_floor",
                    "raw_features": {"feat_4h_bias50": 2.9272, "feat_4h_bias200": 5.8838}
                },
                "calibration_runtime_current": {
                    "entry_quality": 0.4856,
                    "entry_quality_label": "D",
                    "allowed_layers_raw": 0,
                    "allowed_layers_reason": "entry_quality_below_trade_floor",
                    "source": "calibration_component_runtime"
                },
                "scope_applicability": {"status": "current_live_q35_lane_active", "active_for_current_live_row": True},
                "exact_lane_summary": {"rows": 124, "win_rate": 0.95, "current_bias50_percentile": 0.42},
                "broader_bull_cohorts": {"same_gate_same_quality": {}, "same_bucket": {}, "bull_all": {}},
                "segmented_calibration": {"status": "formula_review_required", "recommended_mode": "exact_lane_formula_review"},
                "piecewise_runtime_preview": {"applied": True, "score": 0.2317, "legacy_score": 0.0},
                "deployment_grade_component_experiment": {
                    "verdict": "runtime_patch_crosses_trade_floor",
                    "baseline_entry_quality": 0.4161,
                    "calibration_runtime_entry_quality": 0.4856,
                    "runtime_entry_quality": 0.5667,
                    "calibration_runtime_delta_vs_legacy": 0.0695,
                    "entry_quality_delta_vs_legacy": 0.1506,
                    "baseline_allowed_layers_raw": 0,
                    "calibration_runtime_allowed_layers_raw": 0,
                    "runtime_allowed_layers_raw": 1,
                    "runtime_trade_floor": 0.55,
                    "runtime_remaining_gap_to_floor": -0.0167,
                    "machine_read_answer": {"entry_quality_ge_0_55": True, "allowed_layers_gt_0": True},
                    "runtime_source": "live_predict_probe",
                    "q35_discriminative_redesign_applied": True,
                    "probe_alignment": {"used_live_predict_probe": True},
                    "next_patch_target": "verify_runtime_guardrails",
                    "verify_next": "entry_quality >= 0.55 and allowed_layers > 0",
                },
                "joint_component_experiment": {
                    "verdict": "joint_component_experiment_improves_but_still_below_floor",
                    "reason": "dist_swing_low uplift shrinks the gap but does not cross the floor.",
                    "machine_read_answer": {"entry_quality_ge_0_55": False, "allowed_layers_gt_0": False},
                    "best_scenario": {
                        "scenario": "winner_p50",
                        "entry_quality_after": 0.4977,
                        "remaining_gap_to_floor": 0.0523,
                        "required_bias50_cap_after_swing_uplift": 0.1385,
                    },
                    "verify_next": "summary must persist the best_scenario fields",
                },
                "exact_supported_bias50_component_experiment": {
                    "verdict": "exact_supported_bias50_component_improves_but_still_below_floor",
                    "reason": "exact-supported bias50 uplift still misses the floor.",
                    "machine_read_answer": {"entry_quality_ge_0_55": False, "allowed_layers_gt_0": False, "used_exact_supported_target": True},
                    "best_scenario": {
                        "scenario": "exact_runtime_p90",
                        "entry_quality_after": 0.5124,
                        "remaining_gap_to_floor": 0.0376,
                        "target_score": 0.35,
                    },
                    "verify_next": "summary must persist exact-supported bias50 scenario fields",
                },
                "base_mix_component_experiment": {
                    "verdict": "base_mix_component_experiment_improves_but_still_below_floor",
                    "reason": "bias50 + pulse + nose improves more than structure uplift but still misses the floor.",
                    "machine_read_answer": {"entry_quality_ge_0_55": False, "allowed_layers_gt_0": False},
                    "best_scenario": {
                        "scenario": "winner_triplet_p75",
                        "entry_quality_after": 0.5312,
                        "remaining_gap_to_floor": 0.0188,
                        "required_bias50_cap_after_base_mix": -2.105,
                    },
                    "verify_next": "summary must persist base-mix scenario fields",
                },
                "base_stack_redesign_experiment": {
                    "verdict": "base_stack_redesign_floor_cross_requires_non_discriminative_reweight",
                    "reason": "only ear-heavy weights cross the floor and they destroy discrimination.",
                    "rows": 107,
                    "wins": 99,
                    "losses": 8,
                    "machine_read_answer": {
                        "entry_quality_ge_0_55": False,
                        "allowed_layers_gt_0": False,
                        "positive_discriminative_gap": True,
                    },
                    "best_discriminative_candidate": {
                        "weights": {"feat_4h_bias50": 0.05, "feat_nose": 0.0, "feat_pulse": 0.95, "feat_ear": 0.0},
                        "current_entry_quality_after": 0.2929,
                        "remaining_gap_to_floor": 0.2571,
                        "mean_gap": 0.2247,
                    },
                    "best_floor_candidate": {
                        "weights": {"feat_4h_bias50": 0.0, "feat_nose": 0.0, "feat_pulse": 0.0, "feat_ear": 1.0},
                        "current_entry_quality_after": 0.839,
                        "remaining_gap_to_floor": 0.0,
                        "mean_gap": -0.0109,
                    },
                    "unsafe_floor_cross_candidate": {
                        "weights": {"feat_4h_bias50": 0.0, "feat_nose": 0.0, "feat_pulse": 0.0, "feat_ear": 1.0}
                    },
                    "verify_next": "summary must persist redesign candidate diagnostics",
                },
                "counterfactuals": {"required_bias50_cap_for_floor": 0.1685},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary = hb_parallel_runner.collect_q35_scaling_audit_diagnostics()

    assert summary["deployment_grade_component_experiment"]["verdict"] == "runtime_patch_crosses_trade_floor"
    assert summary["deployment_grade_component_experiment"]["machine_read_answer"]["entry_quality_ge_0_55"] is True
    assert summary["deployment_grade_component_experiment"]["runtime_remaining_gap_to_floor"] == -0.0167
    assert summary["deployment_grade_component_experiment"]["runtime_source"] == "live_predict_probe"
    assert summary["deployment_grade_component_experiment"]["q35_discriminative_redesign_applied"] is True
    assert summary["deployment_grade_component_experiment"]["next_patch_target"] == "verify_runtime_guardrails"
    assert summary["baseline_current_live"]["entry_quality"] == 0.4161
    assert summary["calibration_runtime_current"]["entry_quality"] == 0.4856
    assert summary["current_live"]["entry_quality"] == 0.5667
    assert summary["joint_component_experiment"]["verdict"] == "joint_component_experiment_improves_but_still_below_floor"
    assert summary["joint_component_experiment"]["best_scenario"]["scenario"] == "winner_p50"
    assert summary["joint_component_experiment"]["best_scenario"]["required_bias50_cap_after_swing_uplift"] == 0.1385
    assert summary["exact_supported_bias50_component_experiment"]["verdict"] == "exact_supported_bias50_component_improves_but_still_below_floor"
    assert summary["exact_supported_bias50_component_experiment"]["machine_read_answer"]["used_exact_supported_target"] is True
    assert summary["exact_supported_bias50_component_experiment"]["best_scenario"]["scenario"] == "exact_runtime_p90"
    assert summary["exact_supported_bias50_component_experiment"]["best_scenario"]["target_score"] == 0.35
    assert summary["base_mix_component_experiment"]["verdict"] == "base_mix_component_experiment_improves_but_still_below_floor"
    assert summary["base_mix_component_experiment"]["best_scenario"]["scenario"] == "winner_triplet_p75"
    assert summary["base_mix_component_experiment"]["best_scenario"]["required_bias50_cap_after_base_mix"] == -2.105
    assert summary["base_stack_redesign_experiment"]["verdict"] == "base_stack_redesign_floor_cross_requires_non_discriminative_reweight"
    assert summary["base_stack_redesign_experiment"]["machine_read_answer"]["positive_discriminative_gap"] is True
    assert summary["base_stack_redesign_experiment"]["best_floor_candidate"]["current_entry_quality_after"] == 0.839


def test_collect_current_state_docs_sync_status_flags_stale_docs(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    issues_md = tmp_path / "ISSUES.md"
    roadmap_md = tmp_path / "ROADMAP.md"
    issues_json = tmp_path / "issues.json"
    probe_json = data_dir / "live_predict_probe.json"
    drilldown_json = data_dir / "live_decision_quality_drilldown.json"

    issues_md.write_text("old issues", encoding="utf-8")
    roadmap_md.write_text("old roadmap", encoding="utf-8")
    issues_json.write_text("{}", encoding="utf-8")
    probe_json.write_text("{}", encoding="utf-8")
    drilldown_json.write_text("{}", encoding="utf-8")

    now = time.time()
    os.utime(issues_md, (now - 20, now - 20))
    os.utime(roadmap_md, (now - 10, now - 10))
    os.utime(issues_json, (now + 5, now + 5))
    os.utime(probe_json, (now + 6, now + 6))
    os.utime(drilldown_json, (now + 7, now + 7))

    status = hb_parallel_runner.collect_current_state_docs_sync_status()

    assert status["ok"] is False
    assert status["stale_docs"] == ["ISSUES.md", "ROADMAP.md"]
    assert status["reference_artifacts"] == [
        "issues.json",
        "data/live_predict_probe.json",
        "data/live_decision_quality_drilldown.json",
    ]



def test_save_summary_uses_run_label_and_persists_source_blockers(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))

    counts = {"raw_market_data": 1, "features_normalized": 2, "labels": 3, "simulated_pyramid_win_rate": 0.5}
    collect_result = {
        "attempted": True,
        "success": True,
        "returncode": 0,
        "stdout": 'CONTINUITY_REPAIR_META: {"inserted_total": 2, "bridge_inserted": 1, "used_bridge": true}',
        "stderr": "",
    }
    blockers = {
        "blocked_count": 1,
        "counts_by_history_class": {"snapshot_only": 1},
        "blocked_features": [{"key": "nest_pred", "history_class": "snapshot_only"}],
    }
    results = {"full_ic": {"success": True, "stdout": "ok", "stderr": ""}}

    recent_drift_path = tmp_path / "data" / "recent_drift_report.json"
    recent_drift_path.parent.mkdir(exist_ok=True)
    recent_drift_path.write_text(json.dumps({"generated_at": "2026-04-17T09:54:00+00:00"}), encoding="utf-8")

    summary, summary_path = hb_parallel_runner.save_summary(
        "fast",
        counts,
        blockers,
        collect_result,
        results,
        elapsed=1.2,
        fast_mode=True,
        ic_diagnostics={"global_pass": 13, "tw_pass": 10, "total_features": 30},
        drift_diagnostics={"generated_at": "2026-04-17T09:54:00+00:00", "primary_window": "100", "primary_alerts": ["regime_concentration"]},
        live_predictor_diagnostics={"decision_quality_label": "D", "allowed_layers": 0},
        live_decision_drilldown={
            "json": "data/live_decision_quality_drilldown.json",
            "chosen_scope": "regime_label+entry_quality_label",
            "q15_exact_supported_component_patch_applied": True,
            "signal": "HOLD",
            "allowed_layers": 1,
            "allowed_layers_reason": "entry_quality_C_single_layer",
            "support_route_verdict": "exact_bucket_supported",
            "remaining_gap_to_floor": 0.051,
            "best_single_component": "feat_4h_bias50",
            "best_single_component_required_score_delta": 0.17,
        },
        q35_scaling_audit={
            "overall_verdict": "hold_only_bias50_overheat_confirmed",
            "structure_scaling_verdict": "q35_structure_caution_not_root_cause",
            "broader_bull_cohorts": {"bull_all": {"current_bias50_percentile": 0.99}},
            "segmented_calibration": {
                "status": "hold_only_confirmed",
                "recommended_mode": "keep_hold_only",
                "reference_cohort": {},
            },
            "deployment_grade_component_experiment": {
                "verdict": "runtime_patch_improves_but_still_below_floor",
                "machine_read_answer": {"entry_quality_ge_0_55": False, "allowed_layers_gt_0": False},
                "runtime_entry_quality": 0.4856,
                "runtime_remaining_gap_to_floor": 0.0644,
            },
        },
        circuit_breaker_audit={
            "root_cause": {"verdict": "mixed_horizon_false_positive"},
            "mixed_scope": {"triggered_by": ["streak", "recent_win_rate"], "streak": {"count": 59}},
            "aligned_scope": {"triggered_by": [], "release_ready": True},
        },
        feature_ablation={"recommended_profile": "core_plus_macro", "profile_role": {"role": "global_shrinkage_winner"}},
        bull_4h_pocket_ablation={"bull_collapse_q35": {"recommended_profile": "core_plus_macro"}, "production_profile_role": {"role": "support_aware_production_profile"}},
        leaderboard_candidate_diagnostics={"selected_feature_profile": "core_only", "dual_profile_state": "leaderboard_global_winner_vs_train_support_fallback", "profile_split": {"verdict": "dual_role_required"}},
        auto_propose_result={"attempted": True, "success": True, "returncode": 0, "stdout": "ok", "stderr": ""},
        docs_sync={"ok": False, "stale_docs": ["ISSUES.md"], "reference_artifacts": ["issues.json"]},
        serial_results={
            "recent_drift_report": {
                "result": {"attempted": True, "success": False, "returncode": -1, "stdout": "", "stderr": "TIMEOUT after 30s"},
                "diagnostics": {"generated_at": "2026-04-17T09:54:00+00:00", "primary_window": "100"},
                "artifact_path": recent_drift_path,
            },
            "auto_propose_fixes": {
                "result": {"attempted": True, "success": True, "returncode": 0, "stdout": "ok", "stderr": ""},
                "artifact_path": tmp_path / "issues.json",
            },
        },
    )

    assert summary["heartbeat"] == "fast"
    assert summary["mode"] == "fast"
    assert summary["collect_result"]["success"] is True
    assert summary["collect_result"]["continuity_repair"]["bridge_inserted"] == 1
    assert summary["collect_result"]["continuity_repair"]["bridge_fallback_streak"] == 1
    assert summary["source_blockers"]["blocked_count"] == 1
    assert summary["ic_diagnostics"]["tw_pass"] == 10
    assert summary["drift_diagnostics"]["primary_window"] == "100"
    assert summary["live_predictor_diagnostics"]["decision_quality_label"] == "D"
    assert summary["live_decision_drilldown"]["best_single_component"] == "feat_4h_bias50"
    assert summary["live_decision_drilldown"]["q15_exact_supported_component_patch_applied"] is True
    assert summary["live_decision_drilldown"]["signal"] == "HOLD"
    assert summary["live_decision_drilldown"]["allowed_layers"] == 1
    assert summary["q35_scaling_audit"]["overall_verdict"] == "hold_only_bias50_overheat_confirmed"
    assert summary["q35_scaling_audit"]["segmented_calibration"]["status"] == "hold_only_confirmed"
    assert summary["circuit_breaker_audit"]["root_cause"]["verdict"] == "mixed_horizon_false_positive"
    assert summary["circuit_breaker_audit"]["aligned_scope"]["release_ready"] is True
    assert summary["feature_ablation"]["recommended_profile"] == "core_plus_macro"
    assert summary["feature_ablation"]["profile_role"]["role"] == "global_shrinkage_winner"
    assert summary["bull_4h_pocket_ablation"]["bull_collapse_q35"]["recommended_profile"] == "core_plus_macro"
    assert summary["bull_4h_pocket_ablation"]["production_profile_role"]["role"] == "support_aware_production_profile"
    assert summary["leaderboard_candidate_diagnostics"]["selected_feature_profile"] == "core_only"
    assert summary["leaderboard_candidate_diagnostics"]["profile_split"]["verdict"] == "dual_role_required"
    assert summary["auto_propose"]["success"] is True
    assert summary["docs_sync"]["ok"] is False
    assert summary["docs_sync"]["stale_docs"] == ["ISSUES.md"]
    assert summary["serial_results"]["recent_drift_report"]["timed_out"] is True
    assert summary["serial_results"]["recent_drift_report"]["fallback_artifact_used"] is True
    assert summary["serial_results"]["recent_drift_report"]["artifact_path"] == str(recent_drift_path)
    assert summary["serial_results"]["recent_drift_report"]["artifact_generated_at"] == "2026-04-17T09:54:00+00:00"
    assert summary_path.endswith("heartbeat_fast_summary.json")

    saved = json.loads(Path(summary_path).read_text())
    assert saved["collect_result"]["attempted"] is True
    assert saved["collect_result"]["continuity_repair"]["used_bridge"] is True
    assert saved["source_blockers"]["blocked_features"][0]["key"] == "nest_pred"
    assert saved["ic_diagnostics"]["global_pass"] == 13
    assert saved["drift_diagnostics"]["primary_alerts"] == ["regime_concentration"]
    assert saved["live_predictor_diagnostics"]["allowed_layers"] == 0
    assert saved["live_decision_drilldown"]["remaining_gap_to_floor"] == 0.051
    assert saved["live_decision_drilldown"]["support_route_verdict"] == "exact_bucket_supported"
    assert saved["live_decision_drilldown"]["allowed_layers_reason"] == "entry_quality_C_single_layer"
    assert saved["q35_scaling_audit"]["structure_scaling_verdict"] == "q35_structure_caution_not_root_cause"
    assert saved["q35_scaling_audit"]["broader_bull_cohorts"]["bull_all"]["current_bias50_percentile"] == 0.99
    assert saved["q35_scaling_audit"]["segmented_calibration"]["recommended_mode"] == "keep_hold_only"
    assert saved["circuit_breaker_audit"]["mixed_scope"]["streak"]["count"] == 59
    assert saved["circuit_breaker_audit"]["aligned_scope"]["release_ready"] is True
    assert saved["feature_ablation"]["recommended_profile"] == "core_plus_macro"
    assert saved["feature_ablation"]["profile_role"]["role"] == "global_shrinkage_winner"
    assert saved["bull_4h_pocket_ablation"]["bull_collapse_q35"]["recommended_profile"] == "core_plus_macro"
    assert saved["bull_4h_pocket_ablation"]["production_profile_role"]["role"] == "support_aware_production_profile"
    assert saved["leaderboard_candidate_diagnostics"]["dual_profile_state"] == "leaderboard_global_winner_vs_train_support_fallback"
    assert saved["leaderboard_candidate_diagnostics"]["profile_split"]["verdict"] == "dual_role_required"
    assert saved["auto_propose"]["stdout_preview"] == "ok"
    assert saved["docs_sync"]["ok"] is False
    assert saved["docs_sync"]["reference_artifacts"] == ["issues.json"]
    assert saved["serial_results"]["recent_drift_report"]["fallback_artifact_used"] is True
    assert saved["serial_results"]["recent_drift_report"]["timed_out"] is True


def test_collect_recent_drift_diagnostics_reads_primary_window(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "recent_drift_report.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-17T09:54:00+00:00",
                "target_col": "simulated_pyramid_win",
                "horizon_minutes": 1440,
                "full_sample": {"rows": 11134, "win_rate": 0.6459},
                "primary_window": {
                    "window": "100",
                    "alerts": ["regime_concentration"],
                    "summary": {
                        "rows": 100,
                        "win_rate": 0.93,
                        "win_rate_delta_vs_full": 0.2841,
                        "dominant_regime": "chop",
                        "dominant_regime_share": 0.97,
                        "drift_interpretation": "supported_extreme_trend",
                        "feature_diagnostics": {
                            "feature_count": 30,
                            "low_variance_count": 4,
                            "low_distinct_count": 2,
                            "null_heavy_count": 1,
                        },
                        "target_path_diagnostics": {
                            "window_start_timestamp": "2026-04-12 00:00:00",
                            "window_end_timestamp": "2026-04-13 03:00:00",
                            "latest_target": 1,
                            "tail_target_streak": {
                                "target": 1,
                                "count": 14,
                                "start_timestamp": "2026-04-12 14:00:00",
                                "end_timestamp": "2026-04-13 03:00:00",
                                "regime_counts": {"chop": 14},
                            },
                            "target_regime_breakdown": {"chop:1": 93, "bear:0": 7},
                            "recent_examples": [{"timestamp": "2026-04-13 03:00:00", "target": 1, "regime": "chop"}],
                        },
                    },
                },
            }
        )
    )

    diag = hb_parallel_runner.collect_recent_drift_diagnostics()

    assert diag["generated_at"] == "2026-04-17T09:54:00+00:00"
    assert diag["target_col"] == "simulated_pyramid_win"
    assert diag["primary_window"] == "100"
    assert diag["primary_summary"]["dominant_regime"] == "chop"
    assert diag["primary_summary"]["drift_interpretation"] == "supported_extreme_trend"
    assert diag["primary_summary"]["feature_diagnostics"]["low_variance_count"] == 4
    assert diag["primary_summary"]["target_path_diagnostics"]["tail_target_streak"]["count"] == 14
    assert diag["primary_summary"]["target_path_diagnostics"]["recent_examples"][0]["timestamp"] == "2026-04-13 03:00:00"


def test_collect_live_predictor_diagnostics_reads_probe_json(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "live_predict_probe.json").write_text(
        json.dumps(
            {
                "target_col": "simulated_pyramid_win",
                "used_model": "regime_bull_ensemble",
                "signal": "HOLD",
                "confidence": 0.21,
                "should_trade": False,
                "regime_label": "bull",
                "model_route_regime": "bull",
                "regime_gate": "ALLOW",
                "entry_quality_label": "D",
                "entry_quality_components": {
                    "entry_quality": 0.3861,
                    "trade_floor": 0.55,
                    "trade_floor_gap": -0.1639,
                    "base_components": [{"feature": "feat_4h_bias50"}],
                    "structure_components": [{"feature": "feat_4h_bb_pct_b"}],
                },
                "allowed_layers_raw": 0,
                "allowed_layers": 0,
                "allowed_layers_reason": "entry_quality_below_trade_floor",
                "execution_guardrail_applied": True,
                "decision_quality_calibration_scope": "entry_quality_label",
                "decision_quality_scope_diagnostics": {
                    "regime_gate+entry_quality_label": {"rows": 315},
                    "entry_quality_label": {"rows": 3186},
                },
                "decision_quality_recent_pathology_applied": True,
                "decision_quality_recent_pathology_window": 500,
                "decision_quality_recent_pathology_alerts": ["label_imbalance"],
                "decision_quality_exact_live_lane_bucket_verdict": "toxic_sub_bucket_identified",
                "decision_quality_exact_live_lane_bucket_reason": "q15 子 bucket 比 q35 差，應升級成 veto 候選",
                "decision_quality_exact_live_lane_toxic_bucket": {
                    "bucket": "CAUTION|structure_quality_caution|q15",
                    "rows": 4,
                    "win_rate": 0.0,
                },
                "decision_quality_exact_live_lane_bucket_diagnostics": {
                    "verdict": "toxic_sub_bucket_identified"
                },
                "decision_quality_label": "D",
                "expected_win_rate": 0.154,
                "expected_pyramid_quality": -0.1536,
                "non_null_4h_feature_count": 10,
                "non_null_4h_lag_count": 30,
                "decision_quality_recent_pathology_summary": {
                    "rows": 500,
                    "reference_window_comparison": {
                        "top_mean_shift_features": [{"feature": "feat_4h_dist_swing_low"}]
                    },
                },
            }
        )
    )

    diag = hb_parallel_runner.collect_live_predictor_diagnostics()

    assert diag["used_model"] == "regime_bull_ensemble"
    assert diag["decision_quality_recent_pathology_applied"] is True
    assert diag["decision_quality_recent_pathology_window"] == 500
    assert diag["decision_quality_exact_live_lane_bucket_verdict"] == "toxic_sub_bucket_identified"
    assert diag["decision_quality_exact_live_lane_toxic_bucket"]["bucket"] == "CAUTION|structure_quality_caution|q15"
    assert diag["allowed_layers_raw_reason"] == "entry_quality_below_trade_floor"
    assert diag["allowed_layers_reason"] == "entry_quality_below_trade_floor"
    assert diag["entry_quality_components"]["trade_floor_gap"] == -0.1639
    assert diag["entry_quality_components"]["base_components"][0]["feature"] == "feat_4h_bias50"
    assert diag["decision_quality_label"] == "D"
    assert diag["non_null_4h_lag_count"] == 30
    assert diag["decision_quality_scope_diagnostics"]["entry_quality_label"]["rows"] == 3186


def test_collect_q35_scaling_audit_diagnostics_reads_hold_only_verdict(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "q35_scaling_audit.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-15 00:31:10",
                "target_col": "simulated_pyramid_win",
                "overall_verdict": "hold_only_bias50_overheat_confirmed",
                "structure_scaling_verdict": "q35_structure_caution_not_root_cause",
                "verdict_reason": "gate alone does not change layers",
                "recommended_action": "keep hold-only",
                "current_live": {
                    "regime_label": "bull",
                    "regime_gate": "CAUTION",
                    "base_gate": "ALLOW",
                    "gate_reason": "structure_quality_caution",
                    "structure_bucket": "CAUTION|structure_quality_caution|q15",
                    "structure_quality": 0.4553,
                    "entry_quality": 0.5341,
                    "entry_quality_label": "D",
                    "allowed_layers_raw": 0,
                    "allowed_layers_reason": "entry_quality_below_trade_floor",
                    "entry_quality_components": {
                        "bias50_calibration": {
                            "applied": True,
                            "score": 0.3224,
                            "legacy_score": 0.0,
                            "score_delta_vs_legacy": 0.3224,
                            "mode": "piecewise_quantile_calibration",
                            "segment": "bull_reference_extension",
                            "reference_cohort": "bull_all"
                        }
                    },
                    "raw_features": {
                        "feat_4h_bias50": 3.7318,
                        "feat_4h_bias200": 6.4571
                    }
                },
                "scope_applicability": {
                    "status": "reference_only_current_bucket_outside_q35",
                    "active_for_current_live_row": False,
                    "current_structure_bucket": "CAUTION|structure_quality_caution|q15",
                    "target_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "reason": "current live row 已不在 q35 lane；q35 scaling audit 只能保留為 reference-only calibration artifact，不得誤寫成當前 live blocker 已落在 q35 formula review。"
                },
                "exact_lane_summary": {
                    "rows": 90,
                    "win_rate": 1.0,
                    "current_bias50_percentile": 1.0,
                    "bias50_distribution": {"p90": 3.1054},
                    "structure_quality_distribution": {"p50": 0.5996},
                    "entry_quality_distribution": {"p90": 0.4944}
                },
                "broader_bull_cohorts": {
                    "same_gate_same_quality": {
                        "rows": 105,
                        "win_rate": 0.9714,
                        "current_bias50_percentile": 0.98,
                        "bias50_distribution": {"p90": 3.55}
                    },
                    "same_bucket": {
                        "rows": 90,
                        "win_rate": 1.0,
                        "current_bias50_percentile": 1.0,
                        "bias50_distribution": {"p90": 3.11}
                    },
                    "bull_all": {
                        "rows": 768,
                        "win_rate": 0.7057,
                        "current_bias50_percentile": 0.99,
                        "bias50_distribution": {"p90": 3.4}
                    }
                },
                "segmented_calibration": {
                    "status": "hold_only_confirmed",
                    "recommended_mode": "keep_hold_only",
                    "reason": "current bias50 高於所有候選 cohorts 的 p90",
                    "runtime_contract_status": "piecewise_runtime_active",
                    "runtime_contract_reason": "piecewise bias50 calibration 已由 predictor / q35 audit 實際套用到 current bull q35 lane；後續 heartbeat 不得再把這題描述成 runtime 尚未吃到新公式。",
                    "exact_lane": {
                        "current_bias50_percentile": 1.0,
                        "percentile_band": "overheat",
                        "delta_vs_p90": 0.6264
                    },
                    "reference_cohort": {},
                    "broader_bull_cohorts": {
                        "bull_all": {
                            "current_bias50_percentile": 0.99,
                            "percentile_band": "overheat"
                        }
                    }
                },
                "piecewise_runtime_preview": {
                    "applied": True,
                    "score": 0.3224,
                    "legacy_score": 0.0,
                    "score_delta_vs_legacy": 0.3224,
                    "mode": "piecewise_quantile_calibration",
                    "segment": "bull_reference_extension",
                    "reference_cohort": "bull_all",
                    "reason": "bias50 is above the exact-lane p90 but still inside the broader bull reference p90; use a decaying extension score instead of forcing a zero score.",
                    "exact_p90": 3.1054,
                    "reference_p90": 4.4607
                },
                "counterfactuals": {
                    "entry_if_gate_allow_only": 0.3726,
                    "layers_if_gate_allow_only": 0,
                    "gate_allow_only_changes_layers": False,
                    "entry_if_bias50_fully_relaxed": 0.6726,
                    "layers_if_bias50_fully_relaxed": 1,
                    "required_bias50_cap_for_floor": -0.5565,
                    "current_bias50_value": 3.7318
                }
            }
        )
    )

    diag = hb_parallel_runner.collect_q35_scaling_audit_diagnostics()

    assert diag["overall_verdict"] == "hold_only_bias50_overheat_confirmed"
    assert diag["structure_scaling_verdict"] == "q35_structure_caution_not_root_cause"
    assert diag["scope_applicability"]["status"] == "reference_only_current_bucket_outside_q35"
    assert diag["scope_applicability"]["active_for_current_live_row"] is False
    assert diag["segmented_calibration"]["status"] == "hold_only_confirmed"
    assert diag["segmented_calibration"]["runtime_contract_status"] == "piecewise_runtime_active"
    assert "實際套用" in diag["segmented_calibration"]["runtime_contract_reason"]
    assert diag["segmented_calibration"]["exact_lane"]["percentile_band"] == "overheat"
    assert diag["current_live"]["feat_4h_bias50"] == 3.7318
    assert diag["current_live"]["bias50_calibration"]["applied"] is True
    assert diag["current_live"]["bias50_calibration"]["segment"] == "bull_reference_extension"
    assert diag["exact_lane_summary"]["current_bias50_percentile"] == 1.0
    assert diag["broader_bull_cohorts"]["same_gate_same_quality"]["rows"] == 105
    assert diag["broader_bull_cohorts"]["bull_all"]["current_bias50_percentile"] == 0.99
    assert diag["piecewise_runtime_preview"]["applied"] is True
    assert diag["piecewise_runtime_preview"]["reference_cohort"] == "bull_all"
    assert diag["counterfactuals"]["gate_allow_only_changes_layers"] is False
    assert diag["counterfactuals"]["layers_if_bias50_fully_relaxed"] == 1


def test_collect_circuit_breaker_audit_diagnostics_reads_mixed_horizon_false_positive(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "circuit_breaker_audit.json").write_text(
        json.dumps(
            {
                "target_col": "simulated_pyramid_win",
                "trigger_thresholds": {
                    "horizon_minutes": 1440,
                    "streak": 50,
                    "recent_window": 50,
                    "recent_win_rate_floor": 0.30,
                },
                "root_cause": {
                    "verdict": "mixed_horizon_false_positive",
                    "summary": "240m tail triggers the mixed breaker while 1440m is healthy.",
                    "recommended_patch": "align circuit breaker to 1440m",
                },
                "mixed_scope": {
                    "triggered": True,
                    "triggered_by": ["streak", "recent_win_rate"],
                    "rows_available": 100,
                    "latest_timestamp": "2026-04-15 03:04:33",
                    "streak": {"count": 59, "threshold": 50, "horizons": {"240": 59}},
                    "recent_window": {"window_size": 50, "win_rate": 0.0, "losses": 50},
                },
                "aligned_scope": {
                    "triggered": False,
                    "triggered_by": [],
                    "release_ready": True,
                    "rows_available": 100,
                    "latest_timestamp": "2026-04-14 06:49:03",
                    "streak": {"count": 0, "threshold": 50, "horizons": {"1440": 0}},
                    "recent_window": {"window_size": 50, "win_rate": 1.0, "losses": 0},
                    "release_condition": {"additional_recent_window_wins_needed": 0},
                    "tail_pathology": {"loss_share": 0.0},
                },
            }
        )
    )

    diag = hb_parallel_runner.collect_circuit_breaker_audit_diagnostics()

    assert diag["root_cause"]["verdict"] == "mixed_horizon_false_positive"
    assert diag["mixed_scope"]["triggered_by"] == ["streak", "recent_win_rate"]
    assert diag["mixed_scope"]["streak"]["count"] == 59
    assert diag["aligned_scope"]["release_ready"] is True
    assert diag["aligned_scope"]["recent_window"]["win_rate"] == 1.0
    assert diag["aligned_scope"]["release_condition"]["additional_recent_window_wins_needed"] == 0
    assert diag["aligned_scope"]["tail_pathology"]["loss_share"] == 0.0


def test_collect_feature_ablation_diagnostics_reads_recommended_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "feature_group_ablation.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-14 10:00:00",
                "target_col": "simulated_pyramid_win",
                "recent_rows": 5000,
                "recommended_profile": "core_plus_macro",
                "bull_collapse_4h_features": ["feat_4h_dist_bb_lower"],
                "stable_4h_features": ["feat_4h_bias200"],
                "profiles": {
                    "core_plus_macro": {"cv_mean_accuracy": 0.73, "cv_worst_accuracy": 0.45},
                    "current_full": {"cv_mean_accuracy": 0.65, "cv_worst_accuracy": 0.44},
                },
            }
        )
    )

    diag = hb_parallel_runner.collect_feature_ablation_diagnostics()

    assert diag["recommended_profile"] == "core_plus_macro"
    assert diag["recommended_metrics"]["cv_mean_accuracy"] == 0.73
    assert diag["current_full_metrics"]["cv_mean_accuracy"] == 0.65
    assert diag["profile_role"]["role"] == "global_shrinkage_winner"
    assert diag["bull_collapse_4h_features"] == ["feat_4h_dist_bb_lower"]


def test_collect_q15_support_audit_diagnostics_reads_support_and_floor_verdicts(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "q15_support_audit.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-15T07:12:00Z",
                "target_col": "simulated_pyramid_win",
                "current_live": {
                    "current_live_structure_bucket": "CAUTION|structure_quality_caution|q15",
                    "current_live_structure_bucket_rows": 0,
                },
                "support_route": {
                    "verdict": "exact_bucket_missing_proxy_reference_only",
                    "deployable": False,
                    "preferred_support_cohort": "bull_live_exact_bucket_proxy",
                },
                "floor_cross_legality": {
                    "verdict": "math_cross_possible_but_illegal_without_exact_support",
                    "legal_to_relax_runtime_gate": False,
                    "best_single_component": "feat_4h_bias50",
                    "remaining_gap_to_floor": 0.0198,
                },
                "next_action": "先補 exact bucket 真樣本。",
            }
        )
    )

    diag = hb_parallel_runner.collect_q15_support_audit_diagnostics()

    assert diag["support_route"]["verdict"] == "exact_bucket_missing_proxy_reference_only"
    assert diag["support_route"]["deployable"] is False
    assert diag["floor_cross_legality"]["verdict"] == "math_cross_possible_but_illegal_without_exact_support"
    assert diag["floor_cross_legality"]["best_single_component"] == "feat_4h_bias50"
    assert diag["next_action"] == "先補 exact bucket 真樣本。"


def test_collect_q15_bucket_root_cause_diagnostics_reads_verdict_and_candidate_patch(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "q15_bucket_root_cause.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-15T08:10:00Z",
                "target_col": "simulated_pyramid_win",
                "current_live": {
                    "structure_bucket": "CAUTION|structure_quality_caution|q15",
                    "structure_quality": 0.2813,
                },
                "exact_live_lane": {
                    "rows": 76,
                    "dominant_neighbor_bucket": "CAUTION|structure_quality_caution|q35",
                    "dominant_neighbor_rows": 76,
                    "near_boundary_rows": 0,
                },
                "verdict": "structure_scoring_gap_not_boundary",
                "candidate_patch_type": "structure_component_scoring",
                "candidate_patch_feature": "feat_4h_dist_bb_lower",
                "candidate_patch": {
                    "feature": "feat_4h_dist_bb_lower",
                    "needed_raw_delta_to_cross_q35": 1.6655,
                },
                "reason": "單純調整 boundary 無法生成 exact rows。",
                "verify_next": "做 structure component counterfactual。",
                "carry_forward": ["先讀 data/q15_bucket_root_cause.json"],
            }
        )
    )

    diag = hb_parallel_runner.collect_q15_bucket_root_cause_diagnostics()

    assert diag["verdict"] == "structure_scoring_gap_not_boundary"
    assert diag["candidate_patch_type"] == "structure_component_scoring"
    assert diag["candidate_patch_feature"] == "feat_4h_dist_bb_lower"
    assert diag["exact_live_lane"]["dominant_neighbor_bucket"] == "CAUTION|structure_quality_caution|q35"
    assert diag["carry_forward"] == ["先讀 data/q15_bucket_root_cause.json"]


def test_collect_q15_boundary_replay_diagnostics_reads_replay_and_counterfactual(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "q15_boundary_replay.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-15T08:12:00Z",
                "target_col": "simulated_pyramid_win",
                "current_live": {"structure_bucket": "CAUTION|structure_quality_caution|q15"},
                "boundary_replay": {
                    "replay_bucket": "CAUTION|structure_quality_caution|q35",
                    "replay_scope_bucket_rows": 76,
                    "generated_rows_via_boundary_only": 2,
                },
                "component_counterfactual": {
                    "verdict": "bucket_proxy_only_not_trade_floor_fix",
                    "allowed_layers_after": 0,
                },
                "verdict": "boundary_relabels_into_existing_q35_support",
                "reason": "mostly relabel",
                "next_action": "keep blocker",
                "verify_next": "check floor",
                "carry_forward": ["先讀 data/q15_boundary_replay.json"],
            }
        )
    )

    diag = hb_parallel_runner.collect_q15_boundary_replay_diagnostics()

    assert diag["verdict"] == "boundary_relabels_into_existing_q35_support"
    assert diag["boundary_replay"]["replay_scope_bucket_rows"] == 76
    assert diag["component_counterfactual"]["verdict"] == "bucket_proxy_only_not_trade_floor_fix"
    assert diag["carry_forward"] == ["先讀 data/q15_boundary_replay.json"]


def test_main_runs_q15_support_audit_after_leaderboard_probe(monkeypatch):
    order = []

    class Args:
        fast = True
        hb = "test"
        no_collect = True
        no_train = True
        no_dw = True

    class FakeExecutor:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def submit(self, fn, task):
            raise AssertionError("submit() should not be called when TASKS is empty in this test")

    def _ok(stdout: str = ""):
        return {"success": True, "returncode": 0, "stdout": stdout, "stderr": ""}

    monkeypatch.setattr(hb_parallel_runner, "TASKS", [])
    monkeypatch.setattr(hb_parallel_runner, "parse_args", lambda argv=None: Args())
    monkeypatch.setattr(hb_parallel_runner, "resolve_run_label", lambda args: "test")
    monkeypatch.setattr(hb_parallel_runner, "run_collect_step", lambda skip=False: {"attempted": False, "success": True, "returncode": 0, "stdout": "", "stderr": ""})
    monkeypatch.setattr(
        hb_parallel_runner,
        "quick_counts",
        lambda: {
            "raw_market_data": 1,
            "features_normalized": 1,
            "labels": 1,
            "simulated_pyramid_win_rate": 0.5,
            "latest_raw_timestamp": "2026-04-15 00:00:00",
            "label_horizons": [],
        },
    )
    monkeypatch.setattr(hb_parallel_runner, "collect_source_blockers", lambda: {"blocked_count": 0, "counts_by_history_class": {}, "blocked_features": []})
    monkeypatch.setattr(hb_parallel_runner, "print_source_blockers", lambda payload: None)
    monkeypatch.setattr(hb_parallel_runner, "refresh_train_prerequisites", lambda needs_train: {})
    monkeypatch.setattr(hb_parallel_runner.concurrent.futures, "ProcessPoolExecutor", FakeExecutor)
    monkeypatch.setattr(hb_parallel_runner.concurrent.futures, "as_completed", lambda future_to_name: [])
    monkeypatch.setattr(hb_parallel_runner, "collect_ic_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_recent_drift_report", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_recent_drift_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_q35_scaling_audit", lambda: order.append("q35") or _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_q35_scaling_audit_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_predict_probe", lambda: order.append("predict_probe") or _ok())
    monkeypatch.setattr(hb_parallel_runner, "_persist_live_predictor_probe", lambda stdout: None)
    monkeypatch.setattr(hb_parallel_runner, "collect_live_predictor_diagnostics", lambda result: {})
    monkeypatch.setattr(hb_parallel_runner, "run_live_decision_quality_drilldown", lambda: order.append("drilldown") or _ok())
    monkeypatch.setattr(hb_parallel_runner, "run_circuit_breaker_audit", lambda run_label: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_circuit_breaker_audit_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_feature_group_ablation", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_feature_ablation_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_bull_4h_pocket_ablation", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_bull_4h_pocket_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_leaderboard_candidate_probe", lambda run_label=None: order.append("leaderboard") or _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_leaderboard_candidate_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_q15_support_audit", lambda: order.append("q15") or _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_q15_support_audit_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_q15_bucket_root_cause", lambda: order.append("q15_root") or _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_q15_bucket_root_cause_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_q15_boundary_replay", lambda: order.append("q15_replay") or _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_q15_boundary_replay_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_auto_propose", lambda run_label=None: _ok())
    monkeypatch.setattr(hb_parallel_runner, "save_summary", lambda *args, **kwargs: ({}, "/tmp/heartbeat_test_summary.json"))

    hb_parallel_runner.main(["--fast", "--hb", "test"])

    assert order == ["q35", "predict_probe", "drilldown", "leaderboard", "q15", "q15_root", "q15_replay"]


def test_write_progress_persists_machine_readable_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))

    progress_path = hb_parallel_runner.write_progress(
        "watchdog",
        "parallel_tasks",
        status="running",
        details={"completed": ["full_ic"], "pending": ["regime_ic"]},
    )

    payload = json.loads(progress_path.read_text())
    assert payload["heartbeat"] == "watchdog"
    assert payload["stage"] == "parallel_tasks"
    assert payload["status"] == "running"
    assert payload["details"]["completed"] == ["full_ic"]
    assert payload["details"]["pending"] == ["regime_ic"]


def test_run_serial_command_uses_global_run_label_for_watchdog(monkeypatch):
    captured = {}

    def _fake_watchdog(cmd, *, timeout=600, extra_env=None, progress=None):
        captured["cmd"] = cmd
        captured["timeout"] = timeout
        captured["extra_env"] = extra_env
        captured["progress"] = progress
        return {"attempted": True, "success": True, "returncode": 0, "stdout": "ok", "stderr": "", "command": cmd}

    monkeypatch.setattr(hb_parallel_runner, "_CURRENT_HEARTBEAT_RUN_LABEL", "hb-watchdog")
    monkeypatch.setattr(hb_parallel_runner, "_CURRENT_HEARTBEAT_FAST_MODE", False)
    monkeypatch.setattr(hb_parallel_runner, "_run_command_with_watchdog", _fake_watchdog)

    result = hb_parallel_runner._run_serial_command(["python", "scripts/recent_drift_report.py"], timeout=321)

    assert result["success"] is True
    assert captured["timeout"] == 321
    assert captured["progress"]["run_label"] == "hb-watchdog"
    assert captured["progress"]["stage"] == "recent_drift_report"
    assert captured["progress"]["details"]["command_kind"] == "serial_command"
    assert captured["progress"]["details"]["timeout_seconds"] == 321
    assert captured["progress"]["details"]["fast_mode_timeout"] is False


def test_run_serial_command_uses_fast_mode_timeout_budget(monkeypatch):
    captured = {}

    def _fake_watchdog(cmd, *, timeout=600, extra_env=None, progress=None):
        captured["cmd"] = cmd
        captured["timeout"] = timeout
        captured["progress"] = progress
        return {"attempted": True, "success": True, "returncode": 0, "stdout": "ok", "stderr": "", "command": cmd}

    monkeypatch.setattr(hb_parallel_runner, "_CURRENT_HEARTBEAT_RUN_LABEL", "hb-fast")
    monkeypatch.setattr(hb_parallel_runner, "_CURRENT_HEARTBEAT_FAST_MODE", True)
    monkeypatch.setattr(hb_parallel_runner, "_run_command_with_watchdog", _fake_watchdog)

    result = hb_parallel_runner._run_serial_command(["python", "scripts/hb_predict_probe.py"])

    assert result["success"] is True
    assert captured["timeout"] == hb_parallel_runner.FAST_SERIAL_TIMEOUTS["hb_predict_probe"]
    assert captured["progress"]["details"]["timeout_seconds"] == hb_parallel_runner.FAST_SERIAL_TIMEOUTS["hb_predict_probe"]
    assert captured["progress"]["details"]["fast_mode_timeout"] is True



def test_run_serial_command_reuses_fresh_fast_artifact(monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "_CURRENT_HEARTBEAT_FAST_MODE", True)
    monkeypatch.setattr(
        hb_parallel_runner,
        "_get_fast_serial_cache_hit",
        lambda command_name: {
            "artifact_path": "/tmp/recent_drift_report.json",
            "reason": "fresh_recent_drift_artifact_reused",
            "details": {"label_rows": 12, "latest_label_timestamp": "2026-04-17 10:00:00"},
        } if command_name == "recent_drift_report" else None,
    )

    result = hb_parallel_runner._run_serial_command(["python", "scripts/recent_drift_report.py"])

    assert result["success"] is True
    assert result["attempted"] is False
    assert result["cached"] is True
    assert result["cache_reason"] == "fresh_recent_drift_artifact_reused"
    assert result["artifact_path"] == "/tmp/recent_drift_report.json"



def test_recent_drift_cache_hit_requires_matching_label_signature(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    artifact_path = data_dir / "recent_drift_report.json"
    script_path = tmp_path / "scripts"
    script_path.mkdir()
    (script_path / "recent_drift_report.py").write_text("# test\n", encoding="utf-8")
    artifact_path.write_text(
        json.dumps(
            {
                "generated_at": "2099-04-17T10:30:00+00:00",
                "source_meta": {
                    "label_rows": 21853,
                    "latest_label_timestamp": "2026-04-17 06:00:00",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        hb_parallel_runner,
        "_current_canonical_label_signature",
        lambda: {"label_rows": 21853, "latest_label_timestamp": "2026-04-17 06:00:00"},
    )

    hit = hb_parallel_runner._recent_drift_cache_hit()

    assert hit is not None
    assert hit["reason"] == "fresh_recent_drift_artifact_reused"
    assert hit["details"]["label_rows"] == 21853

    monkeypatch.setattr(
        hb_parallel_runner,
        "_current_canonical_label_signature",
        lambda: {"label_rows": 21854, "latest_label_timestamp": "2026-04-17 10:00:00"},
    )
    assert hb_parallel_runner._recent_drift_cache_hit() is None



def test_build_serial_result_summary_marks_cached_artifact(tmp_path):
    artifact_path = tmp_path / "data" / "q35_scaling_audit.json"
    artifact_path.parent.mkdir()
    artifact_path.write_text(json.dumps({"generated_at": "2026-04-17T10:30:00+00:00"}), encoding="utf-8")

    summary = hb_parallel_runner._build_serial_result_summary(
        "hb_q35_scaling_audit",
        {
            "attempted": False,
            "success": True,
            "returncode": 0,
            "cached": True,
            "cache_reason": "fresh_q35_scaling_artifact_reused",
            "cache_details": {"current_feature_timestamp": "2026-04-17 10:30:00"},
            "artifact_path": str(artifact_path),
        },
        diagnostics={"generated_at": "2026-04-17T10:30:00+00:00"},
        now=hb_parallel_runner._safe_parse_datetime("2026-04-17T10:31:00+00:00"),
    )

    assert summary["cached"] is True
    assert summary["cache_reason"] == "fresh_q35_scaling_artifact_reused"
    assert summary["cache_details"]["current_feature_timestamp"] == "2026-04-17 10:30:00"
    assert summary["artifact_path"] == str(artifact_path)
    assert summary["fallback_artifact_used"] is False


def test_feature_group_ablation_cache_hit_uses_semantic_label_signature_when_available(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    scripts_dir = tmp_path / "scripts"
    model_dir = tmp_path / "model"
    db_dir = tmp_path / "database"
    for directory in (data_dir, scripts_dir, model_dir, db_dir):
        directory.mkdir(parents=True, exist_ok=True)

    artifact_path = data_dir / "feature_group_ablation.json"
    artifact_path.write_text(
        json.dumps(
            {
                "generated_at": "2099-04-17T10:30:00+00:00",
                "recommended_profile": "core_plus_macro",
                "recent_rows": 5000,
                "source_meta": {
                    "label_rows": 21853,
                    "latest_label_timestamp": "2026-04-17 06:00:00",
                    "horizon_minutes": 1440,
                    "target_col": "simulated_pyramid_win",
                },
            }
        ),
        encoding="utf-8",
    )
    (scripts_dir / "feature_group_ablation.py").write_text("# test\n", encoding="utf-8")
    (model_dir / "train.py").write_text("# test\n", encoding="utf-8")
    (db_dir / "models.py").write_text("# test\n", encoding="utf-8")
    db_path = tmp_path / "poly_trader.db"
    db_path.write_text("db", encoding="utf-8")
    monkeypatch.setattr(hb_parallel_runner, "DB_PATH", str(db_path))
    monkeypatch.setattr(
        hb_parallel_runner,
        "_current_canonical_label_signature",
        lambda: {"label_rows": 21853, "latest_label_timestamp": "2026-04-17 06:00:00"},
    )

    hit = hb_parallel_runner._feature_group_ablation_cache_hit()

    assert hit is not None
    assert hit["reason"] == "fresh_feature_group_ablation_artifact_reused"
    assert hit["details"]["recommended_profile"] == "core_plus_macro"
    assert hit["details"]["source_meta"]["label_rows"] == 21853

    os.utime(db_path, (4102440000, 4102440000))
    hit_after_db_touch = hb_parallel_runner._feature_group_ablation_cache_hit()
    assert hit_after_db_touch is not None
    assert hit_after_db_touch["details"]["recommended_profile"] == "core_plus_macro"

    monkeypatch.setattr(
        hb_parallel_runner,
        "_current_canonical_label_signature",
        lambda: {"label_rows": 21855, "latest_label_timestamp": "2026-04-17 07:30:00"},
    )
    bounded_hit = hb_parallel_runner._feature_group_ablation_cache_hit()
    assert bounded_hit is not None
    assert bounded_hit["reason"] == "bounded_label_drift_feature_group_ablation_artifact_reused"
    assert bounded_hit["details"]["label_drift"]["row_delta"] == 2

    monkeypatch.setattr(
        hb_parallel_runner,
        "_current_canonical_label_signature",
        lambda: {"label_rows": 21870, "latest_label_timestamp": "2026-04-17 14:30:00"},
    )
    assert hb_parallel_runner._feature_group_ablation_cache_hit() is None


def test_bull_4h_pocket_cache_hit_reuses_semantic_match_with_bounded_label_drift(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    scripts_dir = tmp_path / "scripts"
    model_dir = tmp_path / "model"
    for directory in (data_dir, scripts_dir, model_dir):
        directory.mkdir(parents=True, exist_ok=True)

    artifact_path = data_dir / "bull_4h_pocket_ablation.json"
    artifact_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-17T10:30:00+00:00",
                "source_meta": {
                    "label_rows": 21913,
                    "latest_label_timestamp": "2026-04-17 04:05:06",
                    "horizon_minutes": 1440,
                    "target_col": "simulated_pyramid_win",
                },
                "live_context": {
                    "regime_label": "bull",
                    "regime_gate": "CAUTION",
                    "entry_quality_label": "C",
                    "decision_quality_label": "D",
                    "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "current_live_structure_bucket_rows": 0,
                    "exact_scope_rows": 0,
                    "execution_guardrail_reason": "decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket",
                    "decision_quality_calibration_scope": "regime_label",
                },
            }
        ),
        encoding="utf-8",
    )
    dep_mtime = 1713344400
    for dep_path in [
        scripts_dir / "bull_4h_pocket_ablation.py",
        scripts_dir / "feature_group_ablation.py",
        model_dir / "predictor.py",
        model_dir / "train.py",
    ]:
        dep_path.write_text("# test\n", encoding="utf-8")
        os.utime(dep_path, (dep_mtime, dep_mtime))

    live_probe_path = data_dir / "live_predict_probe.json"
    live_probe_path.write_text(
        json.dumps(
            {
                "regime_label": "bull",
                "regime_gate": "CAUTION",
                "entry_quality_label": "B",
                "decision_quality_label": "D",
                "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                "current_live_structure_bucket_rows": 0,
                "execution_guardrail_reason": "decision_quality_below_trade_floor; unsupported_exact_live_structure_bucket",
                "decision_quality_calibration_scope": "regime_label",
                "decision_quality_scope_diagnostics": {
                    "regime_label+regime_gate+entry_quality_label": {"rows": 0}
                },
            }
        ),
        encoding="utf-8",
    )
    os.utime(live_probe_path, (4102440000, 4102440000))

    monkeypatch.setattr(
        hb_parallel_runner,
        "_current_canonical_label_signature",
        lambda: {"label_rows": 21915, "latest_label_timestamp": "2026-04-17 05:00:00"},
    )

    hit = hb_parallel_runner._bull_4h_pocket_cache_hit()

    assert hit is not None
    assert hit["reason"] == "bounded_label_drift_bull_4h_pocket_artifact_reused"
    assert hit["details"]["semantic_signature"]["current_live_structure_bucket"] == "CAUTION|structure_quality_caution|q35"
    assert hit["details"]["label_drift"]["row_delta"] == 2

    live_probe_path.write_text(
        json.dumps(
            {
                "regime_label": "bull",
                "regime_gate": "ALLOW",
                "entry_quality_label": "C",
                "decision_quality_label": "D",
                "current_live_structure_bucket": "ALLOW|base_allow|q65",
                "current_live_structure_bucket_rows": 0,
                "execution_guardrail_reason": "unsupported_exact_live_structure_bucket",
                "decision_quality_calibration_scope": "regime_label",
                "decision_quality_scope_diagnostics": {
                    "regime_label+regime_gate+entry_quality_label": {"rows": 0}
                },
            }
        ),
        encoding="utf-8",
    )
    assert hb_parallel_runner._bull_4h_pocket_cache_hit() is None


def test_leaderboard_candidate_cache_hit_uses_semantic_alignment_signature(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    scripts_dir = tmp_path / "scripts"
    model_dir = tmp_path / "model"
    server_routes_dir = tmp_path / "server" / "routes"
    backtesting_dir = tmp_path / "backtesting"
    for directory in (data_dir, scripts_dir, model_dir, server_routes_dir, backtesting_dir):
        directory.mkdir(parents=True, exist_ok=True)

    artifact_path = data_dir / "leaderboard_feature_profile_probe.json"
    artifact_path.write_text(
        json.dumps(
            {
                "generated_at": "2099-04-17T10:30:00+00:00",
                "top_model": {"selected_feature_profile": "core_only"},
                "alignment": {
                    "current_alignment_inputs_stale": False,
                    "global_recommended_profile": "core_only",
                    "train_selected_profile": "core_plus_macro",
                    "train_selected_profile_source": "bull_4h_pocket_ablation.support_aware_profile",
                    "support_governance_route": "no_support_proxy",
                    "minimum_support_rows": 50,
                    "live_current_structure_bucket": None,
                    "live_current_structure_bucket_rows": 0,
                    "live_execution_guardrail_reason": "circuit_breaker_blocks_trade",
                    "live_regime_gate": None,
                    "live_entry_quality_label": None,
                },
            }
        ),
        encoding="utf-8",
    )

    (scripts_dir / "hb_leaderboard_candidate_probe.py").write_text("# test\n", encoding="utf-8")
    (server_routes_dir / "api.py").write_text("# test\n", encoding="utf-8")
    (backtesting_dir / "model_leaderboard.py").write_text("# test\n", encoding="utf-8")
    (model_dir / "last_metrics.json").write_text(
        json.dumps(
            {
                "feature_profile": "core_plus_macro",
                "feature_profile_source": "bull_4h_pocket_ablation.support_aware_profile",
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "feature_group_ablation.json").write_text(
        json.dumps({"recommended_profile": "core_only", "generated_at": "2099-04-17T10:29:00+00:00"}),
        encoding="utf-8",
    )
    (data_dir / "bull_4h_pocket_ablation.json").write_text(
        json.dumps(
            {
                "generated_at": "2099-04-17T10:29:00+00:00",
                "live_context": {
                    "current_live_structure_bucket": None,
                    "current_live_structure_bucket_rows": 0,
                    "minimum_support_rows": 50,
                },
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "q15_support_audit.json").write_text(
        json.dumps(
            {
                "generated_at": "2099-04-17T10:29:00+00:00",
                "support_route": {
                    "support_governance_route": "no_support_proxy",
                    "minimum_support_rows": 50,
                },
                "current_live": {
                    "current_live_structure_bucket": None,
                    "current_live_structure_bucket_rows": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "live_predict_probe.json").write_text(
        json.dumps(
            {
                "generated_at": "2099-04-17T10:29:00+00:00",
                "execution_guardrail_reason": "circuit_breaker_blocks_trade",
                "regime_gate": None,
                "entry_quality_label": None,
            }
        ),
        encoding="utf-8",
    )

    newer = 4102440000
    for dep in [
        data_dir / "feature_group_ablation.json",
        data_dir / "bull_4h_pocket_ablation.json",
        data_dir / "q15_support_audit.json",
        data_dir / "live_predict_probe.json",
        model_dir / "last_metrics.json",
    ]:
        os.utime(dep, (newer, newer))

    hit = hb_parallel_runner._leaderboard_candidate_cache_hit()

    assert hit is not None
    assert hit["reason"] == "fresh_leaderboard_candidate_artifact_reused"
    assert hit["details"]["selected_feature_profile"] == "core_only"


def test_leaderboard_candidate_cache_hit_refreshes_semantic_drift_when_probe_artifact_can_be_realigned(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    scripts_dir = tmp_path / "scripts"
    model_dir = tmp_path / "model"
    server_routes_dir = tmp_path / "server" / "routes"
    backtesting_dir = tmp_path / "backtesting"
    for directory in (data_dir, scripts_dir, model_dir, server_routes_dir, backtesting_dir):
        directory.mkdir(parents=True, exist_ok=True)

    artifact_path = data_dir / "leaderboard_feature_profile_probe.json"
    artifact_path.write_text(
        json.dumps(
            {
                "generated_at": "2099-04-17T10:30:00+00:00",
                "top_model": {"selected_feature_profile": "core_only"},
                "alignment": {
                    "current_alignment_inputs_stale": False,
                    "global_recommended_profile": "core_only",
                    "train_selected_profile": "core_plus_macro",
                    "train_selected_profile_source": "bull_4h_pocket_ablation.support_aware_profile",
                    "support_governance_route": "exact_live_bucket_present_but_below_minimum",
                    "minimum_support_rows": 50,
                    "live_current_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "live_current_structure_bucket_rows": 9,
                    "live_execution_guardrail_reason": "unsupported_exact_live_structure_bucket",
                    "live_regime_gate": "CAUTION",
                    "live_entry_quality_label": "C",
                },
            }
        ),
        encoding="utf-8",
    )

    (scripts_dir / "hb_leaderboard_candidate_probe.py").write_text("# test\n", encoding="utf-8")
    (server_routes_dir / "api.py").write_text("# test\n", encoding="utf-8")
    (backtesting_dir / "model_leaderboard.py").write_text("# test\n", encoding="utf-8")
    (model_dir / "last_metrics.json").write_text(
        json.dumps(
            {
                "feature_profile": "core_plus_macro",
                "feature_profile_source": "bull_4h_pocket_ablation.support_aware_profile",
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "feature_group_ablation.json").write_text(
        json.dumps({"recommended_profile": "core_only", "generated_at": "2099-04-17T10:29:00+00:00"}),
        encoding="utf-8",
    )
    (data_dir / "bull_4h_pocket_ablation.json").write_text(
        json.dumps(
            {
                "generated_at": "2099-04-17T10:29:00+00:00",
                "live_context": {
                    "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "current_live_structure_bucket_rows": 0,
                    "minimum_support_rows": 50,
                },
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "q15_support_audit.json").write_text(
        json.dumps(
            {
                "support_route": {
                    "support_governance_route": "exact_live_bucket_present_but_below_minimum",
                    "minimum_support_rows": 50,
                },
                "current_live": {
                    "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "current_live_structure_bucket_rows": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "live_predict_probe.json").write_text(
        json.dumps(
            {
                "execution_guardrail_reason": "unsupported_exact_live_structure_bucket",
                "regime_gate": "CAUTION",
                "entry_quality_label": "C",
            }
        ),
        encoding="utf-8",
    )

    def _fake_refresh(path):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["generated_at"] = "2099-04-17T10:35:00+00:00"
        payload["leaderboard_payload_source"] = "latest_persisted_snapshot"
        payload["alignment"] = {
            **payload["alignment"],
            "live_current_structure_bucket_rows": 0,
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        fresh = 4102440000
        os.utime(path, (fresh, fresh))
        return payload

    monkeypatch.setattr(hb_parallel_runner, "_refresh_leaderboard_candidate_alignment_snapshot", _fake_refresh)

    hit = hb_parallel_runner._leaderboard_candidate_cache_hit()

    assert hit is not None
    assert hit["reason"] == "refreshed_leaderboard_candidate_artifact_reused"
    assert hit["details"]["refresh_applied"] is True
    assert hit["details"]["semantic_signature"]["live_current_structure_bucket_rows"] == 0
    assert hit["details"]["leaderboard_payload_source"] == "latest_persisted_snapshot"



def test_refresh_leaderboard_candidate_alignment_snapshot_uses_rebuild_path(tmp_path, monkeypatch):
    artifact_path = tmp_path / "leaderboard_feature_profile_probe.json"
    artifact_path.write_text(
        json.dumps({"top_model": {"selected_feature_profile": "core_only"}}),
        encoding="utf-8",
    )

    import scripts.hb_leaderboard_candidate_probe as real_probe

    called = {}

    def _fake_build_probe_result(*, allow_rebuild=True, generated_at=None):
        called["allow_rebuild"] = allow_rebuild
        return {
            "generated_at": "2026-04-19T02:30:05Z",
            "top_model": {"selected_feature_profile": "core_plus_macro"},
            "alignment": {"selected_feature_profile": "core_plus_macro"},
        }

    monkeypatch.setattr(real_probe, "build_probe_result", _fake_build_probe_result)

    refreshed = hb_parallel_runner._refresh_leaderboard_candidate_alignment_snapshot(artifact_path)

    assert called["allow_rebuild"] is True
    assert refreshed["top_model"]["selected_feature_profile"] == "core_plus_macro"
    saved = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert saved["top_model"]["selected_feature_profile"] == "core_plus_macro"



def test_leaderboard_candidate_cache_hit_refreshes_alignment_snapshot_when_only_code_freshness_is_stale(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    scripts_dir = tmp_path / "scripts"
    model_dir = tmp_path / "model"
    server_routes_dir = tmp_path / "server" / "routes"
    backtesting_dir = tmp_path / "backtesting"
    for directory in (data_dir, scripts_dir, model_dir, server_routes_dir, backtesting_dir):
        directory.mkdir(parents=True, exist_ok=True)

    artifact_path = data_dir / "leaderboard_feature_profile_probe.json"
    artifact_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-17T07:11:11Z",
                "top_model": {"selected_feature_profile": "core_only"},
                "alignment": {
                    "current_alignment_inputs_stale": False,
                    "global_recommended_profile": "core_only",
                    "train_selected_profile": "core_plus_macro",
                    "train_selected_profile_source": "bull_4h_pocket_ablation.support_aware_profile",
                    "support_governance_route": "no_support_proxy",
                    "minimum_support_rows": 50,
                    "live_current_structure_bucket": None,
                    "live_current_structure_bucket_rows": 0,
                    "live_execution_guardrail_reason": "circuit_breaker_blocks_trade",
                    "live_regime_gate": None,
                    "live_entry_quality_label": None,
                },
            }
        ),
        encoding="utf-8",
    )

    (scripts_dir / "hb_leaderboard_candidate_probe.py").write_text("# stale dep\n", encoding="utf-8")
    (server_routes_dir / "api.py").write_text("# stale dep\n", encoding="utf-8")
    (backtesting_dir / "model_leaderboard.py").write_text("# stale dep\n", encoding="utf-8")
    (model_dir / "last_metrics.json").write_text(
        json.dumps(
            {
                "feature_profile": "core_plus_macro",
                "feature_profile_source": "bull_4h_pocket_ablation.support_aware_profile",
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "feature_group_ablation.json").write_text(
        json.dumps({"recommended_profile": "core_only", "generated_at": "2026-04-17T07:10:00Z"}),
        encoding="utf-8",
    )
    (data_dir / "bull_4h_pocket_ablation.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-17T07:10:00Z",
                "live_context": {
                    "current_live_structure_bucket": None,
                    "current_live_structure_bucket_rows": 0,
                    "minimum_support_rows": 50,
                },
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "q15_support_audit.json").write_text(
        json.dumps(
            {
                "support_route": {
                    "support_governance_route": "no_support_proxy",
                    "minimum_support_rows": 50,
                },
                "current_live": {
                    "current_live_structure_bucket": None,
                    "current_live_structure_bucket_rows": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "live_predict_probe.json").write_text(
        json.dumps(
            {
                "execution_guardrail_reason": "circuit_breaker_blocks_trade",
                "regime_gate": None,
                "entry_quality_label": None,
            }
        ),
        encoding="utf-8",
    )

    def _fake_refresh(path):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["generated_at"] = "2099-04-17T10:35:00+00:00"
        path.write_text(json.dumps(payload), encoding="utf-8")
        fresh = 4102440000
        os.utime(path, (fresh, fresh))
        return payload

    monkeypatch.setattr(hb_parallel_runner, "_refresh_leaderboard_candidate_alignment_snapshot", _fake_refresh)

    hit = hb_parallel_runner._leaderboard_candidate_cache_hit()

    assert hit is not None
    assert hit["reason"] == "refreshed_leaderboard_candidate_artifact_reused"
    assert hit["details"]["refresh_applied"] is True
    assert hit["details"]["generated_at"] == "2099-04-17T10:35:00+00:00"


def test_leaderboard_candidate_cache_hit_rejects_semantic_drift(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    scripts_dir = tmp_path / "scripts"
    model_dir = tmp_path / "model"
    server_routes_dir = tmp_path / "server" / "routes"
    backtesting_dir = tmp_path / "backtesting"
    for directory in (data_dir, scripts_dir, model_dir, server_routes_dir, backtesting_dir):
        directory.mkdir(parents=True, exist_ok=True)

    (data_dir / "leaderboard_feature_profile_probe.json").write_text(
        json.dumps(
            {
                "generated_at": "2099-04-17T10:30:00+00:00",
                "top_model": {"selected_feature_profile": "core_only"},
                "alignment": {
                    "current_alignment_inputs_stale": False,
                    "global_recommended_profile": "core_only",
                    "train_selected_profile": "core_plus_macro",
                    "train_selected_profile_source": "bull_4h_pocket_ablation.support_aware_profile",
                    "support_governance_route": "no_support_proxy",
                    "minimum_support_rows": 50,
                    "live_current_structure_bucket": None,
                    "live_current_structure_bucket_rows": 0,
                    "live_execution_guardrail_reason": "circuit_breaker_blocks_trade",
                    "live_regime_gate": None,
                    "live_entry_quality_label": None,
                },
            }
        ),
        encoding="utf-8",
    )
    (scripts_dir / "hb_leaderboard_candidate_probe.py").write_text("# test\n", encoding="utf-8")
    (server_routes_dir / "api.py").write_text("# test\n", encoding="utf-8")
    (backtesting_dir / "model_leaderboard.py").write_text("# test\n", encoding="utf-8")
    (model_dir / "last_metrics.json").write_text(
        json.dumps({"feature_profile": "core_plus_macro", "feature_profile_source": "bull_4h_pocket_ablation.support_aware_profile"}),
        encoding="utf-8",
    )
    (data_dir / "feature_group_ablation.json").write_text(json.dumps({"recommended_profile": "core_only"}), encoding="utf-8")
    (data_dir / "bull_4h_pocket_ablation.json").write_text(
        json.dumps({"live_context": {"current_live_structure_bucket": None, "current_live_structure_bucket_rows": 0, "minimum_support_rows": 50}}),
        encoding="utf-8",
    )
    (data_dir / "q15_support_audit.json").write_text(
        json.dumps({"support_route": {"support_governance_route": "no_support_proxy", "minimum_support_rows": 50}, "current_live": {"current_live_structure_bucket": None, "current_live_structure_bucket_rows": 0}}),
        encoding="utf-8",
    )
    (data_dir / "live_predict_probe.json").write_text(
        json.dumps({"execution_guardrail_reason": "entry_quality_below_trade_floor", "regime_gate": None, "entry_quality_label": None}),
        encoding="utf-8",
    )

    assert hb_parallel_runner._leaderboard_candidate_cache_hit() is None


def test_q15_support_cache_hit_tracks_artifact_dependencies(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    scripts_dir = tmp_path / "scripts"
    data_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = data_dir / "q15_support_audit.json"
    artifact_path.write_text(
        json.dumps(
            {
                "generated_at": "2099-04-17T10:30:00+00:00",
                "current_live": {"current_live_structure_bucket": "CAUTION|structure_quality_caution|q15"},
                "support_route": {"verdict": "under_minimum_exact_live_structure_bucket"},
            }
        ),
        encoding="utf-8",
    )
    (scripts_dir / "hb_q15_support_audit.py").write_text("# test\n", encoding="utf-8")
    for name in [
        "live_predict_probe.json",
        "live_decision_quality_drilldown.json",
        "bull_4h_pocket_ablation.json",
        "leaderboard_feature_profile_probe.json",
    ]:
        (data_dir / name).write_text("{}", encoding="utf-8")

    hit = hb_parallel_runner._q15_support_cache_hit()

    assert hit is not None
    assert hit["reason"] == "fresh_q15_support_artifact_reused"
    assert hit["details"]["support_route_verdict"] == "under_minimum_exact_live_structure_bucket"

    dep = data_dir / "live_predict_probe.json"
    os.utime(dep, (4102440000, 4102440000))
    assert hb_parallel_runner._q15_support_cache_hit() is None


def test_get_fast_serial_cache_hit_dispatches_new_governance_artifacts(monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "_CURRENT_HEARTBEAT_FAST_MODE", True)
    monkeypatch.setattr(hb_parallel_runner, "_feature_group_ablation_cache_hit", lambda: {"artifact_path": "fg.json", "reason": "fg", "details": {}})
    monkeypatch.setattr(hb_parallel_runner, "_bull_4h_pocket_cache_hit", lambda: {"artifact_path": "bull.json", "reason": "bull", "details": {}})
    monkeypatch.setattr(hb_parallel_runner, "_q15_support_cache_hit", lambda: {"artifact_path": "q15.json", "reason": "q15", "details": {}})
    monkeypatch.setattr(hb_parallel_runner, "_q15_bucket_root_cause_cache_hit", lambda: {"artifact_path": "root.json", "reason": "root", "details": {}})
    monkeypatch.setattr(hb_parallel_runner, "_q15_boundary_replay_cache_hit", lambda: {"artifact_path": "replay.json", "reason": "replay", "details": {}})

    assert hb_parallel_runner._get_fast_serial_cache_hit("feature_group_ablation")["reason"] == "fg"
    assert hb_parallel_runner._get_fast_serial_cache_hit("bull_4h_pocket_ablation")["reason"] == "bull"
    assert hb_parallel_runner._get_fast_serial_cache_hit("hb_q15_support_audit")["reason"] == "q15"
    assert hb_parallel_runner._get_fast_serial_cache_hit("hb_q15_bucket_root_cause")["reason"] == "root"
    assert hb_parallel_runner._get_fast_serial_cache_hit("hb_q15_boundary_replay")["reason"] == "replay"


def test_main_writes_final_progress_artifact(tmp_path, monkeypatch):
    class Args:
        fast = True
        hb = "progress"
        no_collect = True
        no_train = True
        no_dw = True

    class FakeExecutor:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def submit(self, fn, task):
            raise AssertionError("submit() should not be called when TASKS is empty in this test")

    def _ok(stdout: str = ""):
        return {"success": True, "returncode": 0, "stdout": stdout, "stderr": ""}

    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(hb_parallel_runner, "TASKS", [])
    monkeypatch.setattr(hb_parallel_runner, "parse_args", lambda argv=None: Args())
    monkeypatch.setattr(hb_parallel_runner, "resolve_run_label", lambda args: "progress")
    monkeypatch.setattr(hb_parallel_runner, "run_collect_step", lambda skip=False: {"attempted": False, "success": True, "returncode": 0, "stdout": "", "stderr": ""})
    monkeypatch.setattr(
        hb_parallel_runner,
        "quick_counts",
        lambda: {
            "raw_market_data": 1,
            "features_normalized": 1,
            "labels": 1,
            "simulated_pyramid_win_rate": 0.5,
            "latest_raw_timestamp": "2026-04-15 00:00:00",
            "label_horizons": [],
        },
    )
    monkeypatch.setattr(hb_parallel_runner, "collect_source_blockers", lambda: {"blocked_count": 0, "counts_by_history_class": {}, "blocked_features": []})
    monkeypatch.setattr(hb_parallel_runner, "print_source_blockers", lambda payload: None)
    monkeypatch.setattr(hb_parallel_runner, "refresh_train_prerequisites", lambda needs_train: {})
    monkeypatch.setattr(hb_parallel_runner.concurrent.futures, "ProcessPoolExecutor", FakeExecutor)
    monkeypatch.setattr(hb_parallel_runner.concurrent.futures, "as_completed", lambda future_to_name: [])
    monkeypatch.setattr(hb_parallel_runner, "collect_ic_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_recent_drift_report", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_recent_drift_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_q35_scaling_audit", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_q35_scaling_audit_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_predict_probe", lambda: _ok("{}"))
    monkeypatch.setattr(hb_parallel_runner, "_persist_live_predictor_probe", lambda stdout: None)
    monkeypatch.setattr(hb_parallel_runner, "collect_live_predictor_diagnostics", lambda result: {})
    monkeypatch.setattr(hb_parallel_runner, "run_live_decision_quality_drilldown", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "run_circuit_breaker_audit", lambda run_label: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_circuit_breaker_audit_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_leaderboard_candidate_probe", lambda run_label=None: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_leaderboard_candidate_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_q15_support_audit", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_q15_support_audit_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_q15_bucket_root_cause", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_q15_bucket_root_cause_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_q15_boundary_replay", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_q15_boundary_replay_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_auto_propose", lambda run_label=None: _ok())

    hb_parallel_runner.main(["--fast", "--hb", "progress"])

    progress_path = tmp_path / "data" / "heartbeat_progress_progress.json"
    summary_path = tmp_path / "data" / "heartbeat_progress_summary.json"
    progress = json.loads(progress_path.read_text())
    summary = json.loads(summary_path.read_text())

    assert progress["stage"] == "finished"
    assert progress["status"] == "success"
    assert progress["details"]["summary_path"] == str(summary_path)
    assert summary["runtime_progress"]["path"] == str(progress_path)
    assert summary["runtime_progress"]["snapshot"]["stage"] == "auto_propose"



def test_main_parallel_watchdog_writes_pending_tasks_to_progress(tmp_path, monkeypatch):
    class Args:
        fast = True
        hb = "watchdog"
        no_collect = True
        no_train = True
        no_dw = True

    class FakeFuture:
        def __init__(self, payload):
            self._payload = payload

        def result(self):
            return self._payload

    class FakeExecutor:
        def __init__(self, *args, **kwargs):
            self.future = FakeFuture(("full_ic", True, "ok", ""))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def submit(self, fn, task):
            return self.future

    def _ok(stdout: str = ""):
        return {"success": True, "returncode": 0, "stdout": stdout, "stderr": ""}

    wait_calls = {"count": 0}

    def _fake_wait(pending, timeout=None, return_when=None):
        wait_calls["count"] += 1
        if wait_calls["count"] == 1:
            return set(), set(pending)
        return set(pending), set()

    watchdog_snapshots = []
    original_write_progress = hb_parallel_runner.write_progress

    def _capturing_write_progress(*args, **kwargs):
        path = original_write_progress(*args, **kwargs)
        if len(args) >= 2 and args[1] == "parallel_tasks":
            payload = json.loads(Path(path).read_text())
            if (payload.get("details") or {}).get("watchdog"):
                watchdog_snapshots.append(payload)
        return path

    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(hb_parallel_runner, "write_progress", _capturing_write_progress)
    monkeypatch.setattr(hb_parallel_runner, "TASKS", [{"name": "full_ic", "label": "Full IC", "cmd": ["python", "scripts/full_ic.py"]}])
    monkeypatch.setattr(hb_parallel_runner, "parse_args", lambda argv=None: Args())
    monkeypatch.setattr(hb_parallel_runner, "resolve_run_label", lambda args: "watchdog")
    monkeypatch.setattr(hb_parallel_runner, "run_collect_step", lambda skip=False: {"attempted": False, "success": True, "returncode": 0, "stdout": "", "stderr": ""})
    monkeypatch.setattr(
        hb_parallel_runner,
        "quick_counts",
        lambda: {
            "raw_market_data": 1,
            "features_normalized": 1,
            "labels": 1,
            "simulated_pyramid_win_rate": 0.5,
            "latest_raw_timestamp": "2026-04-15 00:00:00",
            "label_horizons": [],
        },
    )
    monkeypatch.setattr(hb_parallel_runner, "collect_source_blockers", lambda: {"blocked_count": 0, "counts_by_history_class": {}, "blocked_features": []})
    monkeypatch.setattr(hb_parallel_runner, "print_source_blockers", lambda payload: None)
    monkeypatch.setattr(hb_parallel_runner, "refresh_train_prerequisites", lambda needs_train: {})
    monkeypatch.setattr(hb_parallel_runner.concurrent.futures, "ProcessPoolExecutor", FakeExecutor)
    monkeypatch.setattr(hb_parallel_runner.concurrent.futures, "wait", _fake_wait)
    monkeypatch.setattr(hb_parallel_runner, "collect_ic_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_recent_drift_report", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_recent_drift_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_q35_scaling_audit", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_q35_scaling_audit_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_predict_probe", lambda: _ok("{}"))
    monkeypatch.setattr(hb_parallel_runner, "_persist_live_predictor_probe", lambda stdout: None)
    monkeypatch.setattr(hb_parallel_runner, "collect_live_predictor_diagnostics", lambda result: {})
    monkeypatch.setattr(hb_parallel_runner, "run_live_decision_quality_drilldown", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "run_circuit_breaker_audit", lambda run_label: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_circuit_breaker_audit_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_feature_group_ablation", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_feature_ablation_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_bull_4h_pocket_ablation", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_bull_4h_pocket_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_leaderboard_candidate_probe", lambda run_label=None: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_leaderboard_candidate_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_q15_support_audit", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_q15_support_audit_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_q15_bucket_root_cause", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_q15_bucket_root_cause_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_q15_boundary_replay", lambda: _ok())
    monkeypatch.setattr(hb_parallel_runner, "collect_q15_boundary_replay_diagnostics", lambda: {})
    monkeypatch.setattr(hb_parallel_runner, "run_auto_propose", lambda run_label=None: _ok())

    hb_parallel_runner.main(["--fast", "--hb", "watchdog"])

    assert watchdog_snapshots, "expected at least one parallel watchdog snapshot"
    watchdog = watchdog_snapshots[0]["details"]["watchdog"]
    assert watchdog["heartbeat_count"] == 1
    assert watchdog["pending_tasks"] == ["full_ic"]



def test_collect_bull_4h_pocket_diagnostics_reads_live_bucket_support(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "bull_4h_pocket_ablation.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-14 10:05:00",
                "target_col": "simulated_pyramid_win",
                "collapse_features": ["feat_4h_dist_bb_lower"],
                "collapse_thresholds": {"feat_4h_dist_bb_lower": 0.43},
                "live_context": {
                    "regime_label": "bull",
                    "regime_gate": "CAUTION",
                    "entry_quality_label": "D",
                    "current_live_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "current_live_structure_bucket_rows": 0,
                    "supported_neighbor_buckets": ["CAUTION|base_caution_regime_or_bias|q15"],
                },
                "support_pathology_summary": {
                    "blocker_state": "exact_lane_proxy_fallback_only",
                    "preferred_support_cohort": "bull_exact_live_lane_proxy",
                    "minimum_support_rows": 50,
                    "current_live_structure_bucket_gap_to_minimum": 50,
                    "exact_bucket_root_cause": "same_lane_exists_but_q35_missing",
                    "bucket_comparison_takeaway": "neighbor_bucket_outperforms_broader_same_bucket",
                    "proxy_boundary_verdict": "proxy_too_wide_vs_exact_bucket",
                    "proxy_boundary_reason": "proxy 與 recent exact bucket 差距過大",
                    "proxy_boundary_diagnostics": {
                        "recent_exact_current_bucket": {"rows": 5, "win_rate": 0.4},
                        "historical_exact_bucket_proxy": {"rows": 8, "win_rate": 0.8},
                    },
                    "bucket_evidence_comparison": {
                        "current_live_bucket": "CAUTION|structure_quality_caution|q35",
                        "exact_live_lane": {"bucket": "CAUTION|base_caution_regime_or_bias|q15", "rows": 25},
                        "exact_bucket_proxy": {"bucket": "CAUTION|structure_quality_caution|q35", "rows": 8},
                        "broader_same_bucket": {"bucket": "CAUTION|structure_quality_caution|q35", "rows": 61},
                    },
                    "exact_lane_bucket_verdict": "toxic_sub_bucket_identified",
                    "exact_lane_bucket_reason": "q15 子 bucket 明顯拖累 exact lane",
                    "exact_lane_toxic_bucket": {
                        "bucket": "CAUTION|base_caution_regime_or_bias|q15",
                        "rows": 7,
                        "win_rate": 0.1429,
                        "vs_current_bucket": {"win_rate_delta": -0.6571},
                    },
                    "exact_lane_bucket_diagnostics": {
                        "verdict": "toxic_sub_bucket_identified",
                        "buckets": {
                            "CAUTION|structure_quality_caution|q35": {"rows": 5, "win_rate": 0.8},
                            "CAUTION|base_caution_regime_or_bias|q15": {"rows": 7, "win_rate": 0.1429},
                        },
                    },
                    "recommended_action": "維持 blocker",
                },
                "cohorts": {
                    "bull_all": {"rows": 100, "base_win_rate": 0.67, "recommended_profile": "core_plus_macro_plus_all_4h", "profiles": {"core_plus_macro_plus_all_4h": {"cv_mean_accuracy": 0.64}}},
                    "bull_collapse_q35": {"rows": 40, "base_win_rate": 0.51, "recommended_profile": "core_plus_macro", "profiles": {"core_plus_macro": {"cv_mean_accuracy": 0.70}}},
                    "bull_exact_live_lane_proxy": {"rows": 25, "base_win_rate": 0.79, "recommended_profile": "core_plus_macro", "profiles": {"core_plus_macro": {"cv_mean_accuracy": 0.81}}},
                    "bull_live_exact_lane_bucket_proxy": {"rows": 8, "base_win_rate": 0.50, "recommended_profile": "core_plus_macro", "profiles": {"core_plus_macro": {"cv_mean_accuracy": 0.62}}},
                    "bull_supported_neighbor_buckets_proxy": {"rows": 20, "base_win_rate": 0.69, "recommended_profile": "core_plus_macro", "profiles": {"core_plus_macro": {"cv_mean_accuracy": 0.73}}},
                },
            }
        )
    )

    diag = hb_parallel_runner.collect_bull_4h_pocket_diagnostics()

    assert diag["live_context"]["current_live_structure_bucket_rows"] == 0
    assert diag["live_context"]["supported_neighbor_buckets"] == ["CAUTION|base_caution_regime_or_bias|q15"]
    assert diag["support_pathology_summary"]["exact_bucket_root_cause"] == "same_lane_exists_but_q35_missing"
    assert diag["support_pathology_summary"]["bucket_comparison_takeaway"] == "neighbor_bucket_outperforms_broader_same_bucket"
    assert diag["support_pathology_summary"]["proxy_boundary_verdict"] == "proxy_too_wide_vs_exact_bucket"
    assert diag["support_pathology_summary"]["proxy_boundary_diagnostics"]["recent_exact_current_bucket"]["rows"] == 5
    assert diag["support_pathology_summary"]["bucket_evidence_comparison"]["broader_same_bucket"]["rows"] == 61
    assert diag["support_pathology_summary"]["exact_lane_bucket_verdict"] == "toxic_sub_bucket_identified"
    assert diag["support_pathology_summary"]["exact_lane_toxic_bucket"]["bucket"] == "CAUTION|base_caution_regime_or_bias|q15"
    assert diag["support_pathology_summary"]["exact_lane_bucket_diagnostics"]["buckets"]["CAUTION|base_caution_regime_or_bias|q15"]["rows"] == 7
    assert diag["production_profile_role"]["role"] == "support_aware_production_profile"
    assert diag["bull_all"]["recommended_profile"] == "core_plus_macro_plus_all_4h"
    assert diag["bull_collapse_q35"]["recommended_profile"] == "core_plus_macro"
    assert diag["bull_live_exact_lane_bucket_proxy"]["rows"] == 8


def test_collect_leaderboard_candidate_diagnostics_reads_dual_profile_state(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "leaderboard_feature_profile_probe.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-14T12:40:00Z",
                "target_col": "simulated_pyramid_win",
                "leaderboard_count": 8,
                "top_model": {
                    "selected_feature_profile": "core_only",
                    "selected_feature_profile_source": "feature_group_ablation.recommended_profile",
                    "selected_feature_profile_blocker_applied": False,
                    "selected_feature_profile_blocker_reason": None,
                },
                "leaderboard_snapshot_created_at": "2026-04-14T06:51:24Z",
                "leaderboard_payload_source": "latest_persisted_snapshot",
                "leaderboard_payload_updated_at": "2026-04-14T12:39:00Z",
                "leaderboard_payload_cache_age_sec": 120,
                "leaderboard_payload_stale": False,
                "alignment": {
                    "dual_profile_state": "leaderboard_global_winner_vs_train_support_fallback",
                    "profile_split": {
                        "global_profile": "core_only",
                        "production_profile": "core_plus_macro",
                        "verdict": "dual_role_required",
                    },
                    "governance_contract": {
                        "verdict": "dual_role_governance_active",
                        "current_closure": "global_ranking_vs_support_aware_production_split",
                        "treat_as_parity_blocker": False,
                        "support_governance_route": "exact_live_bucket_present_but_below_minimum",
                    },
                    "leaderboard_snapshot_created_at": "2026-04-14T06:51:24Z",
                    "alignment_evaluated_at": "2026-04-14T12:40:00Z",
                    "current_alignment_inputs_stale": False,
                    "current_alignment_recency": {"inputs_current": True},
                    "artifact_recency": {"alignment_snapshot_stale": True},
                    "global_recommended_profile": "core_only",
                    "train_selected_profile": "core_plus_macro",
                    "train_selected_profile_source": "bull_4h_pocket_ablation.support_aware_profile",
                    "train_support_cohort": "bull_supported_neighbor_buckets_proxy",
                    "train_support_rows": 84,
                    "train_exact_live_bucket_rows": 0,
                    "live_regime_gate": "CAUTION",
                    "live_entry_quality_label": "D",
                    "live_execution_guardrail_reason": "unsupported_exact_live_structure_bucket_blocks_trade",
                    "live_current_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "live_current_structure_bucket_rows": 0,
                    "minimum_support_rows": 50,
                    "live_current_structure_bucket_gap_to_minimum": 50,
                    "support_progress": {
                        "status": "stalled_under_minimum",
                        "stagnant_run_count": 3,
                        "escalate_to_blocker": True,
                    },
                    "supported_neighbor_buckets": ["CAUTION|base_caution_regime_or_bias|q15"],
                    "bull_support_aware_profile": "core_plus_macro",
                    "bull_support_neighbor_rows": 84,
                    "bull_exact_live_bucket_proxy_rows": 43,
                    "blocked_candidate_profiles": [
                        {
                            "feature_profile": "core_plus_macro",
                            "blocker_reason": "unsupported_exact_live_structure_bucket",
                            "exact_live_bucket_rows": 0,
                        }
                    ],
                },
            }
        )
    )

    diag = hb_parallel_runner.collect_leaderboard_candidate_diagnostics()

    assert diag["selected_feature_profile"] == "core_only"
    assert diag["dual_profile_state"] == "leaderboard_global_winner_vs_train_support_fallback"
    assert diag["profile_split"]["verdict"] == "dual_role_required"
    assert diag["governance_contract"]["verdict"] == "dual_role_governance_active"
    assert diag["governance_contract"]["current_closure"] == "global_ranking_vs_support_aware_production_split"
    assert diag["support_governance_route"] == "exact_live_bucket_present_but_below_minimum"
    assert diag["governance_current_closure"] == "global_ranking_vs_support_aware_production_split"
    assert diag["train_selected_profile"] == "core_plus_macro"
    assert diag["current_alignment_inputs_stale"] is False
    assert diag["current_alignment_recency"]["inputs_current"] is True
    assert diag["artifact_recency"]["alignment_snapshot_stale"] is True
    assert diag["leaderboard_payload_source"] == "latest_persisted_snapshot"
    assert diag["leaderboard_payload_stale"] is False
    assert diag["live_current_structure_bucket_rows"] == 0
    assert diag["minimum_support_rows"] == 50
    assert diag["live_current_structure_bucket_gap_to_minimum"] == 50
    assert diag["support_progress"]["status"] == "stalled_under_minimum"
    assert diag["support_progress"]["escalate_to_blocker"] is True
    assert diag["blocked_candidate_profiles"][0]["blocker_reason"] == "unsupported_exact_live_structure_bucket"


def test_collect_leaderboard_candidate_diagnostics_surfaces_train_contract_stale_state(tmp_path, monkeypatch):
    monkeypatch.setattr(hb_parallel_runner, "PROJECT_ROOT", str(tmp_path))
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "leaderboard_feature_profile_probe.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-15T23:02:01Z",
                "target_col": "simulated_pyramid_win",
                "leaderboard_count": 8,
                "top_model": {
                    "selected_feature_profile": "core_plus_4h",
                    "selected_feature_profile_source": "feature_group_ablation.recommended_profile",
                    "selected_feature_profile_blocker_applied": False,
                    "selected_feature_profile_blocker_reason": None,
                },
                "alignment": {
                    "dual_profile_state": "train_exact_supported_profile_stale_under_minimum",
                    "support_governance_route": "exact_live_bucket_present_but_below_minimum",
                    "profile_split": {
                        "global_profile": "core_plus_4h",
                        "production_profile": "core_plus_macro_plus_4h_structure_shift",
                        "verdict": "dual_role_required",
                    },
                    "governance_contract": {
                        "verdict": "train_profile_contract_stale_against_current_support",
                        "current_closure": "train_still_claims_exact_supported_profile_but_live_bucket_under_minimum",
                        "recommended_action": "rerun train",
                        "treat_as_parity_blocker": False,
                        "support_governance_route": "exact_live_bucket_present_but_below_minimum",
                    },
                    "current_alignment_recency": {"inputs_current": True},
                    "artifact_recency": {"alignment_snapshot_stale": False},
                    "global_recommended_profile": "core_plus_4h",
                    "train_selected_profile": "core_plus_macro_plus_4h_structure_shift",
                    "train_selected_profile_source": "bull_4h_pocket_ablation.exact_supported_profile",
                    "live_current_structure_bucket": "CAUTION|structure_quality_caution|q35",
                    "live_current_structure_bucket_rows": 9,
                    "minimum_support_rows": 50,
                    "live_current_structure_bucket_gap_to_minimum": 41,
                    "support_progress": {
                        "status": "regressed_under_minimum",
                        "delta_vs_previous": -1,
                    },
                    "exact_bucket_root_cause": "exact_bucket_present_but_below_minimum",
                    "support_blocker_state": "exact_lane_proxy_fallback_only",
                    "proxy_boundary_verdict": "proxy_governance_reference_only_exact_support_blocked",
                    "blocked_candidate_profiles": [],
                },
            }
        )
    )

    diag = hb_parallel_runner.collect_leaderboard_candidate_diagnostics()

    assert diag["dual_profile_state"] == "train_exact_supported_profile_stale_under_minimum"
    assert diag["support_governance_route"] == "exact_live_bucket_present_but_below_minimum"
    assert diag["governance_contract"]["verdict"] == "train_profile_contract_stale_against_current_support"
    assert diag["governance_current_closure"] == "train_still_claims_exact_supported_profile_but_live_bucket_under_minimum"
    assert diag["governance_recommended_action"] == "rerun train"
    assert diag["exact_bucket_root_cause"] == "exact_bucket_present_but_below_minimum"
    assert diag["support_blocker_state"] == "exact_lane_proxy_fallback_only"
    assert diag["proxy_boundary_verdict"] == "proxy_governance_reference_only_exact_support_blocked"
    assert diag["support_progress"]["status"] == "regressed_under_minimum"
    assert diag["support_progress"]["delta_vs_previous"] == -1


def test_refresh_train_prerequisites_runs_both_artifacts_when_train_is_needed(monkeypatch):
    calls = []

    def _feature_result():
        calls.append("feature_result")
        return {"success": True, "returncode": 0}

    def _feature_summary():
        calls.append("feature_summary")
        return {"recommended_profile": "core_plus_macro_plus_4h_structure_shift"}

    def _bull_result():
        calls.append("bull_result")
        return {"success": True, "returncode": 0}

    def _bull_summary():
        calls.append("bull_summary")
        return {"live_context": {"current_live_structure_bucket_rows": 90}}

    monkeypatch.setattr(hb_parallel_runner, "run_feature_group_ablation", _feature_result)
    monkeypatch.setattr(hb_parallel_runner, "collect_feature_ablation_diagnostics", _feature_summary)
    monkeypatch.setattr(hb_parallel_runner, "run_bull_4h_pocket_ablation", _bull_result)
    monkeypatch.setattr(hb_parallel_runner, "collect_bull_4h_pocket_diagnostics", _bull_summary)

    result = hb_parallel_runner.refresh_train_prerequisites(needs_train=True)

    assert calls == ["feature_result", "feature_summary", "bull_result", "bull_summary"]
    assert result["feature_ablation_summary"]["recommended_profile"] == "core_plus_macro_plus_4h_structure_shift"
    assert result["bull_pocket_summary"]["live_context"]["current_live_structure_bucket_rows"] == 90


def test_refresh_train_prerequisites_skips_artifacts_when_train_not_needed():
    assert hb_parallel_runner.refresh_train_prerequisites(needs_train=False) == {}
